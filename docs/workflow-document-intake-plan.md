# Daily work and document intake

Accepted scope, 14 September 2026. Implementation targets v2.11.0.

## Product decisions

- Own goods describes only articles the organisation actually trades. Shared density
  references remain a calculation source, not its product assortment. Product weights,
  packaging, dimensions and identifiers are a subsequent assortment extension.
- Implement the actionable overview and local packing-list intake now.
- Keep visual load planning on the existing companion-module roadmap.
- Do not introduce a driver application or require carriers to adopt EMCargo.
- Build future connections on the existing IFTDGN export, shipment JSON and eFTI
  mapping. A generated CMR PDF is not a complete eCMR exchange service.

## 1. An overview that leads to the next action

Replace the count-first overview with a paginated work list: shipment, responsible
person, stated loading date, outstanding work and one primary action. Reuse the
existing shipment editor and specialist review screens to resolve work.

Separate attention, waiting for a specialist, today's loading work, ready documents
and completed office work. A date comes only from the explicit loading date. A
missing date never becomes today. A download does not prove departure or delivery.
Completion records an office action only and does not grant DG approval.

Index a small work summary when saving a shipment and backfill existing records on
upgrade. Listing must not read every saved document or recalculate the catalogue.
Keep assignment separate from authorship and reject stale concurrent changes.

Acceptance:

- Every task links to its source shipment or review and has one clear next action.
- Counts, filters, ordering and pagination cover the same authorised records.
- Pending, returned and approved DG submissions have distinct actions.
- Department visibility, private drafts and DG review permissions remain enforced,
  including DG review work while optional shipment history is disabled.
- Existing shipments, missing dates, deleted users and moved departments work.
- Assignment and completion retain changes on failures; editing content reopens work.
- Mobile cards and desktop rows share accessible actions in all four languages.

## 2. A packing list, PDF or photo becomes a reviewed proposal

Add document intake to the local assistant. Support text PDFs, scanned PDFs, JPEG
and PNG. Read text locally and use local Tesseract for images. Include OCR language
data in Docker and document native dependencies.

Bound file size, pages, rendered pixels, text length and processing time. Refuse
encrypted, malformed or unsupported documents clearly. Keep a source preview and
recognised text so OCR errors can be corrected; never silently drop pages or rows.

The installed local model proposes goods and whitelisted shipment facts. Document
instructions are data. Proposals carry source page/line excerpts; source spans and
units must support what the model proposes. Missing quantities, ambiguous per-piece
versus total weights and conflicting addresses remain questions. Regulatory choices,
approval and signatures are not inferred from document prose.

Acceptance:

- Text PDFs, scanned PDFs and phone-format images follow the real extraction path.
- A readable source and editable proposal appear before values enter the wizard.
- Goods and fields can be corrected or deselected, with their source visible.
- Stated weights stay stated weights; missing facts do not acquire invented defaults.
- Existing work survives cancellation, OCR/model failures, model removal and late replies.
- Accepted source excerpts travel with the wizard state. Original uploads and page
  previews are temporary and are not kept in server history.
- OCR and inference stay on the installation. Manual/spreadsheet entry remains
  available without an installed local language model.

## Delivery and verification

Run targeted permission, migration, workflow, OCR and UI tests. Exercise actual local
OCR with non-operational packing-list fixtures and inspect the source renderings.
Complete existing CI and container gates before merging and publishing v2.11.0.

## Integration follow-up

IFTDGN D.16A is already generated and parsed back before download. Versioned shipment
JSON and eFTI mapping exist. Next: a real counterparty's profile, structured addresses
and identifiers, transmission, acknowledgements, retries and idempotency. eCMR also
needs party-specific signing and document revisions. Establish that counterpart
before claiming an interoperable connection is complete.
