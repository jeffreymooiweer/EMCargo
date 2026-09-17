# v2.15.0 desktop visual review

Reviewed on 2026-09-17 in the visible Codex desktop browser, continuing the
[cloud handoff](https://chatgpt.com/share/6aabf083-b824-83eb-8707-f32ff8c48917?ogimg=plain).
The baseline is the published
[v2.15.0 release](https://github.com/jeffreymooiweer/EMCargo/releases/tag/v2.15.0),
commit `3fd0943ce3ced6ac1a90feb34e3b4b6864334921`, following merged
[PR 36](https://github.com/jeffreymooiweer/EMCargo/pull/36).

This review used a separate checkout and a local SQLite database with synthetic
records. The earlier desktop edits based on v2.14.1 were not carried over.
The three fixes below are prepared as patch release v2.15.1 on top of that
baseline. There are no design or styling changes. This document records the
local review; the release PR and GitHub Actions provide merge/publication status.

## Observed workflows

| Workflow | Browser result |
| --- | --- |
| Cargo distribution | Created two goods rows, 100 bolts and 100 nuts. Distributed both across three boxes: each box received 33 of each; one of each remained loose. |
| Nested cargo | Placed the three boxes on a Europallet and placed that pallet in an external vehicle. Unknown dimensions, registration and weights remained optional while editing. |
| Identity and persistence | Saved shipment `VISUELE-CONTROLE-2.15`, closed and reopened it. The vehicle, pallet and three boxes retained their individual codes and their nesting. Editing one box separated it from the identical group; matching properties grouped the boxes again. |
| Weight completion | Filled goods masses of 10 kg and 5 kg, pallet tare 25 kg and box tare 0.5 kg each. The resulting cargo total was 41.5 kg; the pallet contained 41.35 kg and the two loose pieces 0.15 kg. Unknown vehicle tare remained unknown. |
| Document recovery | Missing cargo facts blocked the CMR action. After the first fix below, both the document card and side panel described missing cargo weights and linked back to cargo. After completion, the document action became available. |
| Shipment list | Saved shipment appeared with open/template/document actions. A non-matching search showed an empty result with a clear-filters action and a visible input focus outline. |
| Own articles | Entered code, name and optional notes; switched to densities and back without losing the draft. Saved the article, searched for a non-existent article and restored the list. |
| Packaging library | Created a reusable crate with 600 x 400 x 300 mm dimensions and 2 kg tare. Search returned the correct model. Built-in model names and mobile actions remained legible. |
| Equipment | Created a vehicle with 8,000 kg transport weight. A pending alias was preserved by saving without separately pressing Add; searching for that alias returned the equipment. |
| Partial import | Imported a CSV with one valid machine and one row missing weight. The dialog reported one added and one skipped, identified line 3 and remained open with retry controls. |
| Trips | Added the saved ordinary shipment after fixing its import, saw the neutral no-dangerous-goods result, named and saved the trip. Invalid mass disabled saving and showed the correction. The final fix retained the open vehicle field and keyboard focus when correcting it. |
| DG review queue | Inspected the empty queue, status filter and recovery/navigation controls at 360 px. No populated DG approval workflow was exercised. |
| DGSA report | Inspected 2026 totals for one ordinary shipment and zero DG shipments, scope/source text, export buttons and the report-entry tab at 360 px. No report was submitted. |

Physical identities in the retained local sample:

- Vehicle: `CTU-01CFD311B041`.
- Pallet: `PAL-0511390F5575`.
- Boxes: `BOX-168CC5F71270`, `BOX-A78116B89EA7`, `BOX-A633C3A21C56`.

## Viewport and interaction evidence

The cargo workflow was inspected at 360, 390, 768, 1440 and 2560 CSS pixels.
Light and dark themes were exercised. This is a representative matrix, not a
claim that every screen was tested at every width and in both themes.

| View | Evidence |
| --- | --- |
| Nested cargo, 1440 dark | [Screenshot](../visual-review-evidence/02-nested-1440-dark.png) |
| Nested cargo, 360 dark | [Screenshot](../visual-review-evidence/03-nested-360-dark.png) |
| Mobile dialog and keyboard focus | [Screenshot](../visual-review-evidence/05-dialog-360-dark-focus.png) |
| Nested cargo, 390 light | [Screenshot](../visual-review-evidence/06-nested-390-light.png) |
| Nested cargo, 768 light | [Screenshot](../visual-review-evidence/07-nested-768-light.png) |
| Nested cargo, 1440 light | [Screenshot](../visual-review-evidence/07-nested-1440-light.png) |
| Nested cargo, 2560 light | [Screenshot](../visual-review-evidence/07-nested-2560-light.png) |
| Correct cargo document explanation | [Screenshot](../visual-review-evidence/09-export-reason-fixed-1440.png) |
| Saved cargo, 1440 light | [Screenshot](../visual-review-evidence/10-saved-cargo-1440-light.png) |
| Article search, 390 | [Screenshot](../visual-review-evidence/11-articles-empty-filter-390.png) |
| Packaging model, 390 | [Screenshot](../visual-review-evidence/12-packaging-model-390.png) |
| Equipment dialog, 390 | [Screenshot](../visual-review-evidence/13-equipment-dialog-390.png) |
| Partial equipment import, 390 | [Screenshot](../visual-review-evidence/15-import-partial-390.png) |
| Saved cargo, 390 dark | [Screenshot](../visual-review-evidence/16-saved-cargo-390-dark.png) |
| Saved cargo, 768 dark | [Screenshot](../visual-review-evidence/17-saved-cargo-768-dark.png) |
| Saved cargo, 2560 dark | [Screenshot](../visual-review-evidence/18-saved-cargo-2560-dark.png) |
| Reflow at 720 x 500 | [Screenshot](../visual-review-evidence/19-reflow-720x500-dark.png) |
| Invalid mass, 360 dark | [Screenshot](../visual-review-evidence/20-trip-validation-360-dark.png) |
| Saved trip, 360 dark | [Screenshot](../visual-review-evidence/21-trip-saved-360-dark.png) |
| DGSA totals and scope, 360 dark | [Screenshot](../visual-review-evidence/22-dgsa-report-360-dark.png) |
| DGSA form, 360 dark | [Screenshot](../visual-review-evidence/23-dgsa-form-360-dark.png) |
| Shipment search, 360 dark | [Screenshot](../visual-review-evidence/24-shipments-empty-search-360-dark.png) |
| Corrected mass with retained focus | [Screenshot](../visual-review-evidence/25-trip-corrected-focus-360-dark.png) |

Keyboard checks included opening a cargo action menu, tabbing through the unit
dialog to its Save action, closing the dialog, and verifying a visible focus
outline. The corrected trip field also retained focus after invalid-to-valid
typing. Wide article tables scrolled within their card. No persistent page-wide
overflow was observed in the inspected mobile screens; screenshots taken during
viewport transitions were not treated as defects.

## Fixes made from observed failures

1. **Misleading document blockage.** An incomplete cargo weight produced a DG
   classification explanation and an unavailable-validation-service message.
   The UI now uses the cargo failure's own explanation and recovery link. It
   avoids calling remote document validation for a known cargo-blocked payload;
   otherwise the normal validation path remains active.
2. **Ordinary shipments rejected by trips.** The actual ordinary shipment
   exporter omits empty DG and regulation arrays, while the trip importer
   required them. The reader now accepts omitted arrays only when the goods
   explicitly establish ordinary freight. Missing declarations with unknown
   goods, DG flags, detected UN numbers or malformed values remain rejected.
   Saved shipments and JSON imports use the same reader.
3. **Vehicle input collapsed during correction.** The vehicle disclosure was
   forced closed when an invalid mass became valid, hiding the focused field.
   Required facts now open the disclosure without forcing it closed afterwards.
   The final browser replay kept `18` visible with the input focused.

## Verification

| Check | Result |
| --- | --- |
| WizardPage, ShipmentPanel and DocumentWarnings tests | 44 passed across 3 files. |
| TripsPage and tripState tests, final run | 28 passed across 2 files, including correction/focus regression. |
| TypeScript and production build after all three fixes | Passed. Existing large-chunk advisory remains. |
| Git whitespace check | Passed. |

The new regression initially expected recalculation after returning to the exact
saved mass. The application correctly reused its matching saved assessment. The
test was corrected to use a different valid mass, and the final run above passed.
The first sandboxed build could not traverse a directory needed by Vite; the
authorized build with the needed filesystem access passed. Neither was a
production application failure.

The v2.15.1 release preparation subsequently ran the full frontend suite:
**603 passed across 76 files**. The versioned production build, all 12 release
automation tests, version consistency and the inventory check also passed
(218 components, zero issues). The inventory records the review screenshots and
the two version-only dependency declaration changes. Windows line endings in
unchanged inventory files were restored to their already recorded bytes.

The cloud's 3,105 backend passes belong to the release baseline and are recorded
in [the original QA handoff](qa-2.15.0-review.md). The complete backend suite was
not rerun locally for this patch; GitHub CI must run it before merging. No backend
application source was changed.

## Remaining limits

- **Printed CMR:** the clean local installation has no official CMR template.
  Validation returned `templates.missing`, and downloading returned 409. The
  interface displayed a generic export error. A rendered CMR has not been
  visually approved; repeat with the supported template installed. Other
  generated PDFs were not visually signed off here.
- **Actual browser zoom:** zoom shortcuts did not change the embedded browser's
  viewport or pixel ratio. The 720 x 500 check demonstrates narrow/short reflow,
  not verified 200% browser zoom. Actual zoom remains to be checked in a browser
  that supports it.
- **Additional workflows:** populated DG approval/rejection, QR login/scan
  restoration, storage-disabled UI, all specialised document types, and the
  full language matrix were not exercised visually in this session. Existing
  automated evidence does not replace these browser checks.
- **Minor copy:** the Dutch cargo view exposed `pcs` as the piece unit label.
  This was observed but not changed in this review.

The inspected cargo and ordinary-shipment tasks now have desktop browser
evidence. This is a scoped visual review, not complete product-wide acceptance
or a numerical usability score.
