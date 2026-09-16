"""Container allocations keep tare, cargo mass and occupied transport volume separate.

Selections are shipment snapshots. Nothing here writes equipment master data or
interprets a computed gross mass as a verified SOLAS weighing.
"""
from __future__ import annotations

import math
from copy import deepcopy

from pydantic import ValidationError

from app.schemas.equipment import EquipmentSnapshot


def _positive(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def assess(lines: list[dict]) -> tuple[list[dict], list[str]]:
    result = deepcopy(lines)
    indexed = {line["line_id"]: line for line in result if type(line.get("line_id")) is int}
    errors: list[str] = []
    identities: set[int] = set()

    def flag(line: dict, code: str):
        if code not in errors:
            errors.append(code)
        line.setdefault("container_base_status", line.get("status", "ok"))
        line["status"] = "error"
        messages = line.setdefault("messages", [])
        if code not in messages:
            messages.append(code)

    for line in result:
        if "container_base_status" in line:
            line["status"] = line.pop("container_base_status")
            line["messages"] = [message for message in line.get("messages", []) if not message.startswith("equipment.")]
        if "cargo_output_description" in line:
            line["output_description"] = line.pop("cargo_output_description")
        # Repeated assessment must not consume the original package volume.
        if "package_transport_volume_m3" in line:
            line["transport_volume_m3"] = line.pop("package_transport_volume_m3")
        line.pop("container_load", None)
        if not line.get("include", True):
            continue
        equipment = line.get("equipment")
        if equipment:
            try:
                equipment = EquipmentSnapshot.model_validate(equipment).model_dump(mode="json")
                line["equipment"] = equipment
            except ValidationError:
                flag(line, "equipment.snapshot_invalid")
                continue
            if any(equipment.get(key) for key in ("asset_code", "container_number", "registration", "serial_number")):
                if equipment["equipment_id"] in identities or line.get("quantity") != 1:
                    flag(line, "equipment.single_asset")
                identities.add(equipment["equipment_id"])
        if line.get("equipment_role", "cargo") not in (None, "cargo", "container"):
            flag(line, "equipment.snapshot_invalid")
        if line.get("equipment_role") == "container":
            if not equipment or equipment.get("kind") != "container" or line.get("quantity") != 1 or line.get("container_line_id") is not None:
                flag(line, "equipment.container_invalid")
        parent_id = line.get("container_line_id")
        if parent_id is not None:
            parent = indexed.get(parent_id) if type(parent_id) is int else None
            if (parent is None or parent is line or not parent.get("include", True)
                    or parent.get("equipment_role") != "container" or parent.get("container_line_id") is not None
                    or not isinstance(parent.get("equipment"), dict) or parent["equipment"].get("kind") != "container"):
                flag(line, "equipment.container_missing")
            else:
                line["package_transport_volume_m3"] = line.get("transport_volume_m3")
                line["transport_volume_m3"] = 0
                description = line.get("output_description") or line.get("description") or ""
                line["cargo_output_description"] = description
                reference = parent["equipment"].get("container_number") or parent["equipment"].get("asset_code") or parent.get("description", "")
                line["output_description"] = f"{description} [{reference}]"

    for parent in result:
        if not parent.get("include", True) or parent.get("equipment_role") != "container":
            continue
        equipment = parent.get("equipment") or {}
        if not isinstance(equipment, dict):
            continue
        contents = [line for line in result if line.get("include", True) and line.get("container_line_id") == parent.get("line_id")]
        weights = [line.get("weight_total_kg") for line in contents]
        tare = parent.get("weight_total_kg")
        complete = _positive(tare) and all(_positive(weight) for weight in weights)
        cargo = round(sum(weight for weight in weights if _positive(weight)), 2)
        gross = round(tare + cargo, 2) if _positive(tare) else None
        parent["container_load"] = {"tare_kg": tare, "cargo_kg": cargo, "gross_kg": gross,
                                    "complete": complete, "line_ids": [line["line_id"] for line in contents]}
        if not complete:
            flag(parent, "equipment.container_weight_missing")
        if _positive(equipment.get("max_payload_kg")) and cargo > equipment["max_payload_kg"] + 0.01:
            flag(parent, "equipment.payload_exceeded")
        if gross is not None and _positive(equipment.get("max_gross_kg")) and gross > equipment["max_gross_kg"] + 0.01:
            flag(parent, "equipment.gross_exceeded")
    return result, errors
