# Third-party notices

EMCargo's own code is source available under Apache License 2.0 with the
Commons Clause in [LICENSE](LICENSE). That combination is not an OSI-approved
open-source license. It does not relicense third-party software, data, fonts,
forms or regulatory texts. Their original rights and conditions apply.

## Data and assets

| Component | Source and terms | Distribution status |
| --- | --- | --- |
| Airport lookup data | [OurAirports](https://ourairports.com/data/), public-domain dedication | The source permits reuse; data carries no accuracy warranty |
| Railway station lookup data | [Trainline EU stations](https://github.com/trainline-eu/stations), [ODbL 1.0](licenses/ODbL-1.0.txt) | The derivative database is `backend/seed/locations/stations.json`, available under ODbL independently of the application |
| Port lookup data | [UNECE UN/LOCODE](https://unece.org/trade/uncefact/unlocode) | Precise redistribution conditions are recorded as unresolved pending source-specific review |
| Cal Sans | [Cal Sans](https://github.com/calcom/font), SIL Open Font License 1.1 | Preserve `frontend/public/fonts/cal-sans-LICENSE.txt`; the application license does not cover the font |
| Regulatory data, provision texts and label extracts | Source editions and hashes in `backend/seed/dg/sources.json` and the rights register | Public access, a citation and a matching hash do not themselves establish redistribution permission |
| CMR, CIM, IATA DGD and AVC form templates | Issuing bodies and source models described in `docs/data-sources.md` | Original PDFs are no longer bundled; local imports require an operator-recorded basis for use |
| Sixteen ADR/RID/ADN model PDFs | Edition/page fingerprints remain in the source register | Originals are no longer bundled; import locally or derive from a verified, independently obtained source volume |
| Cantell UN cards 2023 | Historical source of `card_data.json` | Seed, extracted prose, parser and runtime fallback removed; earlier Git/release copies need separate review |
| DVSA annual-report questions | The source file claims Open Government Licence v3.0 reuse | Exact source grant still to be confirmed; not attributed solely to the project |
| Densities, profiles and external reference catalogues | Source-level provenance in the seed files and `docs/data-sources.md` | Review the file-level register; a factual-data label is not a blanket rights clearance |
| Optional assistant runtime and model | llama.cpp (MIT), official Qwen3 model (Apache-2.0); exact pins in `assistant_runtime.json` | Independently downloaded components retain their publisher's terms and notices |

Contains information from Trainline EU stations, made available under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).
The distributed station subset is a derivative database. Its source is available
in this repository and through the application's legal downloads; using the
database does not put EMCargo's application source under ODbL.

## Software packages

Python, JavaScript and operating-system packages retain their individual
licenses. The installed-package SBOM and accompanying license notices are
generated from each built distribution. The browser build records the six
packages actually included in emitted chunks and ships their notices in its
`licenses/` directory. `licenses/javascript/` retains the reviewed source
copies. Python notices, including PDFium's bundled third-party notices, are in
`licenses/python/`. OS package licenses remain in the image (including
`/usr/share/doc`); their obligations require architecture-specific review. `compliance/python-dependency-baseline.json`
describes the initial audit environment and is explicitly not a production-image
SBOM. Build-only tools must not be mistaken for runtime dependencies.

PyMuPDF 1.25.5 is dual-licensed under AGPL-3.0 or an Artifex commercial
agreement. The migration removes it from the production dependency set.
Historical extractors and independent test rendering are inventoried separately;
placing a component in development requirements does not grant an exemption
from its license.

pypdf 6.17.0 and ReportLab 4.2.5 perform PDF filling and overlays. PDFium via
pypdfium2 5.13.0 performs isolated OCR rasterisation. Its Python bindings and
PDFium have their own grants, and the native build contains additional libraries:
[the publisher requires their license files to accompany binary distributions](https://pypi.org/project/pypdfium2/5.13.0/).
The wheel notices are included; a top-level BSD/Apache label is not a clearance
of every architecture's native library obligations. Certifi's MPL-covered data,
Pillow's embedded libraries and OS components also retain their original terms.

## Scope and unresolved permissions

The authoritative file list, exact hashes, channels and evidence references are
in `compliance/third-party-manifest.json`. The explanations and pending requests
are in [the rights register](docs/licensing/rights-register.md). An `unresolved`
entry is not permission to publish. The publication gate refuses affected new
images, native bundles and card sets until a lawful route is recorded.

Existing releases and historical Git versions need separate assessment.
Removing or replacing a file today does not erase its earlier distribution.
No affiliation, certification or endorsement by a cited publisher is implied.
