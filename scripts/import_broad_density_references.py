#!/usr/bin/env python3
"""Rebuild the broader density catalogue from the retained source facts.

No correlations, interpolated states, range midpoints or generated variants
are used. Run extract_thermoml_densities.py to refresh the NIST subset first.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "backend" / "seed"
SOURCES = SEED / "density_sources"
LANGUAGES = ("nl", "en", "de", "fr")
CONVERSIONS = {"kg/m3": 1.0, "g/cm3": 1000.0, "g/ml": 1000.0,
               "lb/in3": 0.45359237 / 0.0254 ** 3}


def nist_records():
    records = []
    for row in json.loads((SOURCES / "nist_measurements.json").read_text()):
        compound = row["compound"]
        identity = compound["sStandardInChIKey"]
        phase = row["phase"]
        temperature = round(row["temperature_k"] - 273.15, 6)
        pressure = row["pressure_kpa"]
        property_value = row["point"]["PropertyValue"][0]
        assert property_value["nPropValue"] == row["density_kg_m3"]
        method = row["property"]["Property-MethodID"]["PropertyGroup"]["VolumetricProp"]
        doi = row["citation"]["sDOI"]
        state_names = ("vloeistof", "liquid", "Flüssigkeit", "liquide") if phase == "Liquid" else ("vaste stof", "solid", "Feststoff", "solide")
        name = compound["sCommonName"][0]
        labels = {lang: f"{name} — {state}, {temperature:g} °C, {pressure:g} kPa"
                  for lang, state in zip(LANGUAGES, state_names)}
        uncertainty = property_value.get("CombinedUncertainty", {})
        if isinstance(uncertainty, list):
            uncertainty = uncertainty[0] if uncertainty else {}
        sample_number = row["component"].get("nSampleNm")
        sample = next((s for s in compound.get("Sample", []) if s.get("nSampleNm") == sample_number), {})
        record_id = f"{row['archive_member']}#data={row['block_number']}&point={row['point_number']}"
        records.append({
            "canonical_name": f"nist_{identity.lower()}_{phase.lower()}",
            "category": "chemical", "density_kg_m3": row["density_kg_m3"],
            "condition": f"{phase.lower()}_{row['temperature_k']:g}K_{pressure:g}kPa",
            "language_labels": labels, "aliases": [], "source": "seed:nist:thermoml:2020-09-30",
            "notes": "One original measured point for the identified pure-component sample. No interpolation or average across states.",
            "provenance": {"kind": "measurement", "basis": "liquid" if phase == "Liquid" else "solid",
                "source_name": "NIST ThermoML — " + doi, "source_url": "https://doi.org/" + doi,
                "source_version": "2020-09-30", "license": "NIST open data", "source_record_ids": [record_id],
                "record_count": 1, "condition_key": "sample_at_conditions", "temperature_c": temperature,
                "pressure_kpa": pressure, "phase": phase.lower(), "chemical_identity": identity,
                "method": method.get("eMethodName", method.get("sMethodName")),
                "expanded_uncertainty_kg_m3": uncertainty.get("nCombExpandUncertValue"),
                "sample": sample, "retrieved_at": "2026-09-13"},
        })
    return records


def published_records():
    records = []
    for row in json.loads((SOURCES / "industrial_food_facts.json").read_text()):
        density = row["original_value"] * CONVERSIONS[row["original_unit"]]
        assert math.isfinite(density) and 5 <= density <= 25000
        states = {
            "solid": ("massief", "solid", "massiv", "massif"),
            "effective": ("zoals beschreven", "as described", "wie beschrieben", "tel que décrit"),
        }[row["basis"]]
        qualifier = row.get("qualifier", "")
        name = row["name"] + (f" ({qualifier})" if qualifier else "")
        labels = {lang: f"{name} — {state}" for lang, state in zip(LANGUAGES, states)}
        records.append({
            "canonical_name": row["canonical_name"], "category": row["category"],
            "density_kg_m3": round(density, 6), "condition": row["condition_key"],
            "language_labels": labels, "aliases": [], "source": row["source"],
            "notes": row["notes"],
            "provenance": {k: v for k, v in row.items() if k not in {"canonical_name", "name", "category", "notes", "qualifier", "source", "source_row"}}
                | {"record_count": 1, "retrieved_at": "2026-09-13"},
        })
    return records


def main():
    path = SEED / "materials_measured.json"
    original = [r for r in json.loads(path.read_text()) if r["source"].startswith(("seed:gwdd:", "seed:hapman:"))]
    chemicals, goods = nist_records(), published_records()
    broad = chemicals + goods
    records = original + broad
    names = [r["canonical_name"] for r in records]
    assert len(names) == len(set(names)) and all(len(name) <= 128 for name in names)
    # Keep independently reviewable source bundles below repository transport
    # limits. The runtime loads all parts as a single reference catalogue.
    for name, rows in (("materials_measured.json", original),
                       ("materials_measured_chemicals.json", chemicals),
                       ("materials_measured_goods.json", goods)):
        (SEED / name).write_text("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows) + "\n]\n", encoding="utf-8")
    report = json.loads((SOURCES / "broad_import_report.json").read_text())
    report.update(broader_references=len(broad), by_source=dict(Counter(r["source"] for r in broad)),
                  by_kind=dict(Counter(r["provenance"]["kind"] for r in broad)),
                  total_sourced_references=len(records), total_including_legacy=len(records) + 1093,
                  nist_unique_compounds=len({r["provenance"]["chemical_identity"] for r in broad if r["source"].startswith("seed:nist:")}))
    (SOURCES / "broad_import_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
