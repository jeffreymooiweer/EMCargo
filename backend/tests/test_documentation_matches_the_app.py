"""Documentation that has quietly stopped being true.

A docs pass found three kinds of rot, and all three are the sort that nobody
notices by reading:

1. **`MAX_PASTE_BYTES` was documented as a setting and read by nothing.** It sat
   in `Settings` and in `docs/configuration.md` with a default of 512000, and no
   line of the application ever looked at it. The upload cap has always come from
   a constant in `spreadsheet_io.py`. A documented setting that does nothing is
   worse than an undocumented one: it invites somebody to tune it and then
   conclude the app ignores them.

2. **`ROADMAP.md` still advertised 400 goods** three releases after the catalogue
   grew to 1,093. Nothing breaks; the number is simply a lie in the shop window.

3. **Links to sections that had been renamed.** Silent, and only found by
   clicking.

So these are guards, not prose. They compare the documentation against the thing
it describes and fail when the two drift.

What is deliberately *not* guarded: prose, tone, and the regulatory reasoning.
Those cannot be checked mechanically and this suite should not pretend otherwise.
"""
from __future__ import annotations

import json
import re
import urllib.parse
from pathlib import Path

import pytest

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
# Upstream license notices retain their original relative links unchanged;
# compiled output also is not project-authored documentation.
DOCS = sorted(
    path
    for path in ROOT.rglob("*.md")
    if not any(part in {"node_modules", ".git", ".pytest_cache", "licenses", "dist"} for part in path.parts)
    and not path.is_relative_to(ROOT / "data")
    and not path.is_relative_to(ROOT / "backend" / "data")
)

#: Variables that are read by the container or the runtime rather than by
#: ``Settings``, so they legitimately appear in the docs without being a field.
CONTAINER_VARIABLES = {"TZ", "PUID", "PGID"}


def documented_variables() -> set[str]:
    """The environment variables `docs/configuration.md` promises."""
    text = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    return set(re.findall(r"`([A-Z][A-Z0-9_]{3,})`", text))


def test_every_setting_the_app_reads_is_documented():
    """A setting nobody documents is a setting nobody knows to use."""
    fields = {name.upper() for name in Settings.model_fields}
    missing = sorted(fields - documented_variables())
    assert missing == [], f"undocumented settings: {missing}"


def test_every_documented_variable_still_exists():
    """The other direction, and the one that actually happened.

    `MAX_PASTE_BYTES` was in this table for months while nothing read it.
    """
    text = (ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    fields = {name.upper() for name in Settings.model_fields}
    promised = documented_variables() - CONTAINER_VARIABLES
    # Only the *first* column of a table row names a variable. `DEBUG` and
    # `INFO` sit in the second column of the LOG_LEVEL row as its permitted
    # values, and other capitalised tokens (`USER_REQUIRED`, `GET`) are not
    # settings at all.
    ghosts = sorted(
        name
        for name in promised
        if name not in fields and re.search(rf"^\|\s*`{name}`\s*\|", text, re.M)
    )
    assert ghosts == [], f"documented but not a setting: {ghosts}"


def test_the_goods_count_in_the_documentation_is_the_real_one():
    """ROADMAP said 400 for three releases after the catalogue reached 1,093."""
    materials = json.loads((ROOT / "backend" / "seed" / "materials.json").read_text(encoding="utf-8"))
    actual = len(materials)

    wrong: list[str] = []
    for path in DOCS:
        if path.name == "CHANGELOG.md" or "release-notes" in str(path):
            continue  # a changelog records what was true then, on purpose
        for match in re.finditer(r"([\d][\d,.]*)\s+goods\b", path.read_text(encoding="utf-8")):
            claimed = int(match.group(1).replace(",", "").replace(".", ""))
            if claimed != actual:
                wrong.append(f"{path.relative_to(ROOT)}: says {match.group(1)}, catalogue holds {actual}")
    assert wrong == [], "\n".join(wrong)


def heading_anchors(path: Path) -> set[str]:
    """GitHub's anchor for every heading in a markdown file."""
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^#{1,6}\s+(.*)", line)
        if match:
            slug = re.sub(r"[^\w\s-]", "", match.group(1).lower()).strip().replace(" ", "-")
            found.add(slug)
    return found


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_the_internal_links_in_this_document_resolve(path: Path):
    """A link to a renamed section fails silently; only a click finds it."""
    broken: list[str] = []
    for match in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        target = match.group(1).strip()
        if target.startswith(("http://", "https://", "mailto:", "#!")):
            continue
        file_part, _, fragment = target.partition("#")
        file_part = urllib.parse.unquote(file_part)
        destination = (path.parent / file_part if file_part else path).resolve()
        if file_part and not destination.exists():
            broken.append(f"missing file: {target}")
            continue
        if fragment and destination.suffix == ".md":
            if fragment.lower() not in heading_anchors(destination):
                broken.append(f"missing anchor: {target}")
    assert broken == [], f"{path.relative_to(ROOT)}\n" + "\n".join(broken)
