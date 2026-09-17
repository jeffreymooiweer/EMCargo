# Workflow UX review

This records the non-settings workflow portion of the application-wide UX work.
It is a code and interaction review, not a claim of user-research validation.
The separate settings, account and shipment-editor reviews complete the app inventory.

## Screen and dialog inventory

| Surface | Completed change or reviewed outcome | Information retained |
| --- | --- | --- |
| Overview and ownership dialog | Removed introductory and completion instructions; empty results offer clear filters or a new shipment. Completion actions explicitly refer to office work. | Ownership, deadlines, missing facts, saved/error feedback and storage policy. |
| Transport-mode chooser | Removed explanatory paragraphs and per-mode descriptions; direct choice and import action remain. | Regulation codes and unavailable-mode status. Existing preferred-mode routing is unchanged. |
| Shipment list and selection | Empty results provide a direct recovery or creation action. Existing search, selection, deletion confirmation and pagination remain. | Counts, filters, responsibility, shipment/document status and permission boundaries. |
| Saved shipment detail | Removed renderer implementation prose; shows the saved cargo tree read-only. Canonical exported cargo is preferred to the editor snapshot. | Missing-document status, original metadata, physical unit IDs and expandable contents. |
| Trips, shipment picker and saved-trip list | Removed generic introductions and empty-state instructions; the vehicle mass field only shows an inline error when invalid. | Automatic checks, unknown mass, non-retained-trip status, stale saved assessment, ADR limits and unfinished checks. |
| Groupage route | Reviewed redirect to the single Trips workspace; no duplicate workflow introduced. | Existing selection/query parameters. |
| Own-goods library | Two primary text fields; optional metadata remains expandable. Direct import action supports keyboard use. Loading, failed, empty and filtered-empty states are distinct. | Existing DG/article metadata, active state, import row failures and unfinished edits across tabs. |
| Density library and source disclosure | Removed usage instructions. Search, categories and expandable individual sources remain. | Density, physical conditions, measurement/source qualifications and source links. |
| Equipment list and details | Removed page introduction and file-upload instructions; failed loading and unmatched filters have direct recovery actions. | Location, availability, dimensions, inspections, files, archive status and history. |
| Equipment editor | Read-only current location is displayed as a fact; editable search-name tags replace comma-separated instructions. Pending tag input is retained on save. | Model selection, manufacturer data, inspection records and optional transport configurations. |
| Equipment import | Replaced unlabeled toolbar-only actions with visible file/template buttons in the native dialog. Prevents dismissal during mutation; failed/partial imports remain visible and retryable. | Accepted file extensions, created/updated/skipped counts and translated row errors. |
| Equipment movement, inspections, model picker and action menu | Reviewed existing controls; no instruction overlay or new intermediate dialog added. | Concrete inspection results, model provenance, transfer records and optimistic-version checks. |
| DG review list and submitted detail | Removed queue instructions; empty state has a direct action. Shows submitted nested cargo read-only. | Submitted-version scope, internal-approval limits, specialist-only actions, required return reason and document findings. |
| DG compliance panels | Replaced generic instructions with the actual regulation codes. | Regulatory findings, incomplete/forbidden statuses, applicability limits and calculation/source facts. |
| DGSA figures and questionnaire | Removed general introductions and section usage text. Storage-disabled state uses the common component. | Questionnaire fields, quantity-band definitions, calculated-data scope, unknown quantities, report sources and signature status. |
| UN-card lookup | Removed generic page explanation; added loading state and retry after lookup failure. | Requested regulation, each requested UN number and explicit missing-card status. Authentication is enforced separately at route/API boundaries. |
| Shared storage-disabled state | Concise factual status, actual administrator restriction and direct relevant navigation. | Existing storage and role policy; no retention setting is changed. |

No instruction content was hidden through a CSS rule. Field names, accessible
names and actual errors remain available. Existing application styling and
responsive containers are reused.

## Concrete interaction changes

- A new ordinary library good exposes two text fields instead of ten. Creating
  it still uses the same open, enter and save flow. Advanced metadata requires
  one explicit disclosure; saving without opening it preserves every value.
- Equipment imports expose the file action directly inside their dialog. A clean
  import closes with the result; a partial import stays open at its actual errors.
- Failed list loading is no longer presented as an empty library. Retry and clear
  filters act in place without discarding the unfinished goods form.
- Search names support Enter, a visible add action and individual removal. The
  last name is included if the user saves without first pressing Enter.
- Submitted and saved packing trees expose their original IDs and quantities
  without offering packing edits. The viewer does not fetch mutable catalog data.

These are changes verified from rendered component behavior and code. They are
not timed usability measurements or a claim that external users require no help.

## Verification

A focused run passed **93 tests in 13 suites**, covering overview, shipments,
trips/groupage, goods, mode selection, DG review, DGSA, cards, equipment forms,
inspection forms and equipment imports. After the final search-name improvement,
the three affected suites passed **18 tests**, including its new regression.
There are **94 distinct tests** across those scoped suites.

New regression coverage checks:

- failed goods-list recovery and preserving a draft while clearing search;
- rejected spreadsheet rows staying visible;
- failed equipment uploads being retryable with the same file;
- partial imports preserving errors and pending imports preventing dismissal;
- card lookup retry preserving the regulation and explicit missing cards;
- canonical saved packing data taking precedence over stale editor state;
- submitted packing contents remaining inspectable without mutation actions;
- saving the pending final search name without discarding it.

The scoped whitespace check and current whole-project TypeScript check pass.
Release validation is performed during final integration because other work
packages modify the same build concurrently.

## Critical assessment

The code and tested interaction changes score **9/10** for this bounded work
package: ordinary instructions are removed, visible actions carry their meaning,
recovery paths are explicit and stored data/approval boundaries are preserved.
No database schema or mass-calculation behavior was changed by this package.

Visual sign-off is not asserted here. The prescribed cloud browser runtime
successfully initialized, but refused the local development URL with
`net::ERR_BLOCKED_BY_CLIENT`. No alternative browser mechanism was used. Full
viewport, text-zoom and light/dark screenshot verification therefore remains a
separate integration gate; unit tests do not substitute for that evidence.
