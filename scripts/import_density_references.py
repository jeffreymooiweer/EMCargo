#!/usr/bin/env python3
"""Build traceable density references from pinned, locally downloaded sources.

Only original GWDD air/oven-dry measurements are eligible. Basic density,
model estimates, back-conversions, uncertain taxa and incompatible tissues
are deliberately excluded. Moisture states never get pooled together.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "backend" / "seed"
LB_FT3_TO_KG_M3 = 0.45359237 / 0.3048 ** 3
GWDD_URL = "https://zenodo.org/records/20815517"
HAPMAN_URL = "https://hapman.com/resources-knowledge/bulk-density-guide/"
LANGUAGES = ("nl", "en", "de", "fr")


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def wood_records(path: Path) -> tuple[list[dict], list[dict], Counter]:
    groups = defaultdict(list)
    rejected = Counter()
    for row in csv.DictReader(path.open(encoding="utf-8-sig")):
        if row["quantity_reference"] not in {"Airdry SG/Density", "Ovendry SG/Density"}:
            rejected["basic_density"] += 1
            continue
        if row["backtransformed"] != "0":
            rejected["backtransformed"] += 1
            continue
        if row["status_taxonomic"] != "accepted" or row["rank_taxonomic"] != "species":
            rejected["uncertain_or_non_species_taxon"] += 1
            continue
        if row["location_sample"] not in {"", "bole"} or "bark" in row["type_tissue"]:
            rejected["incompatible_tissue_or_location"] += 1
            continue
        if row["experiment"] in {"Yes", "1"}:
            rejected["experimental_treatment"] += 1
            continue
        moisture = "0" if row["quantity_reference"] == "Ovendry SG/Density" else row["moisture_airdry"]
        if moisture not in {"0", "8", "12", "15"}:
            rejected["unknown_moisture"] += 1
            continue
        try:
            density = float(row["value_reference"]) * 1000
        except (ValueError, TypeError):
            density = math.nan
        if not math.isfinite(density) or not 80 <= density <= 1500:
            rejected["value_requires_individual_review"] += 1
            continue
        if not row["source_long"].strip() or not row["id"].strip():
            rejected["missing_source"] += 1
            continue
        tissue = "heartwood" if row["type_tissue"] == "heartwood" else "wood"
        groups[(row["species"], moisture, tissue)].append(row)

    records, accepted = [], []
    for (species, moisture, tissue), rows in sorted(groups.items()):
        values = [float(row["value_reference"]) * 1000 for row in rows]
        if max(values) / min(values) > 1.75:
            rejected["group_requires_individual_review"] += len(rows)
            continue
        density = round(mean(values), 1)
        wood = {"nl": "hout", "en": "wood", "de": "Holz", "fr": "bois"}
        if tissue == "heartwood":
            wood = {"nl": "kernhout", "en": "heartwood", "de": "Kernholz", "fr": "duramen"}
        if moisture == "0":
            labels = dict(zip(LANGUAGES, (f"{species} — ovendroog {wood['nl']}", f"{species} — oven-dry {wood['en']}", f"{species} — darrtrockenes {wood['de']}", f"{species} — {wood['fr']} anhydre")))
        else:
            labels = dict(zip(LANGUAGES, (f"{species} — {wood['nl']}, {moisture}% vocht", f"{species} — {wood['en']}, {moisture}% moisture", f"{species} — {wood['de']}, {moisture}% Feuchte", f"{species} — {wood['fr']}, humidité {moisture}%")))
        canonical = f"gwdd_{key(species)}_{tissue}_mc{moisture}"
        records.append({
            "canonical_name": canonical, "category": "wood", "density_kg_m3": density,
            "density_min_kg_m3": round(min(values), 1), "density_max_kg_m3": round(max(values), 1),
            "condition": f"wood_mc_{moisture}", "language_labels": labels, "aliases": [],
            "source": "seed:gwdd:2.2:original", "notes": "Mean of original source records at the stated moisture. Observed range, not a guarantee for another load.",
            "provenance": {"kind": "measurement_mean", "basis": "solid", "source_name": "GWDD v2.2 (original measurements)", "source_url": GWDD_URL,
                "source_version": "2.2", "license": "CC-BY-4.0", "source_record_ids": [row["id"] for row in rows],
                "record_count": len(rows), "moisture_percent": int(moisture), "condition_key": f"wood_mc_{moisture}",
                "taxon": species, "tissue": tissue, "aggregation": "arithmetic_mean_of_source_records", "retrieved_at": "2026-09-13"},
        })
        accepted.extend({"canonical_name": canonical, **{k: row[k] for k in ("id", "species", "value_reference", "quantity_reference", "moisture_airdry", "backtransformed", "source_short", "source_long", "location_sample", "type_tissue", "plant_agg", "plants_sampled")}} for row in rows)
    return records, accepted, rejected


def bulk_records(path: Path) -> tuple[list[dict], list[list[str]], list[dict]]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", path.read_text(encoding="utf-8"), re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", cell)).strip() for cell in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) == 4:
            rows.append(cells)
    counts = Counter(key(row[1]) for row in rows)
    records, accepted, rejected = [], [], []
    for row_id, name, lb_ft3, g_cm3 in rows:
        reason = None
        try:
            density = float(lb_ft3) * LB_FT3_TO_KG_M3
            metric = float(g_cm3) * 1000
            if not math.isfinite(density) or not math.isfinite(metric) or not 5 <= density <= 15000:
                reason = "non_physical_value"
            elif abs(density - metric) > max(5.1, density * 0.015):
                reason = "unit_columns_disagree"
        except ValueError:
            reason = "missing_or_invalid_value"
        if counts[key(name)] != 1:
            reason = "ambiguous_duplicate_name"
        if name.casefold() in {"chlorine", "nitrogen", "oxygen", "hydrogen"}:
            reason = "ambiguous_physical_state"
        if reason:
            rejected.append({"source_record_id": row_id, "name": name, "reason": reason})
            continue
        # Preserve the manufacturer's product name; do not invent translations
        # or claim that a grade in the source is a different commodity.
        labels = dict(zip(LANGUAGES, (f"{name} — bulkstof", f"{name} — bulk solid", f"{name} — Schüttgut", f"{name} — vrac")))
        records.append({
            "canonical_name": f"hapman_{key(name)}", "category": "bulk_material", "density_kg_m3": round(density, 1),
            "condition": "bulk_as_reported", "language_labels": labels, "aliases": [], "source": "seed:hapman:2026-09-13",
            "notes": "Published bulk reference only. Moisture, particle size and compaction are not fully specified by the source.",
            "provenance": {"kind": "published_reference", "basis": "bulk", "source_name": "Hapman Bulk Density Guide", "source_url": HAPMAN_URL,
                "source_record_ids": [row_id], "record_count": 1, "original_value": float(lb_ft3), "original_unit": "lb/ft3",
                "condition_key": "bulk_as_reported", "retrieved_at": "2026-09-13"},
        })
        accepted.append([row_id, name, lb_ft3, g_cm3])
    return records, accepted, rejected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gwdd", type=Path, required=True)
    parser.add_argument("--hapman", type=Path, required=True)
    args = parser.parse_args()
    wood, observations, excluded_wood = wood_records(args.gwdd)
    bulk, bulk_rows, excluded_bulk = bulk_records(args.hapman)
    records = wood + bulk
    names = [record["canonical_name"] for record in records]
    assert len(names) == len(set(names)) and all(len(name) <= 128 for name in names)
    sources = SEED / "density_sources"
    sources.mkdir(parents=True, exist_ok=True)
    (SEED / "materials_measured.json").write_text("[\n" + ",\n".join(json.dumps(record, ensure_ascii=False, separators=(",", ":")) for record in records) + "\n]\n", encoding="utf-8")
    with (sources / "gwdd_original_measurements.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(observations[0]))
        writer.writeheader()
        writer.writerows(observations)
    with (sources / "hapman_bulk.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["source_record_id", "name", "lb_ft3", "g_cm3"])
        writer.writerows(bulk_rows)
    report = {"wood_references": len(wood), "wood_species": len({record["provenance"]["taxon"] for record in wood}), "wood_source_records": len(observations),
        "bulk_references": len(bulk), "total_added": len(records), "excluded_wood_records": dict(excluded_wood), "excluded_bulk_rows": excluded_bulk,
        "source_sha256": {"gwdd_v2.2.csv": hashlib.sha256(args.gwdd.read_bytes()).hexdigest(), "hapman.html": hashlib.sha256(args.hapman.read_bytes()).hexdigest()}}
    (sources / "import_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"excluded_bulk_rows", "source_sha256"}}, indent=2))


if __name__ == "__main__":
    main()
