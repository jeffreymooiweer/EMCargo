# The UN card pipeline

EMCargo generates its own UN cards: one A4 datasheet per UN number **and**
regime, named `UN1203_ADR.pdf`, `UN1203_ADN.pdf`, `UN1203_IMDG.pdf` and so
on. Every value on a card comes from the measured regulatory tables in
`backend/seed/dg/` — the same tables the compliance checks run on — the
hazard label artwork — the environmentally hazardous mark of 5.2.1.8.3
included — is cut from the official UNECE English ADR 2025, and the
provisions behind the coded columns are printed verbatim from the official
editions: ADR's V/CV/S (7.2.4, 7.5.11, 8.5), ADN's additional requirements
of 7.1.6 (VE, LO, HA, CO, ST, RA, IN) and the IMDG stowage, handling and
segregation code descriptions (7.1.5, 7.1.6, 7.2.8). No language model, and no hand, ever fills in a regulatory
value: a modality without a measured table (ICAO/air, for want of a
freely licensable source) **fails honestly** instead of borrowing another
regime's data. The RID joined the measured modalities in v1.132.0: its
table A is read from three independently typeset editions — the Dutch and
the OTIF English as the two readings, the OTIF German arbitrating every
cell where the two disagreed (`backend/seed/dg/rid_table_a.json` records
how many, and which way).

## Where things live

| Piece | Place |
|---|---|
| Generator | `scripts/un_cards/` (`generate.py`, `render.py`, `labels.py`, `validate.py`, per-modality adapters under `sources/`) |
| Source configuration | `scripts/un_cards/generator_config.json` — which seed backs which modality, plus the generator version |
| Label artwork | `scripts/un_cards/assets/labels/` — cut from ADR 5.2.2.2.2 (and the 5.2.1.8.3 mark, masked to its own diamond) along the measured boxes in `label_crops.json` by `scripts/extract_adr_label_models.py`. Two figures of chapter 5.2 sit beside the label models there for the package label sheet: `BATTERY_SYMBOL.png`, the symbol alone of Figure 5.2.1.9.2, and `ORIENTATION.png`, the framed arrows of Figure 5.2.1.10.1.2. Their boxes were found by `scripts/measure_figure_crops.py`, which sketches candidates as text so a run log can show what it found |
| Provision texts | `backend/seed/dg/adr_provision_texts.json` and `adn_provision_texts.json` (extracted by their `scripts/extract_*_provision_texts.py`), plus the IMDG code descriptions already measured in `imdg_codes.json` |
| Generated cards | **Not in the repository and not in the image.** A GitHub Release tagged `un-cards-YYYY.MM.DD-N`, assets the generated ZIP asset, `manifest.json`, `generation-report.json` |
| Runtime store | `<data-dir>/un-cards/` on the persistent volume, filled by an administrator |

## Setting a new regulation edition

The editions are **not** typed anywhere in the generator: each seed records
the edition it was read from, and the manifest repeats that value, so the
two cannot disagree. Bringing in a new edition means re-running the
extraction workflow that produces the seed (see `docs/dg-coverage.md` for
which workflow reads which table), letting its two-reading checks pass, and
then regenerating the cards. Only one modality changed? Regenerate all the
same — the release always carries one coherent complete set, so the
application never has to stitch partial packages together.

## Document style

Newly generated cards share the application PDF theme in `backend/app/pdf_style.py`
and its bundled fonts. All available EN/NL/DE/FR names are printed, long provisions
continue across pages and full provenance appears in a flowing source section.
Hazard-label artwork is unchanged. Font licenses travel in the package's
`licenses/` directory alongside its notices and inventories.

Existing installed cards keep their original appearance until an administrator
imports a regenerated set. Source, artwork and dependency publication gates still
apply; a style update does not clear any unresolved redistribution rights.

## Running the generator

Manually, from a checkout (test mode, nothing published):

```bash
python scripts/un_cards/generate.py --scope single --un 1203 --out /tmp/cards
python scripts/un_cards/validate.py --dir /tmp/cards
```

Merging changes to the generator, its measured source tables, its label artwork
or its shared PDF theme into `main` triggers the card workflow. Generation and
publication require the existing rights gate to pass; unresolved rights hold the
workflow before it distributes a new set. Application-only changes leave the existing set in place. A failed
generation or validation stops publication. Card releases never replace the
latest application release, which the in-app updater relies on.

For a manual run, use **Generate UN cards** (`workflow_dispatch`), inputs

- `scope`: `single` (with `un_number`, for a quick look) or `all`;
- `modalities`: comma-separated subset, default all five;
- `publish`: off = the result is uploaded as a workflow artifact for
  inspection; on (with `scope=all`) = a GitHub Release is created.

The workflow validates before it publishes, and validation is strict:
filename ↔ UN ↔ modality agreement, `%PDF` header, SHA-256 against the
manifest, the UN number and the EMCargo footer present in the text, no
third-party branding anywhere. A set that fails does not ship.

## How an installation gets the cards

**Settings → UN Cards** (administrators only) shows what is installed —
generation date, per-regime counts and editions, total size, storage
location — and offers:

- **Check for a new set**: reads the release feed, only when clicked;
- **Download & import latest**: the server fetches
  the generated ZIP asset from the pinned EMCargo release feed (never
  a caller-supplied URL), verifies and installs it;
- **Import from ZIP**: the same package uploaded by hand, for
  installations without outbound access — identical verification;
- **Remove local cards**: deletes the set; the wizard then says no cards
  are available instead of guessing.

Every import is atomic: the archive's member names must match exactly the
shapes the generator produces (which rules out Zip Slip outright), sizes
are capped, every card is hashed against the packaged manifest, and the
verified set replaces the old one in a single rename. A failed import — a
tampered file, a truncated download, a full disk — leaves the previously
working set untouched.

## How the app serves them

The wizard's UN card download — and, since v1.130.0, the export step's
**Download all as ZIP** archive — bundles exactly the cards for the declared
substances on the regimes the journey touches (`profiles` in the request);
a UN number that has no card on a requested regime is named as missing, and
no other regime's card is substituted — the regimes print different
obligations. The whole feature stays out of the way when no set is
imported, and the **Offer UN cards** switch in the instance settings turns
it off entirely.
