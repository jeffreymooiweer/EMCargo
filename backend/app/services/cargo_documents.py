"""Paper projection of cargo, with goods and the complete tree retained in JSON."""
from copy import deepcopy
from decimal import Decimal

from app.core.messages import error
from app.schemas.cargo import CargoManifest
from app.services.cargo import assess


def project_lines(manifest, lines: list[dict], dangerous_goods=None, language="nl") -> list[dict]:
    """Show outer load packages, direct goods and each declaration exactly once.

    Transport-unit tare is not goods mass. Original dangerous-goods declarations
    are appended unchanged as separate descriptive rows, never proportionally
    divided or silently converted into the quantities of a new package tree.
    """
    cargo = manifest if isinstance(manifest, CargoManifest) else CargoManifest.model_validate(manifest)
    assessment = assess(cargo, lines)
    if not assessment["totals"]["complete"]:
        raise error(422, "cargo.documents_incomplete")
    if any(item["code"] in {"cargo.payload_exceeded", "cargo.gross_exceeded"} for item in assessment["issues"]):
        raise error(422, "cargo.payload_exceeded")
    units = {unit.id: unit for unit in cargo.units}
    computed = {unit["id"]: unit for unit in assessment["units"]}
    goods = {(line.get("cargo_goods_id") if type(line.get("cargo_goods_id")) is int else line.get("line_id")): line
             for line in lines if line.get("include", True)}
    children = {}
    allocations = {}
    for unit in cargo.units:
        children.setdefault(unit.parent_id, []).append(unit)
    for allocation in cargo.allocations:
        allocations.setdefault(allocation.unit_id, []).append(allocation)
    migrated = {unit.legacy_goods_id for unit in cargo.units if unit.legacy_goods_id is not None}

    def describe(identity):
        unit = units[identity]
        parts = [f"{item.quantity:g} {goods[item.goods_id].get('unit', '')} {goods[item.goods_id].get('description', '')}".strip()
                 for item in allocations.get(identity, [])]
        parts.extend(describe(child.id) for child in children.get(identity, []))
        return f"{unit.name} {unit.code}" + (f" ({'; '.join(parts)})" if parts else "")

    def destination(unit):
        result = []
        while unit.parent_id:
            unit = units[unit.parent_id]
            if unit.kind == "ctu":
                result.append(unit.external_reference or unit.code)
        return " / ".join(reversed(result))

    result = []
    for unit in cargo.units:
        if unit.kind != "package" or (unit.parent_id and units[unit.parent_id].kind == "package"):
            continue
        target = destination(unit)
        description = describe(unit.id) + (f" [{target}]" if target else "")
        result.append({"line_id": -len(result)-1, "include": True, "quantity": 1, "unit": "pcs",
                       "description": description, "output_description": description,
                       "weight_total_kg": computed[unit.id]["calculated_gross_kg"],
                       "transport_volume_m3": computed[unit.id]["occupied_volume_m3"]})

    direct = [(item["goods_id"], item["quantity"], None) for item in assessment["loose"]]
    direct += [(allocation.goods_id, allocation.quantity, units[allocation.unit_id])
               for allocation in cargo.allocations if units[allocation.unit_id].kind == "ctu"]
    for goods_id, quantity, carrier in direct:
        if goods_id in migrated:
            continue
        source = goods[goods_id]
        original = source.get("quantity")
        if quantity is None or not original:
            raise error(422, "cargo.documents_incomplete")
        ratio = Decimal(str(quantity)) / Decimal(str(original))
        line = deepcopy(source)
        line["line_id"] = -len(result)-1
        line["quantity"] = quantity
        line["weight_total_kg"] = float(Decimal(str(source["weight_total_kg"])) * ratio)
        original_volume = source.get("package_transport_volume_m3", source.get("transport_volume_m3"))
        line["transport_volume_m3"] = float(Decimal(str(original_volume)) * ratio) if original_volume is not None else None
        for key in ("container_line_id", "container_load", "container_base_status", "package_transport_volume_m3"):
            line.pop(key, None)
        line["equipment_role"] = "cargo"
        description = source.get("cargo_output_description") or source.get("output_description") or source.get("description", "")
        if carrier:
            description += f" [{carrier.external_reference or carrier.code}]"
        line["output_description"] = description
        result.append(line)
    if dangerous_goods:
        from app.services.dg.autofill import description_line
        for entry in dangerous_goods:
            for product in entry.get("products") or []:
                if str(product.get("un_number") or "").strip():
                    description = description_line(product, "ADR")
                    result.append({"line_id": -len(result)-1, "include": True, "quantity": None, "unit": "",
                                   "description": description, "output_description": description,
                                   "weight_total_kg": None, "transport_volume_m3": None})
    return result


def validate_for_document(manifest, lines: list[dict], key: str, values: dict) -> None:
    if manifest is None:
        return
    cargo = manifest if isinstance(manifest, CargoManifest) else CargoManifest.model_validate(manifest)
    result = assess(cargo, lines)
    if any(unit.kind == "package" for unit in cargo.units) and key in {"cim", "iata_dgd", "imo_dgd", "adn_transport_doc", "bl_si", "awb_si", "iftdgn", "vgm"}:
        raise error(422, "cargo.document_unsupported", document=key)
    if key in {"cmr", "avc_waybill", "packing_list", "delivery_note", "vgm", "imo_dgd", "bl_si", "iftdgn"}:
        if not result["totals"]["complete"]:
            raise error(422, "cargo.documents_incomplete")
        if any(item["code"] in {"cargo.payload_exceeded", "cargo.gross_exceeded"} for item in result["issues"]):
            raise error(422, "cargo.payload_exceeded")
    if key in {"vgm", "imo_dgd", "bl_si", "iftdgn"}:
        carriers = [unit for unit in cargo.units if unit.kind == "ctu"]
        if carriers:
            if len(carriers) != 1 or result["loose"]:
                raise error(422, "cargo.document_unsupported", document=key)
            carrier = carriers[0]
            if any(unit.parent_id is None and unit.id != carrier.id for unit in cargo.units):
                raise error(422, "cargo.document_unsupported", document=key)
            if carrier.external_reference and values.get("container_number") and carrier.external_reference.strip().upper() != str(values["container_number"]).strip().upper():
                raise error(422, "cargo.document_unsupported", document=key)
