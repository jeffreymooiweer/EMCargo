# Licensing remediation

Authorized work: the six-phase plan agreed on 2026-09-15. Baseline v2.11.2,
commit `a12fc1933470ddb9b571f114c1b5dce88f9bc822`.

| Work package | Status | Acceptance |
| --- | --- | --- |
| Asset and dependency inventory | Implemented; rights questions explicitly open | Every tracked reference asset has an exact hash, source/evidence fields, status and channels |
| Production PDF migration | Implemented; regression checks | Completed forms and signatures render correctly; model selection cannot silently drift; production contains no PyMuPDF |
| Forms and reproduced regulatory content | Imports/migration implemented; publisher permissions open | A lawful template/import route and correct availability reporting; unresolved distribution is blocked |
| Cantell migration | Implemented | No active Cantell text/data fallback; missing necessary DG facts remain unknown and block required approval |
| Notices and contributor/brand policy | Notices and trademark policy implemented; CLA is a draft | Four UI languages, separate third-party notices, explicit draft/final distinction |
| Release gates and SBOMs | Implemented; unresolved rights and package obligations hold publication | Exact new artefacts are checked before publication, including container, native and generated-card outputs |

Changes are reviewed in the licensing remediation PR. A successful technical CI run is not
legal clearance. Unknown publisher rights remain explicit release blockers;
concept contributor agreements do not bind existing contributors. No historical
tags, releases or repository history are rewritten by this remediation.

The technical verification includes synthetic regression fixtures and local
comparison of the existing source forms. Third-party test PDFs are not added to
the public repository merely to demonstrate the migration.
