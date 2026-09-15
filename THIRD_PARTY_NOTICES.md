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
| DGSA annual-report questions | DVSA, December 2025 report, published by the Department for Transport; [official download page](https://www.gov.uk/government/publications/carriage-of-dangerous-goods-annual-report-template), [OGL v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | Source and grant verified for the adapted question configuration; Crown branding and original PDF are not bundled |
| Global Wood Density Database v2.2 | Fischer et al. (2026), [exact dataset](https://doi.org/10.5281/zenodo.20815517), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | The extracted measurements retain CC BY 4.0; the separate mixed GWDD/Hapman catalogue still requires review |
| NIST ThermoML archive, 2020-09-30 | [Dataset metadata](https://data.nist.gov/rmm/records/mds2-2422), [NIST licensing policy](https://www.nist.gov/open/license) | Exact archive and policy link verified; non-SRD status and relevant journal-derived rights still require confirmation |
| Densities, profiles and external reference catalogues | Source-level provenance in the seed files and `docs/data-sources.md` | Review the file-level register; a factual-data label is not a blanket rights clearance |
| Optional assistant runtime and model | llama.cpp (MIT), official Qwen3 model (Apache-2.0); exact pins in `assistant_runtime.json` | Independently downloaded components retain their publisher's terms and notices |

Contains information from Trainline EU stations, made available under the
[Open Database License](https://opendatacommons.org/licenses/odbl/1-0/).
The distributed station subset is a derivative database. Its source is available
in this repository and through the application's legal downloads; using the
database does not put EMCargo's application source under ODbL.

Contains public sector information licensed under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
The DGSA configuration adapts DVSA's *DGSA Annual Report for the Carriage of
Dangerous Goods*, December 2025, published by the Department for Transport.
EMCargo translates questions into Dutch, German and French and generalises
UK-specific references. This is an EMCargo adaptation, not an official
translation or endorsement. OGL exclusions, including third-party rights and
logos, remain applicable.

Wood measurements are adapted from Fischer et al. (2026), *Global Wood Density
Database v.2*, version v2.2 (with metadata). The [version DOI](https://doi.org/10.5281/zenodo.20815517)
identifies the source; the authors also request citation of the
[dataset family](https://doi.org/10.5281/zenodo.16919509) and their
[New Phytologist paper](https://doi.org/10.1111/nph.70860).
EMCargo selects measurements, converts units and derives catalogue values;
the original author list and transformation details are preserved in
[`licenses/GWDD-NOTICE.md`](licenses/GWDD-NOTICE.md).
The [CC BY 4.0 license](https://creativecommons.org/licenses/by/4.0/)
applies to the licensed data independently of EMCargo's Commons Clause.

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
