# Independent review: v2.15.0

Review date: 2026-09-17. The baseline was v2.14.1. This review covers the new
cargo model, its shipment integration, access boundaries and the related UX
changes. It is a code and automated-interaction review, not a user study or a
claim that every screen has received visual sign-off.

## Assessment

The implemented architecture supports mixed goods in nested packages, stable
physical identities, partial allocation, reusable equipment and direct loading
of loose or bulk goods. The versioned API is separate from a future placement
plugin. It does not introduce a placement engine or require a vehicle record to
create a shipment.

Scores are engineering judgements about the stated evidence. An average cannot
compensate for a failing invariant. The target for a completed dimension is
9/10, with no known material defect in that dimension.

| Dimension | Evidence and deductions | Assessment |
| --- | --- | --- |
| Fullstack cargo integration | Stable goods IDs survive positional calculations; cargo survives restore, final save, retries and transport-mode changes; strict wire payloads distinguish templates from units. The tests exercise the real wizard around a controlled cargo component boundary. | 9/10 for the reviewed integration, subject to the final release suite and build. |
| Database and identity | Decimal allocation checks, independent frozen shipment snapshots, permanent reusable identities, transactional conditional revisions, idempotent create retries, explicit deletion cleanup and archive protection for linked equipment. Effective legacy volume participates in revision checks. General form-field concurrency is outside this cargo revision boundary. | 9/10 for the reviewed cargo scope. |
| Access and privacy | Authentication, department and private-draft rules apply to the new cargo endpoints. Managers maintain templates; ordinary users can choose them. Assessment is stateless. QR lookup and PDF now require login and retain the intended scan destination. | 9/10 for the reviewed boundaries. This is not a security certification. |
| UX interaction design | One destination chooser, partial quantities, batch groups, unpack/undo, optional details, direct external/unknown transport and preserved field names/errors. App-wide instructions were reviewed across entry, shipment, libraries, work queues, account and administration. | 9/10 for the bounded code/component interaction review; visual usability is not signed off. |
| Visual/accessibility verification | Component tests retain accessible names and keyboard-triggered actions. No supported browser session could inspect the local running application. | Incomplete; no final numerical score or overall 9/10 claim. |

## Concrete defects found and corrected

- Calculation row positions could replace stable goods identities. Cargo now
  uses `cargo_goods_id`; old `line_id` is only a compatibility fallback.
- Legacy container tare could reappear as loose goods after unpacking or be
  counted twice after a template copy. Migration normalises carriers into the
  graph; unpack/undo preserves the physical ID and removes the old goods row.
- Measured gross could conceal unknown component masses. It is now a separate
  reading; an unknown calculated mass stays unknown, and dependent documents
  reject incomplete cargo while drafts remain editable.
- Direct goods assigned to a transport unit could disappear from occupied
  volume. Assessment now counts those allocations as well as unpacked goods.
- Effective legacy volume could change without advancing the cargo revision.
  The goods comparison now includes `package_transport_volume_m3` and the
  equipment role. A regression proves stale rejection and the next plugin
  response's updated volume and authoritative revision.
- Catalogue response metadata leaked into strict unit/template requests.
  Explicit payload allowlists now preserve each contract. Built-in models are
  copied before editing; archive requests carry the reviewed version.
- Restoring or selecting own equipment could mint a second physical identity,
  especially outside the first 200 reusable units. Exact equipment lookup now
  binds the existing ID while preserving the shipment's dimensions and contents.
- Reusable identities became unreachable after history deletion or disabling
  retention. Shared master metadata remains selectable without returning any
  shipment contents, parent links or loaded measurements. Linked equipment can
  be archived rather than deleted and replaced under a recycled integer ID.
- An older autosave could turn a kept shipment back into a private draft. The
  server rejects that downgrade; final save waits for in-flight autosave and
  cancels future draft timers. A rejected autosave no longer poisons explicit
  retry. Saved shipments retain their server identity across mode changes.
- Assistant replacements could remove allocated goods without using the normal
  deletion control. The wizard now rejects replacements that orphan or
  overallocate cargo.
- Snapshot-only cargo did not affect DG review fingerprints. The authoritative
  graph now travels with shipment and document inputs, and mismatches are
  rejected. Actual content changes invalidate approval; save revisions and
  moving between wizard steps do not.
- Anonymous QR routes bypassed the installation's login policy. Both API and
  application routing now require the usual account, while the feature toggle
  and post-login scan URL remain intact.

## Targeted verification

These are independently observed runs, not inferred from the presence of tests.
The final whole-project test/build and publication status belong to the release
handoff and must be reported separately.

| Tests | Observed result | Important coverage |
| --- | --- | --- |
| `backend/tests/test_cargo.py` and `test_cargo_access.py` | 34 passed | Nested mass conservation, decimal shares, missing facts, graph limits, legacy tare/volume, document projection, actual competing SQL sessions, retained revisions, identity reuse, retry/downgrade, template versions, authentication, department visibility, private drafts and retention gating. |
| `backend/tests/test_card_links.py` and `test_authenticated_installation.py` | 31 passed | Real-cookie login/logout boundaries for QR lookup/PDF, feature toggle and authenticated installation routes. |
| `frontend/src/pages/WizardPage.test.tsx` | 27 passed | Restored IDs and server revisions, blocked assistant deletion, legacy unpack/undo, failed autosave retry, final save ordering and saved shipment carry. |
| `frontend/src/App.test.tsx` | 16 passed | Login routing, scan destination restoration and existing route boundaries. |
| Cargo utilities, cargo state, cargo API and DG review hook suites | 22 passed | Mixed nesting, batch identities, partial moves, cloning, unknown mass, limits, legacy normalisation, API allowlists and semantic approval invalidation. |

The separate [workflow review](ux-workflow-review.md) records the non-settings
screen inventory and its component evidence. Batch tests establish bounded
identity creation and compact group rendering; they are not a browser latency
benchmark. Existing dependency deprecation warnings are not test failures.

## Final local handoff verification

The resumed release check on 2026-09-17 verified the final staged implementation
against the unchanged v2.14.1 base (`2b7b1b445fb6afb4077b0b7eee99646cc75a1f45`).

| Check | Observed result |
| --- | --- |
| Complete backend collection | 3,120 tests covered across the main run and a final-module rerun: 3,105 passed, 15 skipped, no uncovered collection entries. |
| Frontend suite | 599 passed across 76 files. |
| Final TypeScript and production build | Passed; Vite retains its existing large-chunk advisory. |
| Release finalizer tests | 12 passed. |
| Version consistency | All release versions match 2.15.0. |
| Registered third-party inventory | 217 components, zero inventory issues. |
| Staged whitespace check | Passed. |

The primary backend process returned zero, but its captured report stopped after
3,090 test results, without a session summary. This is not presented as a clean
single-run report. The two final modules were rerun with JUnit output: 47 passed
and three skipped, including 20 tests already recorded in the primary run.
Matching the ordered collection to the recorded progress and the JUnit test IDs
accounts for all 3,120 tests. GitHub must still run its complete suite against the
committed revision before merging.

The cloud browser retry again rejected the running local application with
`net::ERR_BLOCKED_BY_CLIENT`. The visual assessment remains incomplete. No overall
9/10 score or screenshot-based acceptance is claimed.

## Explicit limits and final checks

- **Cargo-specific concurrency:** the revision protects cargo topology and its
  underlying goods facts. Simultaneous changes to unrelated party, language or
  document form fields are not covered by a new application-wide revision model.
- **Document scope:** CMR/AVC, packing lists and delivery notes project outer
  packages and retain original declarations. Specialised document mappings
  that cannot express the new structure reject it explicitly; full details are
  in [cargo contract v1](cargo-contract.md). JSON keeps the complete hierarchy.
- **Visual verification:** the prescribed cloud browser rejected the local
  development URL with `net::ERR_BLOCKED_BY_CLIENT`. Consequently this review
  does not attest 360/390/768/1440/2560-pixel layouts, zoom, light/dark appearance,
  focus visibility or screenshots of complete user tasks. DOM tests do not
  substitute for that evidence. No unsupported browser workaround was used.
- **User effort:** the implemented controls reduce repeated entry and avoid
  mandatory drag-and-drop or nested dialogs. No timed before/after measurement
  or novice-user study was performed, so no numerical usability improvement is
  claimed.

The remaining remote release gates are CI against the actual committed revision
and both image builds. A queued CI run, a merged PR and a published release are
distinct states and must not be reported interchangeably.
