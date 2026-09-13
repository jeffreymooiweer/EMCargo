"""Inspect original NIST density records and retain one state per pure substance."""
import argparse
import hashlib
import json
import math
import tarfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
args = parser.parse_args()
OUTPUT = ROOT / "backend" / "seed" / "density_sources"
expected = "231161b5e443dc1ae0e5da8429d86a88474cb722016e5b790817bb31c58d7ec2"
with args.archive.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == expected, "NIST archive checksum differs"



def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != "tml_elements"}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def typ(value):
    return next((v for k, v in value.items() if k != "tml_elements"), "")


def is_direct_method(method):
    if any(word in method for word in ("calculat", "estimat", "predict", "simulat", "derived", "diffraction", "x-ray", "heat capacit", "dsc", "thermogram", "unknown", "none given")):
        return False
    return any(word in method for word in ("vibtub", "pycnom", "buoyan", "archim", "hybal", "msone", "mstwo", "vibrat", "densimet", "densitomet", "hydrostatic", "flotation", "mass", "gas displacement", "westphal", "graduated glass", "levitation", "mechanical oscillator"))


counts = Counter()
methods = Counter()
selected = {}
with tarfile.open(args.archive, "r|gz") as archive:
    for member in archive:
        if not member.isfile() or not member.name.endswith(".json"):
            continue
        raw = archive.extractfile(member).read()
        counts["files"] += 1
        if b"Mass density, kg/m3" not in raw:
            continue
        doc = json.loads(raw)
        compounds = {c["RegNum"]["nOrgNum"]: c for c in doc.get("Compound", [])}
        for block in doc.get("PureOrMixtureData", []):
            components = block.get("Component", [])
            if len(components) != 1:
                continue
            compound = compounds[components[0]["RegNum"]["nOrgNum"]]
            identity = compound.get("sStandardInChIKey")
            if not identity or not compound.get("sCommonName"):
                counts["missing_identity"] += 1
                continue
            props = {}
            for prop in block.get("Property", []):
                group = prop.get("Property-MethodID", {}).get("PropertyGroup", {}).get("VolumetricProp", {})
                if group.get("ePropName") != "Mass density, kg/m3":
                    continue
                methods[group.get("eMethodName", group.get("sMethodName", "unknown"))] += 1
                phase = prop.get("PropPhaseID", {}).get("ePropPhase")
                if phase not in {"Liquid", "Crystal", "Solid"} or prop.get("ePresentation") != "Direct value, X":
                    counts["unsupported_phase_or_presentation"] += 1
                    continue
                method = group.get("eMethodName", group.get("sMethodName", "")).casefold()
                if not is_direct_method(method):
                    counts["not_measured"] += 1
                    continue
                props[prop["nPropNumber"]] = (prop, phase)
            if not props:
                continue
            constants = {}
            for item in block.get("Constraint", []):
                constants[typ(item.get("ConstraintID", {}).get("ConstraintType", {}))] = item["nConstraintValue"]
            variables = {x["nVarNumber"]: typ(x.get("VariableID", {}).get("VariableType", {})) for x in block.get("Variable", [])}
            for point_number, point in enumerate(block.get("NumValues", []), 1):
                conditions = dict(constants)
                for value in point.get("VariableValue", []):
                    conditions[variables.get(value["nVarNumber"], "unknown")] = value["nVarValue"]
                temperature, pressure = conditions.get("Temperature, K"), conditions.get("Pressure, kPa")
                if temperature is None or pressure is None:
                    counts["missing_temperature_or_pressure"] += 1
                    continue
                if set(conditions) - {"Temperature, K", "Pressure, kPa"}:
                    counts["additional_condition"] += 1
                    continue
                if not 80 <= pressure <= 120 or not 0 < temperature < 2500:
                    counts["not_at_ordinary_pressure"] += 1
                    continue
                for value in point.get("PropertyValue", []):
                    if value["nPropNumber"] not in props:
                        continue
                    density = value["nPropValue"]
                    if not math.isfinite(density) or not 20 < density < 25000:
                        counts["invalid_density"] += 1
                        continue
                    prop, phase = props[value["nPropNumber"]]
                    counts["eligible_points"] += 1
                    key = (identity, phase)
                    uncertainty = value.get("CombinedUncertainty", {})
                    if isinstance(uncertainty, list):
                        uncertainty = uncertainty[0] if uncertainty else {}
                    expanded = uncertainty.get("nCombExpandUncertValue")
                    rank = (abs(temperature - 298.15), abs(pressure - 101.325), expanded / density if expanded is not None else 1, member.name, point_number)
                    if key in selected and rank >= selected[key][0]:
                        continue
                    selected[key] = (rank, {
                        "archive_member": member.name, "archive_member_sha256": hashlib.sha256(raw).hexdigest(),
                        "block_number": block["nPureOrMixtureDataNumber"], "point_number": point_number,
                        "compound": clean(compound), "component": clean(components[0]),
                        "citation": {k: v for k, v in clean(doc["Citation"]).items() if k in {"sDOI", "sTitle", "sAuthor", "sPubName", "yrPubYr"}}, "property": clean(prop),
                        "constraints": clean(block.get("Constraint", [])), "variables": clean(block.get("Variable", [])),
                        "point": {"PropertyValue": [clean(value)], "VariableValue": clean(point.get("VariableValue", []))}, "density_kg_m3": density,
                        "temperature_k": temperature, "pressure_kpa": pressure, "phase": phase,
                    })
records = [x[1] for _, x in sorted(selected.items())]
(OUTPUT / "nist_measurements.json").write_text(json.dumps(records, ensure_ascii=False))
report = {"counts": dict(counts), "methods": dict(methods), "selected_references": len(records), "unique_compounds": len({r["compound"]["sStandardInChIKey"] for r in records})}
(OUTPUT / "nist_selection_report.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2), flush=True)
