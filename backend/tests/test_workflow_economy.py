"""Every step once, and emulation only when something is published.

There were two workflows in this repository both called ``CI`` and both firing
on the same push: ``ci.yml`` and ``dockerhub.yml``. They largely did the same
thing. ``pytest`` ran twice, ``npm ci`` ran twice, and there were five checks
under a pull request of which two were copies of two others. On a release with
three commits on the branch that was fifteen jobs before anything was merged.

The second cost was the Docker build. It always asked for ``linux/arm64``, on a
pull request too, where the result was then thrown away because nothing is
pushed. arm64 runs on an amd64 runner under QEMU, and that emulation was the
lion's share of the runtime.

That kind of duplicated work creeps back in unnoticed — a second workflow is
quickly added and nobody counts the checks. Hence these tests. They read the
YAML as text; that is deliberately crude, because what is guarded here is not
the exact wording but the shape: one CI workflow, narrowly scoped publishing
workflows, no duplicates, and no emulation without publication.
"""

from pathlib import Path
from fnmatch import fnmatchcase

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def load(name: str) -> dict:
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    # PyYAML reads the key `on:` as the boolean value True.
    return yaml.safe_load(text)


def triggers(definition: dict) -> dict:
    return definition.get("on") or definition.get(True) or {}


def steps_only(name: str) -> str:
    """The workflow without its comments.

    These files explain in comments what went wrong, and those comments contain
    the words these tests count — "dockerhub.yml", "npm ci". Without this sieve
    a test measures its own explanation.
    """
    lines = (WORKFLOWS / name).read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if not line.lstrip().startswith("#"))


def automatic() -> list[str]:
    """The workflows that start by themselves, and therefore cost money per push."""
    started = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        on = triggers(load(path.name))
        if {"push", "pull_request", "schedule"} & set(on):
            started.append(path.name)
    return started


# --- What runs by itself ---------------------------------------------------


def test_only_ci_and_scoped_publication_workflows_start_by_themselves():
    """Card sets were missing because their publication was manual only.
    Source changes now publish them, while all research and extraction
    workflows remain opt-in and the test suites still run only once."""
    assert automatic() == ["ci.yml", "generate-un-cards.yml", "tag-release.yml"]


@pytest.mark.parametrize("path, should_generate", [
    ("scripts/un_cards/render.py", True),
    ("scripts/un_cards/assets/labels/3.png", True),
    ("backend/seed/dg/adr_table_a.json", True),
    ("backend/app/config/dg_compliance.json", True),
    ("backend/app/pdf_style.py", True),
    ("backend/app/assets/fonts/CalSans-Regular.ttf", True),
    ("backend/app/assets/fonts/DejaVuSans.ttf", True),
    ("backend/app/assets/fonts/DejaVu-LICENSE.txt", True),
    ("backend/app/assets/logo.png", True),
    ("frontend/public/shipping.png", False),
    (".github/workflows/generate-un-cards.yml", True),
    ("VERSION", False),
    ("frontend/src/pages/TripsPage.tsx", False),
    ("backend/app/api/routes/trips.py", False),
    ("docs/development.md", False),
])
def test_card_generation_only_follows_its_sources_on_main(path, should_generate):
    """Ordinary app changes must not rebuild thousands of unchanged PDFs.
    A branch or pull request must not trigger their public release either.
    The dossier style moved cards to the backend's shared theme, bundled
    fonts and logo; only those actual inputs should trigger regeneration.
    """
    events = triggers(load("generate-un-cards.yml"))
    assert set(events) == {"push", "workflow_dispatch"}
    assert events["push"]["branches"] == ["main"]
    assert any(fnmatchcase(path, pattern) for pattern in events["push"]["paths"]) == should_generate


def test_card_publication_does_not_replace_the_latest_app_release():
    """The application updater reads the latest app release. A separately
    published data set must not replace it with a non-version card tag."""
    assert "--latest=false" in steps_only("generate-un-cards.yml")


def test_no_two_workflows_share_a_name():
    """Two entries called "CI" in the list is exactly how the duplicated work
    stayed invisible for so long."""
    names = [load(p.name).get("name") for p in sorted(WORKFLOWS.glob("*.yml"))]
    assert len(names) == len(set(names)), names


def test_the_duplicate_is_gone():
    assert not (WORKFLOWS / "dockerhub.yml").exists()
    assert not (WORKFLOWS / "release.yml").exists()


def test_nothing_still_points_at_the_deleted_workflow():
    """The tag workflow kicks off the build on the tag ref; if that points at a
    file that no longer exists, no image appears and nothing says so."""
    for path in WORKFLOWS.glob("*.yml"):
        assert "dockerhub.yml" not in steps_only(path.name), path.name


# --- Eén keer per duw -----------------------------------------------------


def test_the_test_suites_run_exactly_once_per_push():
    everything = "\n".join(steps_only(name) for name in automatic())
    assert everything.count("pytest -q") == 1
    assert everything.count("npm test") == 1
    assert steps_only("ci.yml").count("npm ci") == 1


def test_the_release_builds_the_interface_once_for_the_bundle_and_tests_nothing():
    """The native bundle carries the built interface, so the release installs
    the frontend's dependencies once more to build it. That is a build, not a
    test: the suites ran on the pull request and on main, and the release
    reruns none of them."""
    tag_release = steps_only("tag-release.yml")
    assert tag_release.count("npm ci") == 1
    assert "npm run build" in tag_release
    assert "npm test" not in tag_release
    assert "pytest" not in tag_release


@pytest.mark.parametrize("step", ["npm test", "npm run build", "npm audit"])
def test_the_frontend_checks_survived_the_merge(step):
    """When the two were merged, the more thorough of the two frontend jobs was
    kept. The audit and the tests were only in ci.yml and must not be lost
    because the other job was shorter."""
    assert step in (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")


# --- Both shipped architectures are inventoried before publication ---------


def test_both_architectures_are_inspected_before_publication():
    """Native PDF/OCR wheels may carry different dependencies on each CPU."""
    docker = load("ci.yml")["jobs"]["docker"]
    assert docker["strategy"]["matrix"]["arch"] == ["amd64", "arm64"]
    build = next(s for s in docker["steps"] if s.get("uses", "").startswith("docker/build-push-action"))
    assert build["with"]["push"] is False
    assert build["with"]["load"] is True


def test_a_pull_request_never_publishes_an_image():
    docker = load("ci.yml")["jobs"]["docker"]
    publish = next(s for s in docker["steps"] if "docker push " in s.get("run", ""))
    assert "github.event_name != 'pull_request'" in publish["if"]
    assert "github.ref == 'refs/heads/main'" in publish["if"]
    manifest = load("ci.yml")["jobs"]["publish-image"]
    assert manifest["if"] == publish["if"]


def test_application_publication_keeps_technical_checks_and_advisory_reports():
    """The owner's release request replaced the blanket licensing hold with
    advisory reports. Publication must still depend on tests and image scans,
    and changing that policy must not erase unresolved evidence records.

    Automatic releases also resolve the exact merge revision before building.
    That added prerequisite must coexist with every original technical gate;
    the old three-job expectation incorrectly rejected the release workflow.
    """
    jobs = load("ci.yml")["jobs"]
    assert set(jobs["docker"]["needs"]) == {"revision", "backend", "frontend", "rights"}
    assert "docker" in jobs["publish-image"]["needs"]
    assert "image_ready" not in steps_only("ci.yml")
    rights = jobs["rights"]["steps"]
    assert any(s.get("run") == "python scripts/check_third_party_manifest.py" for s in rights)
    assert any("if ! python scripts/check_third_party_manifest.py --publish image --report" in s.get("run", "") for s in rights)
    docker = "\n".join(s.get("run", "") for s in jobs["docker"]["steps"])
    assert "--channel image --report" in docker
    assert "--channel image --publish" not in docker
    release = steps_only("tag-release.yml")
    assert "--channel native --report" in release
    assert "--channel native --publish" not in release
    assert "--publish cards" in steps_only("generate-un-cards.yml")


def test_the_release_is_visible_only_when_both_install_routes_exist():
    """Publishing GitHub's latest release before the image was named made the
    in-app updater offer a version that could not yet be pulled. Native assets
    must also be attached as part of creation, not in a later workflow step.
    """
    steps = load("tag-release.yml")["jobs"]["tag-and-release"]["steps"]
    image_index = next(i for i, s in enumerate(steps) if "imagetools create" in s.get("run", ""))
    release_index = next(i for i, s in enumerate(steps) if "gh release create" in s.get("run", ""))
    assert image_index < release_index
    create = steps[release_index]["run"]
    assert "--verify-tag --latest" in create
    assert '"emcargo-$VERSION-native.tar.gz" "emcargo-$VERSION-native.tar.gz.sha256"' in create
    checkout = next(s for s in steps if s.get("uses", "").startswith("actions/checkout"))
    assert "github.event.pull_request.merge_commit_sha" in checkout["with"]["ref"]


def test_qemu_is_only_set_up_when_arm64_is_wanted():
    steps = load("ci.yml")["jobs"]["docker"]["steps"]
    qemu = next(s for s in steps if s.get("uses", "").startswith("docker/setup-qemu-action"))
    assert qemu["if"] == "matrix.arch == 'arm64'"


# --- Not the same result twice ----------------------------------------------


def test_a_superseded_pull_request_run_is_cancelled():
    ci = load("ci.yml")
    assert ci["concurrency"]["cancel-in-progress"] == (
        "${{ github.event_name == 'pull_request' }}"
    )


def test_but_a_publishing_run_is_never_cancelled():
    """main and a tag do run: an image hangs off those. The expression above
    already arranges that, but it is the kind of thing somebody eventually
    simplifies to `true`."""
    ci = load("ci.yml")
    assert ci["concurrency"]["cancel-in-progress"] != True  # noqa: E712


# --- A tag is a name, not a build instruction --------------------------------
#
# The release built the same commit a second time, now on the tag ref: four to
# six minutes to compile precisely the same bits, with the test suites over it
# again. Main had already built, tested and pushed that image under its short
# SHA. `imagetools create` puts the version name on that manifest server-side.


def test_the_release_does_not_rebuild_what_main_already_built():
    tag_release = steps_only("tag-release.yml")
    assert "imagetools create" in tag_release
    assert "gh workflow run" not in tag_release


def test_the_released_image_is_the_one_that_was_tested():
    """The manifest is renamed, not remade. A second compilation of the same
    source can come out slightly different; the same manifest cannot."""
    tag_release = steps_only("tag-release.yml")
    assert "rev-parse --short=7 HEAD" in tag_release
    assert (
        'imagetools create -t "$IMAGE:$VERSION" -t "$IMAGE:v$VERSION" "$IMAGE:$SHORT"'
        in tag_release
    )


def test_the_release_publishes_both_tag_spellings():
    """Up to v1.136.0 the in-app updater built its pull reference as
    ``repo:v<version>``; from v1.137.0 on it asks for the bare version. An
    installation of the first generation cannot update itself out of that
    generation unless the name it asks for exists, so the release names the
    one manifest twice. It costs nothing: no layer is pulled or pushed."""
    tag_release = steps_only("tag-release.yml")
    assert '"$IMAGE:v$VERSION"' in tag_release


def test_it_gives_up_rather_than_release_an_older_image():
    """If the build on main failed there is no tested image. Stopping is then
    better than a version tag on something from yesterday."""
    tag_release = steps_only("tag-release.yml")
    assert "never appeared" in tag_release
    assert "exit 1" in tag_release


def test_ci_no_longer_runs_on_a_tag():
    """Otherwise there are two ways again for a version image to come about, and
    those drift apart in the long run."""
    assert "tags" not in triggers(load("ci.yml"))["push"]


# --- The reading tool no longer runs along ----------------------------------


def test_reading_a_regulation_is_something_you_ask_for():
    """This workflow fetched four PDFs of some 40 MB together on every push that
    touched the script, on a branch where nobody read the log."""
    on = triggers(load("read-land-regulations.yml"))
    assert set(on) == {"workflow_dispatch"}
