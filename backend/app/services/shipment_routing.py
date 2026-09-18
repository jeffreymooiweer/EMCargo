"""Validate preparation facts without making a transport or document decision."""
from collections import defaultdict
import copy
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from app.core.messages import error
from app.schemas.routing import ShipmentRouting


def legacy(export):
    """Adapt known addresses only; never invent a location for old shipments."""
    if export.get("routing") is not None:
        return ShipmentRouting.model_validate(export["routing"])
    values = export.get("consignment") or {}
    locations = []
    for kind, prefix, physical in (("pickup", "consignor", "loading_point"), ("delivery", "consignee", "delivery_point")):
        party = {key: str(values.get(f"{prefix}_{key}") or "") for key in ("name", "address", "country", "contact")}
        address = str(values.get(physical) or party["address"])
        if party["name"] or address:
            locations.append({**party, "id": f"legacy-{kind}", "kind": kind, "address": address, "party": party})
    from app.services.deliveries import source_goods
    distributions = []
    from app.services.delivery_cargo import roots
    groups = roots(export)
    if len(locations) == 2:
        for gid, line in source_goods(export).items():
            if Decimal(str(line.get("quantity") or 0)) > 0:
                distributions.append({"id": str(uuid5(NAMESPACE_URL, f"emcargo-legacy:{gid}")), "goods_id": gid,
                                      "quantity": str(line["quantity"]), "pickup_id": "legacy-pickup", "delivery_id": "legacy-delivery", "unit_ids": [uid for uid, group in groups.items() if gid in group["goods"]]})
    return ShipmentRouting(locations=locations, distributions=distributions)


def entries_for(payload, gid):
    from app.services.deliveries import source_goods
    goods = source_goods({"goods": payload.lines})
    line = goods.get(gid, {})
    return [entry for entry in payload.dangerous_goods or [] if str(entry.get("line_id")) == str(line.get("line_id"))]


def confirmation(payload, distribution):
    from app.services.deliveries import source_goods
    return copy.deepcopy({"goods": source_goods({"goods": payload.lines}).get(distribution.goods_id),
            "entries": entries_for(payload, distribution.goods_id), "quantity": str(distribution.quantity),
            "pickup_id": distribution.pickup_id, "delivery_id": distribution.delivery_id,
            "locations": [p.model_dump(mode="json") for p in payload.routing.locations if p.id in {distribution.pickup_id, distribution.delivery_id}],
            "unit_ids": distribution.unit_ids, "declarations": distribution.dangerous_goods})


def dg_complete(entries):
    return bool(entries) and all(isinstance(entry, dict) and isinstance(entry.get("products"), list) and entry["products"] and all(
        isinstance(product, dict) and all(str(product.get(key) or "").strip() for key in ("un_number", "proper_shipping_name", "class"))
        for product in entry["products"]) for entry in entries)


def issues(payload):
    from app.services.deliveries import source_goods, canonical
    from app.services.cargo import DISCRETE
    from app.services.delivery_cargo import roots
    routing = payload.routing
    if routing is None:
        return ["routing.addresses"]
    goods = source_goods({"goods": payload.lines})
    locations = {p.id: p for p in routing.locations}
    distributions = routing.distributions
    problems = set()
    if not goods or any(line.get("status") == "error" or line.get("quantity_unconfirmed") or line.get("unconfirmed_weight_kg") is not None for line in goods.values()):
        problems.add("routing.goods")
    if len(locations) != len(routing.locations) or len({a.id for a in distributions}) != len(distributions):
        problems.add("routing.references")
    totals = defaultdict(Decimal)
    assigned_units = {}
    groups = roots({"goods": payload.lines, "cargo": payload.cargo.model_dump(mode="json") if payload.cargo else None})
    for a in distributions:
        line = goods.get(a.goods_id)
        if line is None:
            problems.add("routing.references")
            continue
        totals[a.goods_id] += a.quantity
        if a.quantity <= 0:
            problems.add("routing.quantities")
        if str(line.get("unit", "")).lower() in DISCRETE and a.quantity != a.quantity.to_integral_value():
            problems.add("routing.quantities")
        for pid, kind in ((a.pickup_id, "pickup"), (a.delivery_id, "delivery")):
            point = locations.get(pid)
            if not point or point.kind != kind or not point.name or not point.address or not point.country or not point.party.name or not point.party.address:
                problems.add("routing.addresses")
        packed = Decimal(0)
        for uid in a.unit_ids:
            if uid not in groups or a.goods_id not in groups[uid]["goods"]:
                problems.add("routing.packing")
                continue
            pair = (a.pickup_id, a.delivery_id)
            if uid in assigned_units and assigned_units[uid] != pair:
                problems.add("routing.packing")
            assigned_units[uid] = pair
            packed += groups[uid]["goods"][a.goods_id]
        if packed > a.quantity:
            problems.add("routing.packing")
        entries = entries_for(payload, a.goods_id)
        flagged = any(line.get(key) for key in ("dangerous_goods", "un_number", "is_dangerous", "detected_un_numbers"))
        if (flagged or entries) and not dg_complete(entries):
            problems.add("routing.dg")
        if entries and sum(1 for item in distributions if item.goods_id == a.goods_id) > 1:
            if not dg_complete(entries) or not dg_complete(a.dangerous_goods) or canonical(a.dg_confirmation) != canonical(confirmation(payload, a)):
                problems.add("routing.dg_split")
            else:
                # Quantity-dependent fields must be explicitly provided for each
                # linked product; classification and verified source stay intact.
                original = [p for e in entries for p in e["products"]]
                split = [p for e in a.dangerous_goods for p in e["products"]]
                mutable = {"quantity_packages", "type_of_package", "quantity_items_per_package", "net_mass_liters_per_package", "gross_mass_per_package", "adr_total_quantity", "net_explosive_mass", "q_net_quantity"}
                if len(original) != len(split) or any(
                    {k: v for k, v in p.items() if k not in mutable} != {k: v for k, v in q.items() if k not in mutable}
                    or not q.get("quantity_packages") or not q.get("type_of_package") or not q.get("net_mass_liters_per_package")
                    for p, q in zip(original, split)):
                    problems.add("routing.dg_split")
    if set(totals) != set(goods) or any(totals[gid] != Decimal(str(line.get("quantity") or 0)) for gid, line in goods.items()):
        problems.add("routing.quantities")
    for uid, group in groups.items():
        for gid in group["goods"]:
            if sum(uid in a.unit_ids and a.goods_id == gid for a in distributions) != 1:
                problems.add("routing.packing")
    # Unattached declarations must not disappear from operational selection.
    mapped = [e for gid in goods for e in entries_for(payload, gid)]
    if len(mapped) != len(payload.dangerous_goods or []):
        problems.add("routing.dg")
    return sorted(problems)


def validate(payload):
    problems = issues(payload)
    if problems:
        raise error(422, problems[0])
