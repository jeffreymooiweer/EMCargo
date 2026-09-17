# Multimodal delivery implementation status

Release branch: `agent/release-v2.16.0`, based on version 2.15.1.
Prepared for the owner-requested v2.16.0 release. GitHub CI must pass before the
repository finalizer merges the release PR and dispatches publication.
See [the delivery workflow](deliveries.md) for the implemented behavior and
explicit limits.

## Implemented

- Separate shipment preparation and delivery execution, optional source modality,
  five modal leg types and multimodal itineraries.
- Exact reservations, whole-unit selection, actual source balances, shared CTU
  accounting and physical asset availability independent of office completion.
- Loading, partial receipts, damage, refusals, corrections and explicit empty-unit
  evidence; linked return/redelivery records and actual unpacking of ordinary
  returned goods before splitting their original packages.
- Adjustment of future draft quantities after a settled transfer shortage,
  preserving the already executed leg and its document fingerprint.
- Mode-specific checks, explicit qualified reviews for gaps, mandatory source
  verification, and conservative blocking of partial/ambiguous DG declarations.
- Draft preparation outputs, versioned immutable final documents, multi-leg
  contract scope, approved external files and identical-byte download/mail bundles.
- A stateless single-leg final-document path with actor/input-bound review tokens.
- Named task assignments, combined roles, multiple selected shipments per grant,
  verified external invitations and server-enforced scope/expiry.
- Operational reporting, dashboard/shipment links, retention counts and deletion,
  legacy read-only trip conversion, safe concept-only delivery archive import.
- Four interface languages, mobile navigation, explicit status wording, preserved
  failed receipt input and confirmation before discarding document changes.

## Verification

- Mobile dark mode: plan/release, document issue, load, partial and complete
  receipts, office closure, history and operational report.
- Additional mobile journey: select one of two closed boxes, save five goods,
  load five, receive four, settle one missing good, explicitly record the empty
  box; receipt history remains four rather than inventing the fifth.
- Desktop light mode and modal-preference-free shipment preparation inspected.
- Onward journey in the browser: ten loaded, eight received, two settled as a
  shortage; save eight for the next draft leg with a shared CTU, plan/release,
  load/receive eight and verify physical CTU release. Executed quantities stay
  fixed. History identifies the relevant leg and route for each event.
- Recipient desktop/mobile portal: only the assigned delivery appears, planning
  controls stay hidden and direct navigation to another delivery is refused.
  Assignment form and Tab/Enter navigation to the history were inspected.
- Focused backend suites passed for assignment/session isolation, reservations,
  document identity/scope, retention, signatures, return packing and shared CTUs.
- Full backend run: 3,143 passed, 21 skipped. The later onward-transfer and
  assignment/import refinements passed 238 focused tests, including documentation,
  languages, errors and unused-code checks.
- Full frontend run: 600 passed across 78 files. Delivery/temporary-delivery tests
  and the production build also passed after the final portal adjustments.
- An order-dependent work-queue assertion now selects the intended kept shipment
  by ID rather than assuming a private preparation draft cannot appear first.
- Windows-only test execution issues were isolated: the symbolic-link test passes
  with the needed local rights, and both native scripts parse with Git Bash.
  The successful full run used those capabilities without deselecting tests.
- Third-party inventory: 218 registered components, no issues. Package files had
  only CRLF/LF drift; normalization restored the existing verified hashes.

## Before publication

Implementation and the listed local verification are complete. Browser coverage
is a targeted workflow check, not an exhaustive accessibility audit. True 200%
browser zoom could not be verified with this browser's controls. Invitation and
document email behavior was tested with mocked delivery; no real external email
was sent. Optional official-template tests account for the existing skipped tests.

Release notes, version declarations and the release inventory accompany this
release branch. Local release checks precede submission of the release PR.
The PR and GitHub Actions provide the authoritative merge/publication status;
this implementation report does not itself assert that publication succeeded.

The implementation deliberately does not infer DG package splits, silently open
closed units, replace missing source stock, or treat unsupported modal checks as
an automatic approval. Temporary deliveries currently cover one leg and one
source shipment; external execution requires retained delivery records.
