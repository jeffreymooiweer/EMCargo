# Development

EMCargo is one product with two processes: a **FastAPI** backend on Python 3.12 and a
**React 18 + TypeScript** frontend built with Vite. Data lives in a file-based SQLite
database; there is no separate database service.

- [Running from source](#running-from-source)
- [Tests](#tests)
- [Project layout](#project-layout)
- [The schema runner](#the-schema-runner)
- [How documents are produced](#how-documents-are-produced)
- [Versioning](#versioning)
- [Releasing](#releasing)
- [The UN cards](#the-un-cards)

## Running from source

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
mkdir -p ../data

DATABASE_URL=sqlite:////absolute/path/to/repo/data/emcargo.db \
DATA_DIR=/absolute/path/to/repo/data \
APP_ENV=development \
APP_SECRET_KEY=dev-secret \
ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.local ADMIN_PASSWORD=emcargo123 \
CATALOG_AUTO_SYNC=false \
  uvicorn app.main:app --reload --port 8080
```

Three things catch people out:

- **The repo `.env` is not picked up when you run uvicorn from `backend/`.** Pydantic
  resolves `env_file=".env"` relative to the working directory, and there is no
  `backend/.env`. Pass the variables explicitly, as above.
- **`DATA_DIR` and `DATABASE_URL` default to `/data`,** which is usually not writable
  outside Docker. Point them at a folder in the repo.
- **`APP_SECRET_KEY=dev-secret` above is not the key you get.** It is on the published
  list, so the application replaces it with one it generates and stores in
  `DATA_DIR/secret_key`, and reuses that afterwards. This happens in every environment;
  `APP_ENV=development` only silences the CORS and admin-password warnings. You are
  logged out once, the first time, and not again unless you delete the file.

`CATALOG_AUTO_SYNC=false` skips the startup fetch of external catalogues. It makes
startup much faster and does not affect weight calculations.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server runs on port 5173 and proxies `/api` to `http://localhost:8080`.

## Tests

```bash
cd backend
DATABASE_URL=sqlite:////absolute/path/to/repo/data/test.db \
DATA_DIR=/absolute/path/to/repo/data \
  python -m pytest
```

Frontend:

```bash
cd frontend
npm test           # Vitest + Testing Library
npm run build      # tsc -b && vite build (typecheck)
```

No ESLint is configured.

A few notes on the test suite:

- **Import format for manual testing.** The wizard expects one line per row as
  `description | quantity | unit`, pipe- or tab-separated, with dimensions inside the
  description: `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks`. Free text without
  dimensions yields `status=error` and 0 kg. The steel regression set totals ~7,534 kg.
- **The equipment library is empty by design.** Seed tests use generic `DEMO-*` items.
- **Regulatory tables are pinned verbatim.** The IMDG segregation table, the class 1
  compatibility matrix and samples from the EmS index are asserted literally, so an
  accidental edit fails a test instead of silently shipping.
- **The AVC overlay is tested by coordinate.** `test_avc_waybill.py` checks where text
  lands on the page, not just that it is present.
- **A language is complete or it is not.** `test_languages.py` walks the config and seed
  files and requires a text in every language of `SUPPORTED` wherever there is a Dutch and
  an English one, holds lists to the same length, and rejects a "translation" that only
  repeats the Dutch. An AST pass over `app/` catches the same omission in code. The tests
  name no language: they read `SUPPORTED`, so switching a language on is one line and the
  guard grows with it. Adding an interface string means adding it in every language.
- **Errors carry a code, not a sentence.** Anything a user reads goes through
  `app/core/messages.py`: the server sends `{code, message, params}` and the interface
  translates on the code, falling back to the English `message` when it does not know it.
  A sentence typed straight into `HTTPException` can only be written in one language, and
  `test_error_messages.py` fails on one. Schema validators use `PydanticCustomError`, which
  puts the code in the `type` field of the 422 body and the parameters in `ctx`.
- **The source is in English.** Comments and docstrings across `backend/`, `frontend/`,
  `scripts/` and the workflows are English; only what a user reads is translated. Test
  docstrings are deliberately long: they say why the test exists and which defect
  provoked it, so a later reader knows what would break if the test were deleted.
- **The app is started the way a user starts it.** `test_starts_out_of_the_box.py` builds
  the application in a real subprocess with a clean environment and nothing configured.
  It exists because everything else runs with `APP_ENV=test`, and a startup check that
  only fires in production went unnoticed for five releases.

## Project layout

```
backend/
  app/
    api/routes/         FastAPI endpoints
    config/             document_registry.json, dg_compliance.json, dg_instructions.json
    models/             SQLAlchemy tables
    schemas/            Pydantic request and response models
    services/
      documents/        PDF filling and generation
      dg/               dangerous goods: enrichment, autofill, compliance
  seed/                 bundled reference data (materials, locations, dg)
  tests/
frontend/
  src/components/       wizard steps and panels
  src/pages/            routed pages
  src/settings/         the user's own settings, loaded once and shared
  src/i18n/             nl.json, en.json, de.json, fr.json
templates/forms/        official PDF forms that get filled in
scripts/                one-off maintenance scripts (incl. un_cards/, the card generator,
                        and ux_bench/, the usability measurements)
docs/                   this documentation
unraid/                 Unraid Community Applications template
```

## The schema runner

`init_app` calls `Base.metadata.create_all`, which creates **missing tables** and never
adds a column to a table that already exists. For a long time that was enough: the
settings tables (`user_preferences`, `instance_settings`) hold a single JSON document
each, so adding a preference is a field on a Pydantic model in `app/schemas/settings.py`
and a database written by an older version simply lacks the key and falls back to its
default. That rule still holds for settings, and `test_settings.py` pins it.

The shipment history (v1.173.0) is the first thing that wants real columns, so there is
now a runner beside `create_all`: `app/core/migrations.py`. It keeps a numbered list of
steps and a `schema_version` table recording which have been applied.

- **A fresh database is stamped, not migrated.** If no `users` table existed before
  start-up, `create_all` has just made every table in its current shape, and every step
  is recorded as applied without running — a step that adds a column would otherwise
  find it there and fail.
- **An old database has the pending steps run in order**, each in its own transaction,
  recorded as it succeeds. A step that fails leaves the version where it was and the
  next start tries again.
- **Every step is written to be safe to run twice.** `add_column` checks the column is
  absent first; table creation uses `checkfirst`. That is what makes a backup restored
  between two steps recoverable.

To change the schema: change the model, append a step to `MIGRATIONS` with the next
number and a short name, and write the step with the helpers so it is idempotent. Never
renumber or remove a step. Adding a **table** still needs only its model imported
somewhere `startup` reaches (`startup.HISTORY_TABLES` and `SETTINGS_TABLES` exist purely
so those imports cannot look removable), but a step that creates it with `checkfirst` is
the honest way to bring an older database along. `test_history.py` exercises the runner
in both directions.

What the database is asked to carry beyond this, and whether the engine underneath it
should ever change, is worked out in [The database](database-plan.md).

## How documents are produced

Three paths, chosen by the `exporter` field in `document_registry.json`:

| `exporter` | How it works | Used by |
|---|---|---|
| `pdf_template` | Writes into the template's AcroForm fields, via PyMuPDF (falling back to pypdf) | CMR, CIM, IATA |
| `avc` | Draws a reportlab text layer and merges it onto a flat template | AVC waybill |
| `generic` | Generates a PDF from scratch with reportlab | Everything else |

The AVC form has no form fields at all, which is why it needs the overlay. Its
coordinate grid is derived from the template's own ruling and documented at the top of
`backend/app/services/documents/avc_form.py`.

`document_registry.json` is the single source of truth for which documents exist, which
sections and fields they have, which status each field carries (`USER_REQUIRED`,
`CONDITIONAL`, `CARRIER_PROVIDED`, `OPERATIONAL`, `SIGNATURE_REQUIRED`) and which
dangerous goods profile applies. Adding a document usually means editing that file plus
one exporter.

## Versioning

[Semantic Versioning](https://semver.org/) from 1.0.0 onwards. Version numbers are bumped
**conservatively** — collect small fixes into one patch release rather than reaching for
a minor.

| Bump | When | Example |
|---|---|---|
| **PATCH** `1.29.2` → `1.29.3` | Bug fixes, text and label corrections, small data fixes, documentation. No new functionality. | Wrong button label, missing translation, corrected density, a container that will not start |
| **MINOR** `1.28.1` → `1.29.0` | New functionality that leaves existing shipments alone | New wizard step, new document, new endpoint, a third interface language |
| **MAJOR** `1.x` → `2.0.0` | Breaking changes: incompatible APIs or data formats, a different wizard structure, a required migration | Reserved for major overhauls |

When in doubt, take the smaller bump.

The version number lives in **five** places — `VERSION`, `backend/VERSION`,
`frontend/package.json` and twice in `frontend/package-lock.json` — as well as in the git
tag `v*`, in the Docker tag, and in `GET /api/health`.

Do not set them by hand:

```bash
python scripts/bump_version.py 1.37.0
```

`scripts/check_versions.py` runs in CI and fails a pull request whose five values disagree.

> **Why this is stricter than it looks.** The lock file used to be left out of the check, so
> it drifted at every release, and the **Tag release** workflow repaired it by committing to
> `main` *after* the merge. The repair worked — and moved `main` out from under whatever
> branch came next, which then conflicted on `VERSION` and `CHANGELOG.md` and could not be
> merged until it was rebased. Four lines of JSON cost two rebases in a single day.
> Releasing no longer writes to `main` at all; the check moved to the pull request, where
> the mistake is made.

## Releasing

1. Run `python scripts/bump_version.py <version>` and write the `CHANGELOG.md` entry.
   The changelog is not only the record: since v1.125.0 it ships in the Docker image and
   the what's-new card serves its entries to users after an update, and a test fails the
   pull request if the newest heading and the `VERSION` files disagree — a release note
   cannot be forgotten.
2. Merge to `main`.
3. Run the **Tag release** workflow from GitHub Actions with the version number,
   or merge from an `agent/release-v<version>` branch to start it automatically.
   It verifies the version files, builds the native bundle and names the tested
   image before publishing the GitHub Release. It does not commit anything.
4. **CI** already built and pushed `ghcr.io/jeffreymooiweer/emcargo:latest` and `:<short-sha>` on
   the merge in step 2. Step 3 adds `:<version>` and `:v<version>` to that same image;
   nothing is rebuilt. Both spellings are published because the in-app updater asked for
   the `v` form up to v1.136.0 and for the bare form from v1.137.0 on — an installation of
   either generation finds the image it looks for.

Publishing on current `main` uses the workflow's `GITHUB_TOKEN`. An optional
`RELEASE_TOKEN` with workflow scope is needed only to tag an older commit whose
workflow tree differs from current `main`.

**A release does not rebuild the image.** The image is built once, by the push to `main`, and pushed as
`latest` and as the short commit SHA. `tag-release.yml` then puts the version number on
that same manifest with `docker buildx imagetools create` — server-side, both
architectures, in seconds.

Until v1.40.0 the tag rebuilt the identical commit from scratch, four to six minutes of
recompiling bits that already existed, with the test suites run over them a second time.
Retagging is not merely quicker: what gets released is bit for bit what went green through
CI, rather than a second compilation that could differ.

If the build on `main` has not finished yet, `tag-release.yml` waits for the SHA tag to
appear — up to twenty minutes, then it fails. Failing is the right outcome there: no tested
image means nothing to release, and a version tag pointing at yesterday's build would be
worse than no release at all.

Application license reports are advisory under the
[publication policy](licensing/rights-register.md#application-publication-policy--2026-09-16).
CI still validates the content inventory and scans both image architectures. The
native bundle includes its inventories, license notices and open-review reports.
Tests, dependency checks and image smoke tests must pass before images publish.
Only `main` publishes images; pull requests and other dispatched refs do not.

The docker job has a 45-minute timeout so a wedged build fails visibly rather than running
all day, and each ref writes its own buildx cache scope — sharing one `mode=max` scope let
two exports race, and a build once hung for an hour and a half instead of taking three
minutes.

### What runs, and when

Automatic workflows are limited to CI, application release tagging and card-set
publication after relevant source changes. Everything else in `.github/workflows/`
waits to be asked. Ordinary application changes do not regenerate card sets.

| Workflow | Runs on | Jobs |
|---|---|---|
| `ci.yml` | push to `main`, every pull request, on request | Backend tests, Frontend build, Docker build |
| `tag-release.yml` | on request (and on a merged `agent/release-v*` branch) | tag, GitHub Release, and it renames main's image to the version |
| `generate-un-cards.yml` | card generator/source changes on `main`, or on request | generate, validate and publish the separate card package; never mark it as the latest app release |
| `read-land-regulations.yml` | on request | quotes ADR/RID/ADN; commits nothing |
| `probe-*.yml`, `extract-imdg-*.yml` | on request | maintenance and research |

Until v1.39.0 there were two workflows *both named* `CI` — `ci.yml` and `dockerhub.yml` —
each triggered by the same pushes, so `pytest` ran twice and `npm ci` ran twice on every
commit. Five checks per push, two of them a copy of two others. A release with three
commits on the branch spent fifteen jobs before anything was merged. They are now one
workflow, and `release.yml` — a second, unused path to creating the same GitHub Release —
is gone with them.

Both `linux/amd64` and `linux/arm64` are built and inspected in CI, including on
pull requests. ARM64 uses QEMU on the amd64 runner; each architecture has its own
cache scope. A pull request produces reports without publishing an image.

Pull request runs cancel their own predecessors. Runs on `main` and on a tag never do —
a publication hangs off those.

## The UN cards

Since v1.129.0 EMCargo generates its own UN cards from the measured seed tables in
`backend/seed/dg/` — the generator lives in `scripts/un_cards/`, the **Generate UN
cards** workflow publishes the set as a GitHub Release, and an administrator imports it
under **Settings → UN Cards**. The cards are in neither the repository nor the Docker
image; they live on the data volume. The whole pipeline — sources, label artwork,
provision texts, validation, atomic import — is described in
[un-cards.md](un-cards.md), and `backend/tests/test_un_card_generator.py` plus
`backend/tests/test_un_card_store.py` guard both ends of it.

One historical dataset remains: `backend/seed/dg/card_data.json` was extracted with
`scripts/extract_un_card_data.py` from the third-party card set that shipped before
v1.129.0 (IMDG 41-22 per-substance data: marine pollutant, bulk). The extraction
cross-checked its EmS readings against `ems.json` — 2,282 agreed, none disagreed — and
`backend/tests/test_dg_card_data.py` still guards the values. The source PDFs are no
longer bundled, so re-running that extraction needs the original set; replacing the
dataset with values read from the official IMDG Code is the intended way forward.

## Browser preview

Vite allows the supervised preview hostname explicitly. Start the development
server with the documented preview service when available; the backend must also
be running for authenticated workflows. A successful sign-in page render verifies
connectivity only, not complete browser QA.
