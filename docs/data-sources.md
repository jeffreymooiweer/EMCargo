# Data sources

EMCargo ships with reference data so that most of it works without internet access.
This page lists where each dataset comes from.

Only **factual data** is included — a UN number mapped to a code, a material mapped to a
density. Regulatory texts themselves are not in this repository.

That policy is unchanged, but one assumption behind it was wrong and worth correcting.
**ADR and ADN are published free of charge by UNECE, and RID by OTIF** — those three are
not paywalled. Neither, it turned out, is the IMDG Code: the consolidated volumes are
sold by the IMO, but resolution MSC.556(108) — freely distributed — states that "the
complete text of the IMDG Code is replaced by the following" and then prints it, which
is how the Dangerous Goods List was read in v1.48.0 and chapter 5.3 in v1.150.0. The
IATA DGR remains the one text this project cannot read. What kept the others out of
reach was a network policy in the development container, not their price.
`scripts/read_land_regulations.py` therefore reads them on a CI runner and prints the
provisions the application implements to the run log, so a rule can be checked against the
text. It commits nothing: the quoted text stays in the log, and only the values read out of
it — thresholds, limits, multipliers — are stored, each with the provision it came from.

Since v1.72.0 the documents themselves have a durable home: a **document store** outside
the repository (`/data/regulations`), registered file by file in
`backend/seed/dg/sources.json` with edition and sha256, managed by
`scripts/regulations_store.py`. See [docs/regulatory-database.md](regulatory-database.md)
for the architecture and the procedure when a new edition appears.

- [Goods and densities](#goods-and-densities)
- [Steel and timber profiles](#steel-and-timber-profiles)
- [Locations](#locations)
- [Dangerous goods regulations](#dangerous-goods-regulations)
- [Official form templates](#official-form-templates)
- [Which edition is running](#which-edition-is-running)
- [UN cards](#un-cards)

## Goods and densities

**1,093 goods** with densities, min/max ranges, search aliases and names in Dutch, English,
German and French, in `backend/seed/materials.json`. Each entry carries a **category** —
`liquid`, `agri`, `bulk_material`, `ore_mineral`, `metal`, `wood`, `general_cargo` and nine
others — which drives which units the goods step offers first.

| Category | Goods | Category | Goods |
|---|--:|---|--:|
| `agri` | 241 | `general_cargo` | 55 |
| `liquid` | 137 | `plastic` | 39 |
| `wood` | 111 | `waste` | 32 |
| `construction` | 103 | `bulk_material` | 28 |
| `metal` | 88 | `paper` | 21 |
| `chemical` | 67 | `insulation` | 20 |
| `ore_mineral` | 62 | `textile` | 20 |
| `food` | 61 | `concrete` | 8 |

The invariants are held by `backend/tests/test_materials_catalog.py`: no good appears
twice, no alias belongs to two goods, every good carries every supported language, every
category is one `units.py` knows, and every density lies inside its own min/max band.

**How a new good reaches an installation that already runs.** `seed_catalogs` fills the
materials table only when it is empty, so on its own it would never deliver anything to an
existing database. The startup catalogue sync does: it reads the same seed file and
*upserts*, so new goods are added and changed ones updated. Measured on a database seeded
with the old set, adding one good to the seed and restarting: `seed_catalogs` added
nothing, the sync added it. This is why `CATALOG_AUTO_SYNC=false` also freezes the goods
database at whatever it held on first start.

One thing the sync deliberately does *not* do: remove an alias. `merge_seed_material_aliases`
folds the aliases already in the database back into the record so that anything added
locally survives an update — which also means a **deletion in the seed never propagates**.
The stray `broccoli` alias on cauliflower, corrected in v1.42.0, therefore disappears on a
fresh install but stays on an existing one. It no longer does harm there: an exact match on
a good's own name now outranks another good's alias.

> **A correction.** This page used to claim that each entry states whether its figure is a
> bulk, solid, liquid or effective pallet density. It does not: there is no such field, only
> the category. That distinction matters — 20 m³ of gravel times a bulk density is right,
> 20 m³ of steel times a solid density is right, and 20 m³ of *stacked* timber is neither.
> Since v1.34.0 the application derives a density basis from the category and reports it as
> derived (`backend/app/services/units.py`), rather than treating it as something the data
> states.

**The form a good travels in is a choice, not an assumption.** Oak is 720 kg/m³ and steel
7850 — those are the densities of the *material*. A cubic metre of stacked boards, of
loose-tipped firewood and of a solid beam are three different weights of the same wood, and
the difference is air. Rather than hiding one average in the code, the line carries a
**form** and the form carries the factor:

| Form | Share of a cubic metre that is material |
|---|---|
| Solid / single piece | 1.00 |
| Sheets, lying flat | 1.00 |
| Bundled / packaged | 0.75 |
| Stacked | 0.65 |
| Loose bulk | 0.45 |

So 20 m³ of oak is 14,400 kg solid, 10,800 bundled, 9,360 stacked or 6,480 loose — the
shipper says which. The same choice applies to steel (plate against scrap), plastic
(granulate against regrind), paper and textile.

**Where the form deliberately does not apply.** For gravel, grain and ore the stored figure
is *already* a bulk density: those goods travel no other way and the database describes them
in that state. Laying a loose factor over that would subtract the air twice. The same holds
for liquids and for the effective per-pallet averages. The form is therefore only offered
where the stored number describes the substance itself.

These factors are practical figures, not standards. They live in `units.py` rather than in
the goods database because `seed_catalogs` only fills that database when it is empty — new
seed values never reach an existing installation, and a calculation that is only right for
new users is worse than none. A line with explicit length, width and height is weighed
solid regardless, because those dimensions describe actual material.

## Steel and timber profiles

Synchronised automatically at startup — no manual maintenance.

| Data | Source |
|---|---|
| UPN, IPE, HEA, HEB and similar | [steelprofiles_api](https://github.com/timskovjacobsen/steelprofiles_api) |
| SHS, RHS, CHS | [eurocodepy](https://github.com/kristapsfreibergs/eurocodepy) |
| Steel, timber and concrete densities | eurocodepy + EN 1991 reference values |
| Metal densities | Wikidata SPARQL |

Set `CATALOG_AUTO_SYNC=false` to use the bundled copies instead.

## Locations

Location autocomplete works fully offline from the seeds in
`backend/seed/locations/`.

| Data | Source | Licence |
|---|---|---|
| 4,500+ airports (IATA/ICAO) | [OurAirports](https://ourairports.com/data/) | Public domain |
| 17,500+ ports (UN/LOCODE) | [UNECE UN/LOCODE](https://unece.org/trade/uncefact/unlocode) | Freely reusable |
| 750+ European railway stations | [Trainline EU stations](https://github.com/trainline-eu/stations) | ODbL |

Address autocomplete is the one feature that calls out: it uses a Photon geocoder on
OpenStreetMap data (`photon.komoot.io` by default, configurable). Without internet it
goes quiet; typing an address by hand always works.

## Dangerous goods regulations

| Data | Source |
|---|---|
| Classification per UN number — class, classification code, packing group, labels, special provisions, LQ/EQ, packing instructions, the carriage provisions of columns (16)–(19), transport category, tunnel code, Kemler number | **ADR 2025, official Dutch edition**, table A of chapter 3.2, read by `scripts/extract_adr_table_a.py`. 3,158 rows over 2,345 UN numbers, no unreadable page. Checked against the alphabetical index of the same edition, which is that table set a second time: eleven of the thirteen compared fields agree on every UN number, class and transport category on all but eight. The book is not in this repository; only the derived table is |
| Proper shipping names, English | **ADR 2025, official UNECE English volume I**, table A column (2), read by `scripts/extract_adr_names_multilingual.py` — 2,344 UN numbers, 0.9987 agreement against the Dutch table. Until v1.89.0 this came from the 2023 export, which left fourteen entries without an English name and cut off a fifteenth, and which flattened the alternatives the ADR prints ("Gasoline" where the book has "MOTOR SPIRIT or GASOLINE or PETROL"). Where the volume breaks a name across the column and the two other English readings this repository holds — the export and the IMDG Dangerous Goods List — agree with each other against it, their hyphenation is taken: 49 names |
| Proper shipping names, German | **ADR 2025, official German edition** (Bundesamt für Strassen, document store), read by the same script — 2,346 UN numbers, 0.9996 agreement |
| Proper shipping names, French | **ADR 2025, official UNECE French volume I**, read by the same script — 2,346 UN numbers, 0.9996 agreement. The ADR is authentic in English and French alike, so this is a source text and not a translation |
| Which UN numbers ADR does not admit for carriage | The 2023 export, which marks them in words. The Dutch table writes a prohibition by leaving the row empty, and so writes "not subject to ADR" — the two cannot be told apart from the table alone. This is now the only thing that export supplies |
| The eleven Table A rows ADR 2025 added (UN 0514, 3551–3560) | **ADR 2025, official Dutch edition** — copied by hand in v1.52.0, each row read twice with the page recorded. Since v1.56.0 they come out of the machine reading like every other row, and the hand transcription is kept as a third reading to check it against |
| Proper shipping names, Dutch | **ADR 2025, official Dutch edition**, table A column (2), read by `scripts/extract_adr_names.py` and cross-checked against the alphabetical index of the same edition (2,345 UN numbers, 99.9% agreement). The book itself is not in this repository; only the derived names are |
| English proper shipping names, cross-check | 49 CFR 172.101 (eCFR / GovInfo, public domain) |
| UN packaging codes (107) | ADR 6.1.2 / 6.5.1.4 / 6.6.2 |
| EmS emergency schedules per UN number, and the schedule descriptions | IMO **MSC.1/Circ.1588/Rev.3** — EmS Guide (IMO circular, freely distributable) |
| Class segregation table and class 1 compatibility matrix | IMDG Code chapter 7.2, Amendment 40-20 — unchanged in 42-24 |
| Segregation exemption tables 7.2.6.3.1 – 7.2.6.3.4 | IMDG Code chapter 7.2, Amendment 40-20 — unchanged in 42-24 |
| Segregation groups per substance (SGG1–SGG18, 629 entries) | IMDG Code chapter 3.1, section 3.1.4.4 — unchanged in 42-24; the separate SGG1a marking for strong acids was dropped in 41-22 |
| Lithium and sodium-ion batteries in aviation | [IATA Guidance Document for Lithium Batteries and Sodium ion Batteries](https://www.iata.org/contentassets/05e6d8742b0047259bf3a700bc9d42b9/lithium-battery-guidance-document.pdf), 2026 edition |
| ADR 1.1.3.6 points, loading together 7.5.2, IATA Table 9.3.A, Q value | ADR 2025 (UNECE) and the IATA DGR |
| ADR 3.4.2/3.4.3 gross mass, table 3.5.1.2 E-code limits, 3.5.5 package cap, note (a) to 1.1.3.6.3 | Read from **ADR 2025 Volume I** (UNECE, ECE/TRANS/352) by `scripts/read_land_regulations.py` |
| RID 1.1.3.6.3 categories and 1.1.3.6.4 multipliers, RID 5.4.1.1.1 particulars | Read from **RID 2025** (OTIF, Appendix C to COTIF) by the same script |
| ADN 1.1.3.6.1 per-class exempted quantities and the 3,000 kg ceiling, 1.1.3.6.2 conditions | Read from **ADN 2025** (UNECE) by the same script |
| Stowage codes SW1–SW31, handling codes H1–H5, segregation codes SG1–SG78 with their descriptions | IMDG Code chapters 7.1.5, 7.1.6 and 7.2.8, via IMO resolution **MSC.556(108)** (adopted 23 May 2024), read by `scripts/extract_imdg_codes.py` |
| Dangerous Goods List per UN number — class, subsidiary hazards, packing group, special provisions, LQ/EQ, packing/IBC/tank instructions, EmS, stowage and handling (16a), segregation (16b), properties | IMDG Code chapter 3.2, Amendment 42-24, via IMO resolution **MSC.556(108)**, read by `scripts/extract_imdg_dgl.py` |
| Placarding and marking of cargo transport units at sea | IMDG Code chapter 5.3, Amendment 42-24, via IMO resolution **MSC.556(108)**, quoted by `scripts/read_land_regulations.py --quote sea_placarding` |
| Errata and corrigenda to Amendment 42-24, December 2025 | IMO, operator-supplied and pinned by hash as `imdg_corr_dec2025`. Read in full and checked against every extracted sea value in v1.149.0: none of its eleven corrections touches one |
| MSC.1/Circ.1498, informative material on the CTU Code | IMO, 16 December 2014, operator-supplied and pinned as `ctu_circ_1498`. Registered for provenance; explicitly informative, so nothing in it decides a document |
| Limited quantities at sea — package mark, unit mark, "LTD QTY" on the document | IMDG Code chapter 3.4, Amendment 42-24, read directly from the pinned `imdg_42_24` file (PDF pages 797–799) on 2026-08-26; values in `backend/seed/dg/package_marking.json` under `imdg.limited_quantities` |
| IMDG Code Supplement, 2020 edition | IMO, operator-supplied and pinned as `imdg_supplement_2020`. A text-preserving reconstruction (138 of 184 source images missing), so usable for text only. Registered for future reading; **no value is read from it yet** — the EmS source of record remains MSC.1/Circ.1588/Rev.3 |
| IMDG Amendment 42-24 changes over 41-22 | NCB Hazcheck, *IMDG Code Amendment 42-24 changes detailed summary*, October 2024 v1.0, and IMO **E&T 38/3/9** for the UN 1361 provisions |

## Which edition is running

`GET /api/regulatory` reports, per rule set, the edition, the source, the validity
period, known errata and a SHA-256 over every data file it uses. `GET /api/health`
carries a compact form of the same thing, so a bug report can say what the installation
actually computes with.

Two things it answers that documentation cannot:

- **Whether an edition has expired.** The IATA DGR is replaced every year and the 67th
  edition runs to 31 December 2026. From 1 January 2027 the manifest reports `iata` under
  `expired` instead of quietly carrying on. The UN cards (41-22) are already listed as
  expired — they are still used, but only for marine pollutant and bulk carriage.
- **Whether two installations hold the same data.** The `manifest_id` is a hash over all
  seed files together. Same id, same data.

Where the data lives:

| File | Contents |
|---|---|
| `backend/seed/dg/un_numbers.json` | 2,928 Table A rows over 2,336 UN numbers |
| `backend/seed/dg/adr_names_nl.json` | The Dutch proper shipping names, 2,345 UN numbers |
| `backend/seed/dg/adr_2025_additions.json` | The eleven rows ADR 2025 added, and the two it dropped |
| `backend/seed/dg/ems.json` | 2,338 UN numbers with fire and spillage schedules |
| `backend/seed/dg/segregation_groups.json` | 18 groups, 629 substance entries |
| `backend/seed/dg/packagings.json` | 107 UN packaging codes |
| `backend/seed/dg/imdg_42_24.json` | The IMDG Amendment 42-24 difference layer over the 41-22 data |
| `backend/seed/dg/imdg_codes.json` | 110 stowage, handling and segregation code descriptions |
| `backend/seed/dg/imdg_dgl.json` | The Dangerous Goods List: 2,860 rows over 2,347 UN numbers |
| `backend/seed/dg/rid_table_a.json` | RID 3.2.1 table A: 2,939 rows over 2,347 UN numbers, read from three independently typeset editions (Dutch and OTIF English as the readings, OTIF German arbitrating) |
| `backend/app/config/dg_compliance.json` | Segregation tables and compliance rules |
| `backend/app/config/dg_instructions.json` | Field help text |

Where internet is available, the UN lookup enriches entries live from an ADR 2025 source
and falls back to the offline database automatically.

## UN cards

Since v1.129.0 the UN cards are generated by EMCargo itself — one datasheet per UN
number and regime, from the measured seed tables listed on this page — and published as a
GitHub Release rather than committed or baked into the image. The note that used to stand
here about **2,849 third-party PDFs totalling 575 MB** in the repository and in every
`docker pull` is resolved: those files are gone, the image shrank by roughly nine tenths,
and an administrator imports the current card set into the data volume on request. The
pipeline is described in [un-cards.md](un-cards.md).

One inheritance from that third-party set remains, as data rather than as files:
`backend/seed/dg/card_data.json` was extracted from the Cantell IMDG UN cards (2023
edition, IMDG 41-22) by `scripts/extract_un_card_data.py` — marine pollutant status
(column 4), stowage codes (SW, 16a), segregation codes (SG, 16b) and bulk carriage for
2,336 UN numbers. The regulatory manifest carries that provenance, including that the
source PDFs are no longer bundled.

Since v1.23.0 columns 16a and 16b come from the Dangerous Goods List of Amendment 42-24
instead, so what the cards still supply is marine pollutant status and bulk carriage.
They no longer carry a class: nothing in the application read it, and the card parser had
it wrong for eleven substances (see the v1.27.1 entry in the changelog).

The extraction cross-checks its own EmS readings against `ems.json`, which comes from the
official EmS Guide and remains the authority: **2,282 agreed, none disagreed**.

## Official form templates

The filled-in official forms live in `templates/forms/`:

| File | Form |
|---|---|
| `cmr.pdf` | CMR consignment note, IRU model 2007 |
| `cim.pdf` | CIM consignment note, CIT CIM/CUV 2019 |
| `iata_dgd.pdf` | IATA Shipper's Declaration, open format |
| `avc.pdf` | AVC waybill, sVa / Stichting Vervoeradres |

If you fork this repository publicly, check the redistribution terms of each form first.

## Assistant runtime (optional, phase 23)

The AI assistant's model runtime ships nothing in the image. When an admin
enables it, two artifacts download once into `/data/assistant`, each verified
against the SHA-256 pinned in `backend/app/config/assistant_runtime.json`:

| Artifact | Source | License |
|---|---|---|
| `llama-server` (llama.cpp release binary, per architecture) | github.com/ggml-org/llama.cpp releases | MIT |
| `Qwen3-1.7B-Q8_0.gguf` | huggingface.co/Qwen/Qwen3-1.7B-GGUF (official publisher) | Apache-2.0 |

The pins are produced by the `pin-assistant-sources` workflow, which downloads
and hashes the artifacts on a runner and prints the digests to its log — the
same read-then-pin pattern the document store uses. A `null` pin means nobody
has hashed that artifact yet, and the in-app download refuses to run. The model
reads free text into structured fields only; every regulatory answer continues
to come from the sources above.

## Interface icons

### Current set (v2.2.0)

The interface and toast icons now use original, hand-written geometry from
`frontend/src/components/icons.tsx`, on one 24px grid with a 1.7px stroke.
Since v2.5.0 the compass in `AiIcon.tsx` is also original geometry. The
historical sources below remain documented, and the Legal page retains its
credits.

The mail copy glyph is rendered from the same current `CopyIcon` path by
`scripts/render_mail_icons.py`; the regression test checks the shared module.
Run the script with `--logo` to also regenerate the mail logo from
`frontend/public/emcargo.svg`. Both are attached PNGs, so mail clients do not
need SVG support or an outbound image request.

Since v2.11.1 the product mark is the owner-supplied logo used on the EMCargo
website, with its cropped bounds and SVG colour/alpha filter retained. The
mark and EM lettering use #245BEA in both themes. Cal Sans is bundled locally
with its SIL Open Font License in `frontend/public/fonts/cal-sans-LICENSE.txt`.
Its 700/1000 cap height aligns the mark with the capital E.

The default mail/document PNG is rendered with Sharp's SVG filter support;
MuPDF does not apply this filter. Run `npm ci` in `frontend` before using
`scripts/render_mail_icons.py --logo`, or run
`node frontend/scripts/render-brand.mjs` directly. Sharp is a build-time
dependency only; deployed servers use the committed PNG.

### Previous icon sets (before v2.2.0)

Most icons in the interface are drawn in this repository — the copy, delete,
pencil and chevron glyphs are a handful of hand-written SVG paths in the
component that uses them, which is why they share one line weight and one
viewBox.

One of them also travels outside the interface. Gmail strips inline `<svg>`
from mail, so the copy glyph beside a sign-in code is attached to the message
as a PNG, rendered by `scripts/render_mail_icons.py` from the same paths as
`ReviewLinesPanel.tsx` — a test asserts the two stay identical. Because the
drawing is the application's own, nothing about the credit below changes: the
eight remain eight.

Eight are the exception: the six in `frontend/src/toast/icons.tsx` for the five
kinds of toast and the close button, plus the import glyph in
`frontend/src/components/icons.tsx` and the assistant's mark in
`AiIcon.tsx`. They are third-party SVGs, supplied by the project owner, and
embedded as paths rather than fetched — so the application makes no outbound
request for them and they inherit the colour of whatever they sit in.

| Icon | Used for |
|---|---|
| check | a success |
| exclamation in a circle | an error |
| i in a circle | information |
| question in a speech bubble | a question waiting for an answer |
| open arc | working on it (rotated in the toast) |
| cross in a circle | the close button |
| document with an arrow | importing a spreadsheet |
| framed "AI" with a spark | the assistant |

They come from **Uicons by [Flaticon](https://www.flaticon.com/uicons)**, which
is free to use on the condition that the maker is credited. That credit is on
the application's own Legal page, where the people using it can see it — a
licence condition met only in a repository file is not met, since nobody
running the application ever reads that file.

All eight carry the same credit, confirmed by the owner against the set they
came from, so the one line on the Legal page covers them. Their exported markup
falls into several groups — some carry an Adobe Illustrator header and a
`Capa_1` layer, others an `id="Layer_1"` or an `id="Outline"` — which is the
set's different styles showing through, not different origins.

### The twenty-one added for the shell (v1.202.0)

The shell — one header, an icon rail, a mode switcher — needs glyphs the eight
do not cover, and the owner supplied twenty-one more from Flaticon. They live
in the same `frontend/src/components/icons.tsx`, stripped of the exporter's
furniture (XML declarations, Illustrator comments, layer ids, hard-coded
fills), each keeping the `viewBox` it was drawn in.

| Component | Used for |
|---|---|
| `HomeIcon` | a house — waiting for the overview of release 122 |
| `ShipmentsIcon` | the shipments list |
| `GroupageIcon` | groupage |
| `TripsIcon` | trips |
| `LibraryIcon` | the article library |
| `SettingsIcon` | settings |
| `UserIcon` | the user list |
| `LogoutIcon` | signing out — waiting for the folded rail's foot |
| `SearchIcon`, `PasteIcon`, `PlusIcon`, `ChevronDownIcon`, `MoreIcon`, `WeightIcon` | searching, pasting, adding, unfolding, the rest, mass |
| `CollapseIcon`, `MenuIcon` | folding the rail, the menu on a phone |
| `RoadIcon`, `RailIcon`, `SeaIcon`, `AirIcon` | the transport modes, in the switcher |

**Their provenance is not the eight's, and this says so rather than assuming
it.** Four of the twenty-one are drawn on a 24×24 `viewBox` the way a Uicons
export is; the other seventeen are not — they arrive on 32, 64, 128, 306.773,
426.667, 465.2, 512, 612 and one at `-42 0 512 512.002`, which is what
Flaticon's general library looks like and not what the Uicons picker produces.
So the Legal page names them on their own line, as *Icons by Flaticon*, and
does not extend the Uicons credit over them.

What is still open, and what it needs: Flaticon's free licence credits the
**author** of each icon, and the authors are not recorded here — the SVG files
carry no metadata and the download pages were not kept. The attribution lines
from those pages (Flaticon prints one per icon) are the missing piece; with
them, this table gains an author column and the Legal page gains the names.
Until then the credit says what is certain — where they came from — and this
paragraph says what is not.
