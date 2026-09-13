#!/usr/bin/env python3
"""Extract numeric density facts from downloaded public source snapshots.

The input directory contains Ensinger's product JSON, CAMPUS density table
pages, CDA alloy pages and the FAO and ROCKWOOL PDFs. No source prose or
artwork is bundled. This extraction requires pdfplumber for the FAO tables.
"""
import argparse
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode

import pdfplumber

OUTPUT = Path(__file__).resolve().parents[1] / "backend" / "seed" / "density_sources"


def extract(root):
    facts, rejected = [], Counter()
    hashes = {}

    def read(path):
        raw = (root / path).read_bytes()
        hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        return raw

    def add(provider, identity, name, value, unit, category, **extra):
        facts.append({"canonical_name": f"{provider}_{identity}", "source": f"seed:{provider}:2026-09-13",
            "name": name, "category": category, "kind": "manufacturer_specification", "basis": "solid",
            "original_value": value, "original_unit": unit, "condition_key": "grade_as_reported",
            "source_record_ids": [identity], "notes": "Published grade-specific density; not a shipment or batch measurement.", **extra})

    for row in json.loads(read("ensinger-data.json"))["items"]:
        value = row.get("Density")
        if not isinstance(value, (int, float)) or not 0.1 <= value <= 5:
            rejected["ensinger_invalid_value"] += 1
            continue
        add("ensinger", row["id"], row["Title"], value, "g/cm3", "plastic",
            manufacturer="Ensinger", qualifier="Ensinger; " + row["BasicPolymer"],
            source_name="Ensinger", source_url="https://www.ensingerplastics.com" + row["DetailUrl"],
            source_row={k: row[k] for k in ("id", "Title", "BasicPolymer", "Density", "DetailUrl")})

    campus_ids = set()
    for path in sorted((root / "campus").glob("*.json"), key=lambda p: int(p.stem)):
        data = json.loads(read(path.relative_to(root)))
        table = data["data"]["data"]
        column = next(c for c in table["columns"] if c["fieldName"] == "Spt-578")
        assert column["tooltip"] == "Density [kg/m³] ISO 1183"
        for row in table["content"]:
            if row["id"] in campus_ids:
                rejected["campus_duplicate_id"] += 1
                continue
            campus_ids.add(row["id"])
            # The manufacturer's datasheet labels paired values "dry / cond".
            # Keep one explicit state per grade, preferring the dry specimen;
            # never average states or fill a missing value.
            raw = row.get("Spt-578") or ""
            parts = [v.strip() for v in raw.split("/")]
            if len(parts) not in {1, 2} or all(v == "-" for v in parts) or any(v != "-" and not re.fullmatch(r"\d+(?:\.\d+)?", v) for v in parts):
                rejected["campus_missing_or_ambiguous_state"] += 1
                continue
            index = 0 if parts[0] != "-" else 1
            value = float(parts[index])
            condition = "campus_as_reported" if len(parts) == 1 else ("campus_dry" if index == 0 else "campus_conditioned")
            if not 100 <= value <= 10000:
                rejected["campus_invalid_value"] += 1
                continue
            manufacturer = "; ".join(row.get("Placeholder-17-203") or [])
            if not manufacturer:
                rejected["campus_missing_manufacturer"] += 1
                continue
            add("campus", row["id"], row["materialname"], value, "kg/m3", "plastic",
                manufacturer=manufacturer, qualifier=manufacturer + "; " + row["Placeholder-12"],
                method="ISO 1183", condition_key=condition,
                source_name="CAMPUS — " + manufacturer,
                source_url="https://www.campusplastics.com/campus/datasheet/" + row["id"] + "?" + urlencode({"name": row["materialname"]}),
                source_row=row)

    # The density header fixes the physical state and original units. Do not
    # silently convert the adjacent dimensionless specific-gravity column.
    for path in sorted((root / "copper").glob("C*.html")):
        text = read(path.relative_to(root)).decode()
        code = path.stem
        match = re.search(rf'<th id="{code}-physical-Density-header">Density<span class="measurement-unit-label">([^<]+)</span></th>\s*<td[^>]*>(.*?)</td>', text, re.S)
        if not match:
            rejected["cda_no_density"] += 1
            continue
        unit, raw = match.groups()
        raw = html.unescape(re.sub(r"<[^>]*>", "", raw)).strip()
        if unit != "lb/cu in. at 68°F" or not re.fullmatch(r"0\.\d+", raw):
            rejected["cda_qualified_or_unsupported_value"] += 1
            continue
        add("cda", code.lower(), "Copper alloy " + code, float(raw), "lb/in3", "metal",
            kind="literature_reference", condition_key="alloy_20c", temperature_c=20,
            source_name="Copper Development Association — " + code,
            source_url="https://alloys.copper.org/alloy/" + code,
            source_row={"alloy": code, "density": raw, "unit": unit},
            notes="Published solid-alloy density at 68 degrees Fahrenheit, exactly 20 degrees Celsius.")

    # PDF cell boundaries keep density and specific gravity separate. Preserve
    # empty cells; dropping them would shift values into the wrong column.
    read("fao-density.pdf")
    fao_names = set()
    with pdfplumber.open(root / "fao-density.pdf") as pdf:
        for page_number in range(7, 23):
            for table in pdf.pages[page_number].extract_tables():
                for row_number, cells in enumerate(table, 1):
                    row = [cell.replace("\n", " ").strip() for cell in cells if cell is not None]
                    if len(row) != 5 or row[3] not in {"RC", "KEN", "USDA", "FNDDS 4.1", "S&W", "DK"}:
                        continue
                    name, density, specific_gravity, biblio, _ = row
                    if not re.fullmatch(r"\d+(?:\.\d+)?", density):
                        rejected["fao_range_or_missing_density"] += 1
                        continue
                    if name.casefold() in fao_names:
                        rejected["fao_duplicate_name"] += 1
                        continue
                    fao_names.add(name.casefold())
                    measured = biblio in {"RC", "KEN"}
                    identity = f"p{page_number + 1}_r{row_number}"
                    add("fao", identity, name, float(density), "g/ml", "food",
                        source="seed:fao:2.0:" + ("measured" if measured else "compiled"),
                        kind="measurement" if measured else "literature_reference", basis="effective",
                        condition_key="fao_measured_" + biblio.lower() if measured else "fao_compiled",
                        temperature_c=21 if biblio == "RC" else None,
                        source_name="FAO/INFOODS v2.0 — " + biblio,
                        source_url="https://openknowledge.fao.org/handle/20.500.14283/ap815e",
                        source_record_ids=[identity + ":" + biblio],
                        source_row={"page": page_number + 1, "row": row_number, "cells": row},
                        notes="Mass per described food volume, including spaces where present. Preparation and composition are part of the identity.")

    read("rockwool-slabs.pdf")
    with pdfplumber.open(root / "rockwool-slabs.pdf") as pdf:
        text = pdf.pages[2].extract_text()
        assert "Nominal density (kg/m3)" in text
        rows = re.findall(r"^(RWA45|RW[3456])\s+(45|60|80|100|140)\s+", text, re.M)
        assert len(set(rows)) == 5
        for name, value in sorted(set(rows)):
            add("rockwool", name.lower(), "ROCKWOOL " + name, float(value), "kg/m3", "insulation",
                condition_key="insulation_nominal", manufacturer="ROCKWOOL",
                source_name="ROCKWOOL RW Slabs, page 3",
                source_url="https://www.rockwool.com/siteassets/rw-uk/downloads/datasheets/rw-slabs.pdf",
                source_row={"page": 3, "product": name, "nominal_density_kg_m3": value})

    assert len({r["canonical_name"] for r in facts}) == len(facts)
    OUTPUT.joinpath("industrial_food_facts.json").write_text("[\n" + ",\n".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in facts) + "\n]\n")
    report = {"by_source": dict(Counter(r["source"] for r in facts)), "rejected": dict(rejected),
              "campus_product_ids_seen": len(campus_ids), "source_sha256": hashes}
    OUTPUT.joinpath("broad_import_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "source_sha256"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path)
    extract(parser.parse_args().sources)
