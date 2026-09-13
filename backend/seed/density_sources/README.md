# Density source data

## GWDD original measurements

Fischer et al. (2026), *Global Wood Density Database v2.2*,
[fixed release 20815517](https://zenodo.org/records/20815517), CC BY 4.0.
Associated paper: [Beyond species means](https://doi.org/10.1111/nph.70860).
The authors' preferred dataset citation is DOI
[10.5281/zenodo.16919509](https://doi.org/10.5281/zenodo.16919509).

`gwdd_original_measurements.csv` is an attributed subset of the original
`gwdd_v2.2.csv`. It preserves record IDs, original values, measurement types,
moisture, tissue and the original bibliographic references. The full source
file's published MD5 was verified before extraction; its SHA256 is recorded
in `import_report.json`.

The application uses `value_reference`, multiplied by 1000 to express the
source density in kg/m³. It never uses `wsg`, `wsg_raw`, `wsg_est` or a
conversion coefficient. Only accepted species with `backtransformed=0`,
air-dry measurements at 8%, 12% or 15% moisture, or oven-dry measurements
are included. Basic density, experimental treatments, explicitly non-stem
material and bark are excluded. Heartwood is kept separate.

Records are grouped by accepted species, moisture state and tissue. The
reported value is the arithmetic mean of source records, rounded to 0.1
kg/m³. The minimum and maximum are the observed source range. This is not
a population estimate, confidence interval or guarantee for another load.
`record_count` counts source records, not individual trees: some original
records already aggregate multiple trees. Unknown source sample counts
are not invented. Groups with a max/min ratio above 1.75 and individual
values outside 80–1500 kg/m³ await individual review and are not included.
These conservative filters can exclude real unusual woods.

Original specimen locations are sometimes unspecified. No claim is made
that every record represents commercial timber. Scientific species names
are preserved, with the moisture state translated into each UI language.
Only the complete qualified label is eligible for automatic recognition;
an unqualified species name is not an instruction to assume a moisture state.

## Hapman bulk references

[Hapman Bulk Density Guide](https://hapman.com/resources-knowledge/bulk-density-guide/),
retrieved 2026-09-13. `hapman_bulk.csv` preserves source row IDs, product names
and the two published unit columns. Only factual product/density rows are
retained; no website text or artwork is redistributed. This does not imply
Hapman endorsement or an open license for the original website.

The lb/ft³ value is converted using the exact international pound and foot:
`0.45359237 / 0.3048³`. Rows whose two unit columns disagree beyond rounding,
rows with missing or invalid values, and ambiguous duplicate names are
excluded. The original product names are preserved to avoid inventing
translated grades or identities. This source explicitly publishes estimates;
they are labelled **published references**, never measured or certified values.
Particle size, moisture and compaction are incompletely specified. An actual
shipment can therefore differ, even when a copied source number is correct.

## NIST chemical measurements

[NIST ThermoML archive](https://data.nist.gov/od/id/mds2-2422), release
2020-09-30, under the [NIST open license](https://www.nist.gov/open/license).
Archive SHA256:
`231161b5e443dc1ae0e5da8429d86a88474cb722016e5b790817bb31c58d7ec2`.

`nist_measurements.json` retains 1,974 original points for 1,969 distinct
InChIKeys, with the original compound/sample, property, variables, constraints,
uncertainty, paper DOI and archive-member checksum. This is a selected subset,
not the entire archive. Paper abstracts and other properties are not copied.
Only pure-component, direct mass-density measurements with an identified
measurement method, explicit temperature and pressure between 80 and 120 kPa
are eligible. X-ray-derived densities, model calculations, estimates and
unidentified methods are excluded. Liquid and solid/crystal phases remain
separate. One point per compound and phase is chosen, nearest 298.15 K, then
101.325 kPa, then smallest reported relative expanded uncertainty. No state is
interpolated or averaged. Some real measurements are of molten substances or
pressed specimens; the recorded state and method remain part of the reference.

Re-extract with `python scripts/extract_thermoml_densities.py
/path/ThermoML.v2020-09-30.tgz`. The script checks the pinned checksum.

## Manufacturer and food facts

`industrial_food_facts.json` retains numeric source cells, identifiers and
links for the following sources, retrieved 2026-09-13:

| Source | Retained references | Basis and treatment |
| --- | ---: | --- |
| [CAMPUS](https://www.campusplastics.com/campus/table) | 8,426 | Named manufacturer grades, density according to ISO 1183, in kg/m³. |
| [Ensinger](https://www.ensingerplastics.com/en/shapes/products) | 177 | Named plastic product grades, source g/cm³ converted to kg/m³. |
| [Copper Development Association](https://alloys.copper.org/) | 130 | Solid alloy density at 68 °F = 20 °C, source lb/in³ converted exactly using the international pound and inch. |
| [FAO/INFOODS v2.0](https://openknowledge.fao.org/handle/20.500.14283/ap815e) | 352 | 202 original food measurements and 150 compiled density values for the stated preparation. |
| [ROCKWOOL RW Slabs](https://www.rockwool.com/siteassets/rw-uk/downloads/datasheets/rw-slabs.pdf) | 5 | Published nominal porous-board density; different thicknesses do not create extra grades. |

CAMPUS's 9,170 listed products are not all imported: missing or invalid
densities are excluded. `campus_density_schema.json` preserves the
manufacturer's table header establishing the order **dry / conditioned**.
One state is kept per grade: dry where available, otherwise the explicitly
conditioned value. Single values without a moisture qualifier remain labelled
as reported. Manufacturer and material designation are part of the product
identity. Neither colour aliases nor package dimensions are generated.
These are published manufacturer values, not measurements of a user's batch.

The CDA extraction includes available, unqualified numerical density rows
whose original units and temperature could be verified. It does not claim to
contain all 940 indexed alloys. Missing, footnoted or otherwise unresolved
values are excluded. The adjacent specific-gravity column is never silently
substituted for mass density.

The FAO PDF table contains **separate columns** for density and specific
gravity. Empty cells are preserved during extraction. Only the density
column is eligible; ranges never become invented midpoint densities.
RC denotes Charrondiere's own measurements at 21 °C and 393 m altitude; KEN
denotes the Kenyan project measurements at room temperature and 1,350 m
altitude. USDA, FNDDS 4.1, S&W and DK values are clearly labelled literature
references. ASI bulk estimates and the TB classroom compilation are excluded
from this expansion. The first eligible source row for each full food name is
retained; duplicate food names do not inflate the count. The value remains
that particular source record, not a mean of differing foods or preparations.

Only numerical facts, product identities and citations are retained from the
manufacturer and FAO sources, not their PDFs, prose or artwork. This does not
imply an open license to republish those original works or endorsement by
their authors. `broad_import_report.json` records downloaded source checksums
and exclusions. The input snapshots can be re-extracted with
`python scripts/extract_industrial_food_densities.py /path/to/source-directory`
(requires pdfplumber). Rebuild the bundled catalogue from the retained facts
with `python scripts/import_broad_density_references.py`.

## Installation and reproduction

The original 1,093 seed rows are retained. They have no row-level citations
and are shown as **unverified** in the source view; this expansion does not
retroactively certify them. Installation-specific edits are also never given
the provenance of a bundled value merely because the names match.

Run `python scripts/import_density_references.py --gwdd /path/gwdd_v2.2.csv
--hapman /path/hapman.html` with the pinned sources to rebuild the bundle
and extraction report, then run the broader importer above. The runtime
needs no internet access. Source
references also remain available when shipment history is disabled.
