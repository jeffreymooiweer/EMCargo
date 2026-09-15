# Historical distribution review

Prepared 2026-09-15. This is a remediation procedure, not a finding of liability.
Production replacement and a release gate reduce future exposure; they do not
remove earlier copies or decide whether an earlier distribution was lawful.

## Evidence record

Keep a private record for each relevant Git revision, release archive, container
digest/architecture, native installer and document/card pack. Record publication
date, contents/hashes, package versions, notices, source offers, download surface
and any actual commercial permission. Inspect an artifact's contents instead of
assuming its tag matches the current dependency file. Review public release
assets, workflow artifacts, GHCR tags/digests and externally mirrored copies as
separate surfaces. Download counts cannot identify all recipients.

| Material | Specific question | Available remediation routes |
| --- | --- | --- |
| PyMuPDF/MuPDF | What was distributed or modified, how was it combined with EMCargo, which license applied, and were corresponding-source/notice obligations met? | Establish compliant historic terms and source delivery where possible, or obtain an agreement covering the actual past uses; review termination/reinstatement before asserting a cure |
| Cantell extracts | Which copied expressions/database portions were distributed, in which territories, under what permissions? | Obtain appropriately scoped permission, replace remaining active occurrences, and assess corrective handling of historical assets |
| Publisher forms/model PDFs | Which exact blank forms were included, and did existing permissions cover recipients/channels? | Record actual permission or remove affected release assets after preserving evidence and selecting a reviewed replacement |
| Regulatory prose/images | Is there a publisher grant or an applicable statutory basis for this exact edition, translation and use? | Separate independently obtained facts from protected expression, obtain permission or replace the affected material |
| MIT-era EMCargo | Which original code was validly licensed under MIT and which later additions have different terms? | Preserve historical grants/notices; avoid promises of exclusivity over code already licensed permissively |

[AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html) distinguishes conveying a
covered work, mere aggregation, additional restrictions, license termination
and remote interaction with a modified version (sections 0, 5–8 and 13).
Neither installation alongside a GPL executable nor every network service
automatically makes all application code AGPL. Importing a library and
distributing a combined program require a fact-specific assessment. A private
commercial agreement also needs the correct component, versions and uses.

Do not delete tags, rewrite Git history, change repository visibility, contact
publishers, admit liability or promise compensation as an automatic consequence
of a scanner result. Prepare the exact proposed action and preserve evidence
first. A public corrective release can identify affected versions and changes
without publishing personal agreements or speculating about infringement.

Completion requires a recorded disposition of each affected distribution,
proof that any required notices/source/permissions were actually supplied, and
a repeat check of the remaining public surfaces. Retiring a manifest entry is
only evidence about the current tree.
