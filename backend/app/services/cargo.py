"""Cargo invariants and accounting, independent of persistence and placement.

Goods quantities remain on shipment lines. Allocations only refer to a share of
that quantity; packages add their tare once. A carrier is never added to cargo
mass, and measured gross never conceals unknown component weights.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from math import isfinite
from typing import Any

from app.core.config import get_settings
from app.core.messages import error
from app.schemas.cargo import CargoManifest, Dimensions

D = Decimal
ZERO = D(0)
EPSILON = D("0.000000001")
DISCRETE = {"pcs", "pc", "piece", "pieces", "st", "stuk", "stuks", "ea", "each", "unit", "units"}


def number(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    if not isfinite(value) or value < 0 or value > 1e12:
        return None
    return D(str(value))


def rounded(value: Decimal | None) -> float | None:
    return round(float(value), 6) if value is not None else None


def volume(dimensions: Dimensions | None) -> Decimal | None:
    if dimensions is None or any(getattr(dimensions, key) is None for key in ("length", "width", "height")):
        return None
    return D(str(dimensions.length)) * D(str(dimensions.width)) * D(str(dimensions.height)) / D(10**9)


def assess(manifest: CargoManifest | dict, lines: list[dict]) -> dict:
    cargo = manifest if isinstance(manifest, CargoManifest) else CargoManifest.model_validate(manifest)
    settings = get_settings()
    if len(cargo.units) > settings.cargo_max_units or len(cargo.allocations) > settings.cargo_max_allocations:
        raise error(422, "cargo.limit")
    units = {unit.id: unit for unit in cargo.units}
    children: dict[str | None, list[str]] = defaultdict(list)
    depth: dict[str, int] = {}
    equipment: set[int] = set()
    for unit in cargo.units:
        if unit.parent_id is not None and unit.parent_id not in units:
            raise error(422, "cargo.parent_missing")
        if unit.equipment_id is not None:
            if unit.equipment_id in equipment:
                raise error(422, "cargo.identity_duplicate")
            equipment.add(unit.equipment_id)
        children[unit.parent_id].append(unit.id)
        path: list[str] = []
        current = unit.id
        seen: set[str] = set()
        while current is not None and current not in depth:
            if current in seen:
                raise error(422, "cargo.cycle")
            seen.add(current)
            path.append(current)
            if len(path) > settings.cargo_max_depth:
                raise error(422, "cargo.limit")
            current = units[current].parent_id
            if current is not None and current not in units:
                raise error(422, "cargo.parent_missing")
        level = depth[current] if current else 0
        for identity in reversed(path):
            level += 1
            depth[identity] = level
            if level > settings.cargo_max_depth:
                raise error(422, "cargo.limit")
        if unit.kind == "ctu" and unit.parent_id is not None and units[unit.parent_id].kind == "package":
            raise error(422, "cargo.parent_invalid")

    goods: dict[int, dict] = {}
    for line in lines:
        if not line.get("include", True):
            continue
        identity = line.get("cargo_goods_id")
        if type(identity) is not int:
            identity = line.get("line_id")
        if type(identity) is not int:
            raise error(422, "cargo.goods_missing")
        if type(identity) is int:
            if identity in goods:
                raise error(422, "cargo.goods_duplicate")
            goods[identity] = line
    migrated = {unit.legacy_goods_id for unit in cargo.units if unit.legacy_goods_id is not None}
    if len(migrated) != sum(unit.legacy_goods_id is not None for unit in cargo.units):
        raise error(422, "cargo.identity_duplicate")
    for unit in cargo.units:
        if unit.legacy_goods_id is not None:
            line = goods.get(unit.legacy_goods_id)
            if (not line or line.get("equipment_role") != "container" or unit.kind != "ctu"
                    or unit.tare_kg != line.get("weight_total_kg")):
                raise error(422, "cargo.legacy_invalid")

    assigned: dict[int, Decimal] = defaultdict(Decimal)
    contents: dict[str, list] = defaultdict(list)
    for allocation in cargo.allocations:
        line = goods.get(allocation.goods_id)
        if line is None or allocation.goods_id in migrated:
            raise error(422, "cargo.goods_missing")
        if allocation.unit_id not in units:
            raise error(422, "cargo.parent_missing")
        quantity = D(str(allocation.quantity))
        available = number(line.get("quantity"))
        if available is None:
            raise error(422, "cargo.quantity_missing")
        if str(line.get("unit", "pcs")).strip().lower() in DISCRETE and quantity != quantity.to_integral_value():
            raise error(422, "cargo.whole_items")
        assigned[allocation.goods_id] += quantity
        if assigned[allocation.goods_id] - available > EPSILON:
            raise error(422, "cargo.overallocated")
        contents[allocation.unit_id].append(allocation)

    def mass(line: dict, quantity: Decimal) -> Decimal | None:
        available, total = number(line.get("quantity")), number(line.get("weight_total_kg"))
        # Zero is the legacy pipeline's unknown weight, never an established
        # mass for a positive physical quantity.
        return total * quantity / available if total is not None and total > 0 and available else None

    issues: list[dict] = []
    computed: dict[str, dict] = {}
    for identity in sorted(units, key=lambda key: depth[key], reverse=True):
        unit = units[identity]
        masses = [mass(goods[item.goods_id], D(str(item.quantity))) for item in contents[identity]]
        masses.extend(computed[child]["_gross"] for child in children[identity])
        known = sum((value for value in masses[:len(contents[identity])] if value is not None), ZERO)
        known += sum((computed[child]["_known_gross"] for child in children[identity]), ZERO)
        content_mass = sum(masses, ZERO) if all(value is not None for value in masses) else None
        tare = number(unit.tare_kg)
        gross = content_mass + tare if content_mass is not None and tare is not None else None
        measured = number(unit.measured_gross_kg)
        load_volume = volume(unit.loaded_dimensions_mm)
        # Rigid enclosed packs occupy their known outer dimensions. A pallet,
        # open crate or vehicle needs explicit loaded dimensions for its load.
        if load_volume is None and unit.kind == "package" and unit.category in {"box", "case", "drum", "jerrycan", "ibc"}:
            load_volume = volume(unit.dimensions_mm)
        if gross is None:
            issues.append({"code": "cargo.weight_unknown", "unit_id": identity})
        if content_mass is not None and unit.max_payload_kg is not None and content_mass > D(str(unit.max_payload_kg)):
            issues.append({"code": "cargo.payload_exceeded", "unit_id": identity})
        effective_gross = measured if measured is not None else gross
        if effective_gross is not None and unit.max_gross_kg is not None and effective_gross > D(str(unit.max_gross_kg)):
            issues.append({"code": "cargo.gross_exceeded", "unit_id": identity})
        if measured is not None and gross is not None and abs(measured - gross) > D("0.01"):
            issues.append({"code": "cargo.weight_difference", "unit_id": identity})
        computed[identity] = {"id": identity, "content_kg": rounded(content_mass), "known_content_kg": rounded(known),
                              "calculated_gross_kg": rounded(gross), "measured_gross_kg": unit.measured_gross_kg,
                              "occupied_volume_m3": rounded(load_volume), "complete": gross is not None,
                              "_gross": gross, "_known_gross": known + (tare if tare is not None else ZERO), "_volume": load_volume}

    goods_masses: list[Decimal | None] = []
    loose: list[dict] = []
    volumes: list[Decimal | None] = []
    for identity, line in goods.items():
        if identity in migrated:
            continue
        quantity = number(line.get("quantity"))
        total = number(line.get("weight_total_kg"))
        goods_masses.append(total if total and total > 0 else None)
        remainder = quantity - assigned[identity] if quantity is not None else None
        if remainder is None or remainder > EPSILON:
            loose_mass = mass(line, remainder) if remainder is not None else None
            loose.append({"goods_id": identity, "quantity": rounded(remainder), "weight_kg": rounded(loose_mass)})
            original_volume = number(line.get("package_transport_volume_m3", line.get("transport_volume_m3")))
            volumes.append(original_volume * remainder / quantity if original_volume is not None and remainder is not None and quantity else None)
    # Unpacked goods assigned directly to a carrier still occupy load space.
    for allocation in cargo.allocations:
        if units[allocation.unit_id].kind != "ctu" or units[allocation.unit_id].parent_id is not None:
            continue
        line = goods[allocation.goods_id]
        original_volume = number(line.get("package_transport_volume_m3", line.get("transport_volume_m3")))
        quantity = number(line.get("quantity"))
        volumes.append(original_volume * D(str(allocation.quantity)) / quantity if original_volume is not None and quantity else None)
    # A carrier's tare belongs in transport gross, not shipment cargo gross.
    package_tares = [number(unit.tare_kg) for unit in cargo.units if unit.kind == "package"]
    carrier_tares = [number(unit.tare_kg) for unit in cargo.units if unit.kind == "ctu"]
    def complete_sum(values):
        return sum(values, ZERO) if all(value is not None for value in values) else None
    goods_mass, package_mass, carrier_mass = map(complete_sum, (goods_masses, package_tares, carrier_tares))
    cargo_mass = goods_mass + package_mass if goods_mass is not None and package_mass is not None else None
    transport_mass = cargo_mass + carrier_mass if cargo_mass is not None and carrier_mass is not None else None
    for unit in cargo.units:
        # Only the outer load packages count, including packages inside a CTU.
        if unit.kind == "package" and (unit.parent_id is None or (units[unit.parent_id].kind == "ctu" and units[unit.parent_id].parent_id is None)):
            volumes.append(computed[unit.id]["_volume"])
    for unit in cargo.units:
        if unit.kind == "ctu" and unit.parent_id is not None and units[unit.parent_id].parent_id is None:
            volumes.append(volume(unit.loaded_dimensions_mm or unit.dimensions_mm))
    total_volume = complete_sum(volumes)
    if goods_mass is None:
        issues.append({"code": "cargo.weight_unknown"})
    return {"cargo": cargo.model_dump(mode="json"),
            "units": [{key: value for key, value in computed[unit.id].items() if not key.startswith("_")} for unit in cargo.units],
            "loose": loose, "issues": issues,
            "totals": {"goods_kg": rounded(goods_mass), "packaging_kg": rounded(package_mass),
                       "cargo_gross_kg": rounded(cargo_mass), "transport_tare_kg": rounded(carrier_mass),
                       "transport_gross_kg": rounded(transport_mass), "occupied_volume_m3": rounded(total_volume),
                       "complete": cargo_mass is not None}}
