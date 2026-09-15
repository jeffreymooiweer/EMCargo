# Rights register

Baseline: `a12fc1933470ddb9b571f114c1b5dce88f9bc822` (v2.11.2).
Technical inventory date: 2026-09-15. This register records evidence and open
questions; it is not a legal opinion or a representation that every source is
cleared. The machine-readable file inventory is
[`compliance/third-party-manifest.json`](../../compliance/third-party-manifest.json).

## Evidence and decisions

| Family | Evidence inspected | Outstanding decision |
| --- | --- | --- |
| Project software | [Current LICENSE](../../LICENSE); initial MIT release on 2026-07-07; Commons Clause added on 2026-07-11 | Previously granted MIT rights are not retroactively revoked; later additions must be evaluated under their applicable license |
| PyMuPDF | [Publisher's 1.25.5 licensing statement](https://pypi.org/project/pymupdf/1.25.5/) | Production replacement is a technical migration. Review historical distributions and remaining extractor/test use separately |
| IMO material | [IMO IP policy](https://wwwcdn.imo.org/localresources/en/OurWork/Documents/POLICY%20ON%20INTELLECTUAL%20PROPERTY%20RIGHTS%20FOR%20THE%20IMO.pdf), paragraphs 20-24; [website terms](https://www.imo.org/en/about/pages/imo-website-terms-and-conditions-of-use.aspx) | Identify the rules applying to each resolution, publication, factual extraction and reproduced text; commercial reuse needs specific attention. A freely accessible resolution is not blanket commercial permission |
| IATA form and guidance | [Shipper's Declaration downloads](https://www.iata.org/en/programs/cargo/dangerous-goods/shippers-declaration/); [website terms](https://www.iata.org/en/terms/), section 3 | Establish any specific overriding permission for repository, image and generated-output distribution. Download/ordinary business use does not establish those rights |
| IRU CMR / CIT CIM / sVa AVC forms | The exact source PDFs and form mappings in this baseline | Confirm the actual publisher/rightsholder of each file and obtain or locate the relevant software-redistribution grant |
| UNECE / OTIF / national regulatory texts and models | Edition/publisher/hash/page provenance in `sources.json` and the model manifest | Assess each publisher's grant and any applicable statutory basis, translations and embedded third-party material; do not infer permission from an official-domain URL |
| Cantell-derived content | The baseline `card_data.json` identifies Cantell IMDG UN cards 2023, contains 2,336 UN entries and 70 segregation provisions | Active seed, extracted prose, historical parser and runtime fallbacks removed. Unknown IMDG facts require a recorded source assessment and final server checks; historical distributions remain open |
| Trainline stations | [Upstream license](https://github.com/trainline-eu/stations/blob/master/LICENCE.txt) | ODbL attribution, derivative-database availability and separate licensing must accompany every relevant distribution |
| OurAirports | [Data download page](https://ourairports.com/data/) | Public-domain source statement recorded; no accuracy guarantee is implied |
| Cal Sans | [Bundled OFL](../../frontend/public/fonts/cal-sans-LICENSE.txt) | Preserve the font's notices and any reserved-name conditions |
| Other reference data and assets | Exact paths and hashes in the manifest, plus existing source annotations | Confirm the specific rights for the captured dataset/version; do not relabel unknowns as MIT, public domain or project-owned |

## Interpretation of status

- `project`: a project-authored declaration, configuration or owner-supplied
  asset; applicable third-party rights in referenced content are not granted.
- `documented`: a specific publisher grant or dedication has been identified
  and its conditions must be implemented for the listed channels.
- `unresolved`: provenance or a rights question remains open. Publication for
  any listed channel is blocked by the strict gate.
- `retired`: no active path or distribution channel remains. Historical rights
  and copies are still assessed independently.

Private agreements should be retained by the owner, not committed to a public
repository. Record their stable evidence reference, covered versions, recipients,
uses, expiry and any notice requirements. Do not mark an agreement executed
without the actual rights holder's assent.

## Scope of the inventory

Every tracked file under `backend/seed/`, `backend/app/config/`,
`templates/forms/`, `frontend/public/` and `scripts/un_cards/assets/` is accounted
for. Dependency declarations, the frontend lockfile and Dockerfile are hashed
as inputs; the actual resolved software is described by build SBOMs. The initial
Python dependency snapshot contains audit/test dependencies and says so.

Source archives, container/native releases, generated cards, workflow outputs
and subsequent optional downloads are separate publication surfaces. The
root software license does not override a source-specific restriction.

## Implemented boundary and remaining work

The current distribution no longer contains the four transport form PDFs,
sixteen regulatory model PDFs or the Cantell-derived seed. Twenty compatibility
profiles retain hashes/fields/page counts, not publisher artwork. Automatic
Docker/native upgrades preserve compatible local originals before replacing
the previous installation. Manual replacements require the documented local
migration step. No historical shipment files, tags or releases are deleted.

The remaining source datasets and regulatory label crops are inventoried,
including literal prose. They have not been declared universally reusable.
Full regulatory-volume transfers through workflow artifacts/draft releases
have a separate `regulations` channel and remain held. The gates control the
updated automation; they cannot revoke historical downloads, prevent an owner
from publishing outside those workflows, or make an already-public Git tree
private. Source remediation commits remain publicly visible.

The clean runtime snapshot contains 50 Python distributions and no PyMuPDF.
The compiled browser SBOM contains six actual bundled packages. These snapshots
do not represent a container's OS or every wheel architecture: CI produces
separate SBOMs for the built amd64 and arm64 images. Package review records
pin a specific package/version and detected license metadata; unresolved entries
are intentionally rejected for publication. Before reopening a channel, inspect
its complete report, satisfy the original notices/source obligations and record
the real evidence. Do not clear it merely to make CI publish.

The CLA remains a draft. Activating it, establishing the licensor's authority,
and obtaining publisher permissions require actual legal decisions and assent.
The prepared permission correspondence has not been sent.
