# AGENTS.md

## Cursor Cloud specific instructions

EMCargo is a single product with two dev processes: a Python 3.12 FastAPI backend
(`backend/`, port 8080) and a React/Vite/TypeScript frontend (`frontend/`, Vite dev
server on port 5173 that proxies `/api` → `http://localhost:8080`). Data is stored in
file-based SQLite; there is no separate database service. Standard commands live in
`docs/development.md`, `backend/requirements.txt`, and `frontend/package.json`.

Python dependencies are installed into a virtualenv at `/workspace/.venv` (the startup
update script creates it and installs `backend/requirements.txt`; frontend deps via
`npm install`). Use `/workspace/.venv/bin/python` / `/workspace/.venv/bin/uvicorn` /
`/workspace/.venv/bin/pytest` when running the backend.

Non-obvious gotchas for running/testing:

- **Env vars are NOT auto-loaded from the repo `.env` when running uvicorn from `backend/`.**
  Pydantic settings use `env_file=".env"` resolved relative to the current working
  directory, and there is no `backend/.env`. Pass config explicitly when running dev.
- **`DATA_DIR`/`DATABASE_URL` default to `/data` (not writable in this environment).**
  For local dev, point them at the repo, e.g. `DATA_DIR=/workspace/data` and
  `DATABASE_URL=sqlite:////workspace/data/emcargo.db`. Create `data/` if missing;
  the backend seeds catalogs on startup.
- **Admin bootstrap:** there is no public registration. The first admin is created on
  startup only if `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` are set. Log in
  with those credentials.
- **`CATALOG_AUTO_SYNC` defaults to `true`** and fetches reference catalogs from external
  URLs at every startup (with per-source HTTP timeouts). Set `CATALOG_AUTO_SYNC=false`
  for faster/offline dev startup — it falls back to the bundled seeds in `backend/seed/`
  and does not affect weight calculations.
- **Material recognition input format (important for manual testing):** the wizard's
  Excel/text import expects one line per row as `description | quantity | unit`
  (pipe- or tab-separated), with dimensions embedded in the description, e.g.
  `Stalen hoekprofiel 80x80x8x6000 | 8 | stuks`. Free-text descriptions without
  dimensions yield `status=error` and 0 kg. The steel regression set totals ~7534 kg.
- **Equipment library starts empty.** Seed tests use generic `DEMO-*` items; no
  operational equipment JSON ships with the repo.
- **`APP_SECRET_KEY=dev-secret` is not actually used.** It is on the published-secrets
  list, so the app replaces it with a generated key, stored in `DATA_DIR/secret_key` and
  reused from then on. That happens in every environment — `APP_ENV=development` only
  silences the CORS and admin-password warnings, it does not license signing tokens with
  a published string. Delete `DATA_DIR/secret_key` and you are logged out once.
- **Four interface languages.** Any new string goes into `frontend/src/i18n/nl.json`,
  `en.json`, `de.json` *and* `fr.json`, and any new `{nl, en}` block in the config or
  seed data needs a `de` and an `fr`. `backend/tests/test_languages.py` reads
  `SUPPORTED` and fails otherwise — it names no language, so a fifth is one line.
- **An error the user reads goes through `app/core/messages.py`.** It carries a code the
  interface translates, with an English fallback. A Dutch sentence in a `raise` fails
  `test_error_messages.py`.
- **Comments and docstrings are in English.** Everything a user reads is translated;
  everything a developer reads is English, across `backend/`, `frontend/`, `scripts/`
  and the workflows. Test docstrings stay long and explain *why* the test exists, with
  the real defect that provoked it — that is the project's institutional memory, and it
  is written in English since v1.46.0.

Example dev run (from repo root):

```bash
# Backend
cd backend
DATABASE_URL=sqlite:////workspace/data/emcargo.db DATA_DIR=/workspace/data \
  APP_ENV=development APP_SECRET_KEY=dev-secret \
  ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.local \
  ADMIN_PASSWORD=emcargo123 CATALOG_AUTO_SYNC=false \
  /workspace/.venv/bin/uvicorn app.main:app --reload --port 8080

# Frontend (separate shell)
cd frontend && npm run dev
```

- **Tests:** `cd backend && DATABASE_URL=sqlite:////workspace/data/emcargo_test.db DATA_DIR=/workspace/data /workspace/.venv/bin/python -m pytest`
- **Frontend tests:** `cd frontend && npm test` (Vitest + Testing Library).
- **Typecheck/build (no ESLint configured):** `cd frontend && npm run build` (`tsc -b && vite build`).

## Release handoff

Owner-created, non-draft `agent/release-vX.Y.Z` pull requests opt into automatic
release completion. The final CI job waits for backend, frontend, inventory and
both image checks, verifies the tested head and unchanged main, merges through
GitHub's normal rules, then explicitly dispatches CI and publication for that
merge SHA. Other branches and outside contributions never auto-merge.

After local verification and submitting the release PR, report its link and the
actual queued/running state. Do not spend a chat turn polling Actions for minutes.
GitHub owns the remaining wait; do not claim publication before it is verified.
If the finalizer fails after merging, rerun its job to resume dispatch. A moved
base or head requires updating the branch and testing again, not bypassing checks.
