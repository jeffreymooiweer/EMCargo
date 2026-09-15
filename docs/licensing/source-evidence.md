# Source evidence and bounded reuse decisions

Reviewed 2026-09-15 against main `c5e702fb8099f573e48b2605f813f27339f9cc9d`.
These decisions concern the identified files, not a certification of EMCargo.
Hashes establish identity; a publisher's actual grant establishes licensed uses.
The machine-readable register remains authoritative for affected paths/channels.

## GWDD v2.2: documented for the separate measurement extract

The [versioned Zenodo record](https://zenodo.org/records/20815517) and its
[metadata API](https://zenodo.org/api/records/20815517) identify publication date
2026-06-23, version `v2.2 (with metadata)`, DOI `10.5281/zenodo.20815517` and
license identifier `cc-by-4.0`. This is evidence attached to the exact dataset,
not an assumption based on Zenodo hosting. The recorded upstream CSV MD5 is
`646454bd0ebcecb201fe081d0efde8fe`.

Decision: `backend/seed/density_sources/gwdd_original_measurements.csv` may be
distributed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en),
subject to attribution, license reference, change indication and preservation
of supplied notices. `licenses/GWDD-NOTICE.md` retains the named creators,
citations and modifications. The original data license is not replaced by the
application license. Standalone copies of the extract need that notice too.

This does not clear `materials_measured.json`: it also contains Hapman-derived
material, whose redistribution basis remains unresolved. Combining a licensed
dataset with an unresolved source does not transfer the first grant to the second.

## DGSA questions: documented Crown-authored adaptation

The [Department for Transport publication page](https://www.gov.uk/government/publications/carriage-of-dangerous-goods-annual-report-template)
was published 2026-01-15 and updated 2026-05-06. It links the
[DGSA report PDF](https://assets.publishing.service.gov.uk/media/694504759273c48f554cf647/dgsa-annual-audit.pdf),
internally dated December 2025. SHA-256 of the inspected 2,441,740-byte PDF:
`c82127f104f922d4acca58124fa09e3249de6a06f8a4be64205ce4226ecbd8bb`.
The page makes its content available under OGL v3.0 except where otherwise stated.

Decision: the Crown-authored structure/question adaptation in
`backend/app/config/dgsa_form.json` has a documented
[OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
basis. English questions were compared with the PDF; translations and
generalised national references are EMCargo changes. The full source PDF,
Crown branding and a general right to reproduce ADR publications are outside
this decision. OGL's third-party-rights exclusion remains in force; any newly
identified reserved material must be reviewed separately. Attribution and an
adaptation notice accompany the configuration and distribution notices.

## NIST ThermoML: better evidence, specific question still open

The [NIST record API](https://data.nist.gov/rmm/records/mds2-2422) identifies
*ThermoML / Data Archive*, NIST as publisher, public access, and the license URL
`https://www.nist.gov/open/license`. It lists archive
`ThermoML.v2020-09-30.tgz`, 189,433,115 bytes, SHA-256
`231161b5e443dc1ae0e5da8429d86a88474cb722016e5b790817bb31c58d7ec2`.
That fingerprint matches EMCargo's extraction provenance. NIST describes its
staff extracting measurements from journal articles; retaining their DOI is
useful provenance, not itself permission from every possible rights holder.

The [policy](https://www.nist.gov/open/license) distinguishes copyrighted
Standard Reference Data (15 USC 290e), other NIST employee works, and extramural
data. Its non-SRD section provides a worldwide reuse grant for NIST-held rights,
with acknowledgments and modification notices. A generic policy link does not
unambiguously establish which category this journal-derived archive occupies.

Decision: the two NIST measurement/catalogue files remain `unresolved` pending
confirmation of the applicable non-SRD grant and any source-data reservations.
Do not describe all NIST data as public domain. The project-generated selection
report is not automatically cleared through a database-wide relabeling either.
The permission question is now bounded to this archive/hash and the extracted
numerical observations, rather than all NIST products.

## UN/LOCODE: a promising grant, not a matched historical source yet

The current [official publications page](https://unlocode.unece.org/publications/)
links UN/LOCODE 2025-1 and states that UN/CEFACT standards use CC BY 4.0.
The [same site's terms](https://unlocode.unece.org/terms/) also contain general
personal/non-commercial restrictions without redistribution or derivative rights.
The source-specific open grant therefore needs to be identified and retained
with the actual release being used, rather than relying on the generic terms
or silently omitting the open-grant statement.

The existing `ports.json` is a transformed subset without a source edition/hash
in the file itself. Decision: keep its status unresolved while tracing its exact
source, or regenerate from an expressly licensed official release with recorded
hash, transformation and CC BY notices. That is a bounded route to clearance;
it is not a finding that UN/LOCODE generally cannot be reused. The general UNECE
Statistical Database license is for a different resource and was not substituted.

## Forms: use and redistribution are different decisions

| Form | Primary evidence | Decision for EMCargo |
| --- | --- | --- |
| CIM/CUV | [CIT forms page](https://www.cit-rail.org/en/freight-traffic/products/forms/) permits downloading, completing and saving the PDFs; the currently listed consignment forms are dated 2023-03-15 | Supports the described document use. No express permission to bundle a blank publisher PDF in public software distributions was established. Check compatibility with the historical model before any new import |
| IATA DGD | [IATA website terms](https://www.iata.org/en/terms/), sections 1–3, distinguish ordinary business use from reproduction/redistribution; [specific form page](https://www.iata.org/en/programs/cargo/dangerous-goods/shippers-declaration/) | Seek a specific grant for blank templates, adaptations, hosting and generated documents; do not infer it from download availability. Separately review the section 3 restriction on AI use before ingesting IATA material into an assistant |
| CMR | [IRU CMR model 2007](https://www.iru.org/resources/iru-library/iru-cmr-model-2007) identifies the model and its history | No software-redistribution grant established. Required transport information and the publisher's artwork must be assessed separately |
| AVC | [Stichting Vervoeradres](https://www.sva.nl/) publishes information about its terms and transport documents | Availability of AVC conditions is not a grant for the particular historic PDF. Identify its actual publisher and obtain model-specific terms |

All four originals remain retired from active distribution. A recorded local
import declaration documents the operator's basis; it does not create rights
or authenticate a publisher's permission. Exact historical profiles remain
distinct from newer publisher downloads.

## Regulatory extracts and earlier distributions

The [IMO IP policy](https://wwwcdn.imo.org/localresources/en/OurWork/Documents/POLICY%20ON%20INTELLECTUAL%20PROPERTY%20RIGHTS%20FOR%20THE%20IMO.pdf),
paragraphs 20–24, distinguishes publicly disseminated non-publication works,
commercial reuse, publications and a limited excerpt allowance. The allowance
is not a basis for reconstructing a publication through many small extracts.
IMDG/EmS prose and crops need a file-specific route; a publicly hosted mirror
does not supply the rights holder's permission. The blanket description of
EmS as freely distributable has therefore been removed.

UN/LOCODE, UNECE/OTIF editions, national translations and other regulatory
datasets remain subject to the source register. Official legal information,
editorial content, translations, database investment and artwork can have
different legal treatment. Keep that distinction in any statutory-basis review.

[Database Directive 96/9/EC, article 7](https://www.legislation.gov.uk/eudr/1996/9/article/7)
addresses substantial investment in obtaining, verifying or presenting contents,
and extraction/reutilisation of all or a substantial part. Facts being
unprotected individually does not decide database rights. Assess investment,
eligibility, protected expression, quantity/quality and repeated extraction;
do not claim every factual collection automatically has a database right.

The retired Cantell extraction remains an issue for historical Git revisions,
release archives and images. The same is true of earlier PyMuPDF distributions.
See [historical distribution review](historical-distributions.md). No historical
license breach is assumed proved, waived or cured merely by this update.

## Package decisions: ten additional grants, no image-wide clearance

The original packaged notices were read for alembic 1.14.0, anyio 4.15.1,
FastAPI 0.141.1, openpyxl 3.1.5, Pydantic 2.10.3, pydantic-settings 2.6.1,
PyJWT 2.13.0 and slowapi 0.1.9 (MIT), and httpcore 1.0.9 and httpx 0.28.1
(BSD-3-Clause). Their full notices already accompany `licenses/python/`.
The package policy now records these exact versions, detected metadata,
evidence files and notice obligations for the native channel.

This leaves 37 of the 50 Python distributions in the recorded runtime snapshot
awaiting package-specific review; all six recorded browser packages had been
reviewed previously. Native-library dependencies are distinct from a Python
wrapper's grant. A GPL executable in a container is not automatically a copyleft
license for the application; MPL/LGPL/AGPL and bundled native notices require
their actual scope and delivery obligations to be examined. The amd64 and arm64
image reports remain separate evidence and are not cleared by these ten entries.
