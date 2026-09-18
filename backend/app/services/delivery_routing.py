"""Delivery stops retain original shipment locations and explicit deviations."""
from collections import defaultdict
from decimal import Decimal

from app.core.messages import error
from app.services.shipment_routing import legacy

FIELDS = ("name", "address", "country", "contact")


def label(point):
    return ", ".join(str(point.get(k) or "") for k in ("name", "address", "country") if point.get(k))


def distributions(export):
    return {a.id: a.model_dump(mode="json") for a in legacy(export).distributions}


def hydrate(value, previous, actor):
    from app.services import deliveries as d
    for a in value["allocations"]:
        if a.get("source_distribution_id") is None: a.pop("source_distribution_id", None)
    for part in value["legs"]:
        for key in ("origin_stop_id", "destination_stop_id"):
            if part.get(key) is None: part.pop(key, None)
    old = {s["id"]: s for s in (previous or {}).get("stops", [])}
    for stop in value.get("stops", []):
        if stop["kind"] == "transfer":
            if stop.get("shipment_id") or stop.get("location_id"):
                raise error(422, "routing.references")
            continue
        source = value["sources"].get(str(stop.get("shipment_id")))
        original = next((p.model_dump(mode="json") for p in legacy(source["export"]).locations if p.id == stop.get("location_id")), None) if source else None
        if not original or original["kind"] != stop["kind"]:
            raise error(422, "routing.references")
        stop["original"] = original
        before = old.get(stop["id"], {})
        changed = any(stop.get(k, "") != original.get(k, "") for k in FIELDS)
        if changed and not stop.get("override_reason", "").strip():
            raise error(422, "routing.override")
        stop["changes"] = list(before.get("changes", []))
        if any(stop.get(k, "") != before.get(k, original.get(k, "")) for k in (*FIELDS, "override_reason")):
            stop["changes"].append({"actor": actor.id, "at": d.stamp(), "reason": stop["override_reason"],
                                    "before": {k: before.get(k, original.get(k, "")) for k in FIELDS},
                                    "after": {k: stop.get(k, "") for k in FIELDS}})
    stops = {s["id"]: s for s in value.get("stops", [])}
    for leg in value["legs"]:
        if leg.get("origin_stop_id") in stops and leg.get("destination_stop_id") in stops:
            leg["origin"] = label(stops[leg["origin_stop_id"]])
            leg["destination"] = label(stops[leg["destination_stop_id"]])


def validate(value):
    from app.services import deliveries as d
    stops = value.get("stops", [])
    routed = any(s["export"].get("routing") is not None for s in value["sources"].values())
    if not stops and not routed:
        return  # Frozen legacy records retain their original interpretation.
    if not value["allocations"]:
        return
    if any(not s.get("name") or not s.get("address") or not s.get("country") for s in stops):
        raise error(422, "routing.addresses")
    positions = {s["id"]: i for i, s in enumerate(stops)}
    if len(positions) != len(stops) or len(value["legs"]) != len(stops) - 1:
        raise error(422, "delivery.itinerary")
    for i, part in enumerate(value["legs"]):
        if part.get("origin_stop_id") != stops[i]["id"] or part.get("destination_stop_id") != stops[i + 1]["id"]:
            raise error(422, "delivery.itinerary")
    totals = defaultdict(Decimal)
    for a in value["allocations"]:
        source = value["sources"][str(a["shipment_id"])]["export"]
        distribution = distributions(source).get(a.get("source_distribution_id"))
        if not distribution or distribution["goods_id"] != a["goods_id"]:
            raise error(422, "routing.references")
        totals[(a["shipment_id"], distribution["id"])] += d.decimal(a["quantity"])
        if totals[(a["shipment_id"], distribution["id"])] > d.decimal(distribution["quantity"]):
            raise error(409, "delivery.overallocated")
        if value.get("followup"):
            continue
        ends = []
        for field in ("pickup_id", "delivery_id"):
            found = [i for i, stop in enumerate(stops) if stop.get("shipment_id") == a["shipment_id"] and stop.get("location_id") == distribution[field]]
            if len(found) != 1:
                raise error(422, "delivery.itinerary")
            ends.append(found[0])
        start, end = ends
        if start >= end or a["leg_ids"] != [p["id"] for p in value["legs"][start:end]]:
            raise error(422, "delivery.itinerary")
        from app.services.delivery_cargo import roots
        groups = roots(source)
        assigned = set(distribution["unit_ids"])
        chosen = set(a.get("unit_ids") or [])
        source_packed = sum((groups[uid]["goods"].get(a["goods_id"], Decimal(0)) for uid in assigned), Decimal(0))
        selected_packed = sum((groups[uid]["goods"].get(a["goods_id"], Decimal(0)) for uid in chosen if uid in groups), Decimal(0))
        if d.decimal(a["quantity"]) - selected_packed > d.decimal(distribution["quantity"]) - source_packed:
            raise error(422, "routing.packing")
        if not chosen <= assigned:
            raise error(422, "routing.packing")


def reserve(values, current):
    from app.services import deliveries as d
    totals = defaultdict(Decimal)
    for value in values:
        for a in d.active_allocations(value):
            if a.get("source_distribution_id"):
                totals[(a["shipment_id"], a["source_distribution_id"])] += d.reserved_quantity(value, a)
    for a in d.active_allocations(current):
        if a.get("source_distribution_id"):
            source = distributions(current["sources"][str(a["shipment_id"])]["export"])[a["source_distribution_id"]]
            if totals[(a["shipment_id"], a["source_distribution_id"])] > d.decimal(source["quantity"]):
                raise error(409, "delivery.overallocated")


def balances(db, shipment_id, export):
    from app.models.delivery import Delivery
    from app.services import deliveries as d
    used = defaultdict(Decimal)
    for record in db.query(Delivery).all():
        value = d.data(record)
        for a in d.active_allocations(value):
            if a["shipment_id"] == shipment_id:
                source_id = a.get("source_distribution_id")
                if not source_id:
                    candidates = [aid for aid, entry in distributions(export).items() if entry["goods_id"] == a["goods_id"]]
                    if len(candidates) == 1: source_id = candidates[0]
                if source_id: used[source_id] += d.reserved_quantity(value, a)
    return [{**a, "available": str(max(Decimal(0), d.decimal(a["quantity"]) - used[aid])), "reserved": str(used[aid])}
            for aid, a in distributions(export).items()]


def grant_ids(grant, value):
    """Old shipment grants are valid only for unsplit legacy records."""
    import json
    from app.services import deliveries as d
    explicit = json.loads(grant.allocation_ids_json or "[]")
    if explicit:
        return set(explicit)
    shipments = json.loads(grant.shipment_ids_json)
    return {a["id"] for a in d.selected(value, grant.leg_id) if a["shipment_id"] in shipments
            and not value["sources"][str(a["shipment_id"])]["export"].get("routing")}
