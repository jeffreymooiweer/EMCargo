"""Select complete physical units without proportioning their packing manifests."""
import copy
from collections import defaultdict
from decimal import Decimal

from app.core.messages import error


def roots(export):
    from app.services import deliveries as d
    manifest = export.get("cargo") or {}
    units = {u["id"]: u for u in manifest.get("units", [])}
    groups = {}
    parents = {}
    for uid in units:
        root, seen = uid, set()
        while units[root].get("parent_id"):
            if root in seen or units[root]["parent_id"] not in units:
                raise error(422, "delivery.unpack")
            seen.add(root)
            root = units[root]["parent_id"]
        parents[uid] = root
        group = groups.setdefault(root, {"id": root, "code": units[root]["code"], "name": units[root]["name"], "unit_ids": [], "goods": defaultdict(Decimal)})
        group["unit_ids"].append(uid)
    for item in manifest.get("allocations", []):
        if item["unit_id"] not in parents:
            raise error(422, "delivery.unpack")
        groups[parents[item["unit_id"]]]["goods"][str(item["goods_id"])] += d.decimal(item["quantity"])
    goods = d.source_goods(export)
    for uid, unit in units.items():
        gid = unit.get("legacy_goods_id")
        if gid is not None and str(gid) in goods:
            groups[parents[uid]]["goods"][str(gid)] += d.decimal(goods[str(gid)]["quantity"])
    return groups


def chosen(allocation, groups):
    ids = allocation.get("unit_ids")
    if ids is None:
        return {uid for uid, group in groups.items() if allocation["goods_id"] in group["goods"]}
    if len(ids) != len(set(ids)) or any(uid not in groups or allocation["goods_id"] not in groups[uid]["goods"] for uid in ids):
        raise error(422, "delivery.unpack")
    return set(ids)


def validate(value):
    from app.services import deliveries as d
    if value.get("followup") and value.get("unpacked"):
        return
    for sid, source in value["sources"].items():
        groups = roots(source["export"])
        goods = d.source_goods(source["export"])
        allocations = [a for a in value["allocations"] if str(a["shipment_id"]) == sid]
        used, loose = set(), defaultdict(Decimal)
        for allocation in allocations:
            gid = allocation["goods_id"]
            ids = chosen(allocation, groups)
            packed = sum((groups[uid]["goods"][gid] for uid in ids), Decimal(0))
            remainder = d.decimal(allocation["quantity"]) - packed
            if remainder < 0 or any((gid, uid) in used for uid in ids):
                raise error(422, "delivery.unpack")
            used.update((gid, uid) for uid in ids)
            loose[gid] += remainder
            source_loose = d.decimal(goods[gid]["quantity"]) - sum((g["goods"].get(gid, Decimal(0)) for g in groups.values()), Decimal(0))
            if loose[gid] > source_loose:
                raise error(422, "delivery.unpack")
        for part in value["legs"]:
            selected = [a for a in d.selected(value, part["id"]) if str(a["shipment_id"]) == sid]
            if any(d.decimal(a["quantity"]) < sum((groups[uid]["goods"][a["goods_id"]] for uid in chosen(a, groups)), Decimal(0)) for a in selected):
                raise error(422, "delivery.unpack")
            for uid, group in groups.items():
                members = {a["goods_id"] for a in selected if uid in chosen(a, groups)}
                if members and members != set(group["goods"]):
                    raise error(422, "delivery.unpack")


def project(value, part, shipment_id):
    from app.services import deliveries as d
    export = value["sources"][str(shipment_id)]["export"]
    manifest = copy.deepcopy(export.get("cargo"))
    if value.get("followup") and value.get("unpacked"):
        manifest = None
    if not manifest:
        from app.services.delivery_load_units import project as load_project
        return load_project(None, value, part, shipment_id)
    groups = roots(export)
    allocations = [a for a in d.selected(value, part["id"]) if a["shipment_id"] == shipment_id]
    selected = {uid for a in allocations for uid in chosen(a, groups)}
    included = {uid for root in selected for uid in groups[root]["unit_ids"]}
    manifest["units"] = [u for u in manifest["units"] if u["id"] in included]
    manifest["allocations"] = [a for a in manifest["allocations"] if a["unit_id"] in included]
    from app.services.delivery_load_units import project as load_project
    return load_project(manifest, value, part, shipment_id)


def occupied(value, part):
    from app.services import deliveries as d
    return {u["id"] for sid in {a["shipment_id"] for a in d.selected(value, part["id"])}
            for u in (project(value, part, sid) or {}).get("units", [])}


def reserve_units(values):
    """A completed box consumes source inventory even when its reusable shell is free."""
    from app.services import deliveries as d
    seen = set()
    loose = defaultdict(Decimal)
    for value in values:
        if value.get("followup"):
            continue
        current = set()
        for allocation in d.active_allocations(value):
            sid, gid = allocation["shipment_id"], allocation["goods_id"]
            export = value["sources"][str(sid)]["export"]
            groups = roots(export)
            ids = chosen(allocation, groups)
            current.update((sid, uid) for uid in ids)
            loose[(sid, gid)] += d.decimal(allocation["quantity"]) - sum((groups[uid]["goods"][gid] for uid in ids), Decimal(0))
            source_loose = d.decimal(d.source_goods(export)[gid]["quantity"]) - sum((g["goods"].get(gid, Decimal(0)) for g in groups.values()), Decimal(0))
            if loose[(sid, gid)] > source_loose:
                raise error(409, "delivery.overallocated")
        if current & seen:
            raise error(409, "cargo.unit_in_use")
        seen.update(current)
