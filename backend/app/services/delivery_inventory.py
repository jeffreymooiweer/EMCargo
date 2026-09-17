"""Operational quantities are distinct from office completion and DGSA history."""
from collections import defaultdict
from decimal import Decimal
from datetime import datetime

from app.models.delivery import Delivery
from app.services import deliveries as d


def balances(db, shipment_id, export, user):
    reserved = defaultdict(Decimal)
    received = defaultdict(Decimal)
    returned = defaultdict(Decimal)
    links = []
    for row in db.query(Delivery).all():
        value = d.data(row)
        allocations = [a for a in value["allocations"] if a["shipment_id"] == shipment_id]
        if not allocations:
            continue
        if d.internal(db, user, row):
            links.append({"id": row.id, "name": row.name, "status": d.aggregate(value)})
        active = {a["id"] for a in d.active_allocations(value)}
        for allocation in allocations:
            gid = allocation["goods_id"]
            if allocation["id"] in active:
                reserved[gid] += d.reserved_quantity(value, allocation)
            # A transfer across two modes is one delivery, not two deliveries.
            end = allocation["leg_ids"][-1]
            amount = d.receipt_totals(value, end)[allocation["id"]]["quantity"]
            target = returned if value.get("followup", {}).get("kind") == "return" else received
            target[gid] += amount
    return {"goods": [{"id": gid, "description": goods.get("description", ""), "unit": goods.get("unit", ""),
                        "quantity": str(d.decimal(goods["quantity"])), "reserved": str(reserved[gid]),
                        "available": str(max(Decimal(0), d.decimal(goods["quantity"]) - reserved[gid])),
                        "received": str(received[gid]), "returned": str(returned[gid])}
                       for gid, goods in d.source_goods(export).items()], "deliveries": links}


def operations(db, user, start=None, end=None):
    """Count final receipts only; use their actual dates, never planning dates."""
    states = defaultdict(int)
    rows = []
    for record in db.query(Delivery).order_by(Delivery.updated_at.desc()).all():
        if not d.internal(db, user, record):
            continue
        value = d.data(record)
        states[d.aggregate(value)] += 1
        by_id = {a["id"]: a for a in value["allocations"]}
        totals = defaultdict(lambda: defaultdict(Decimal))
        for part in value["legs"]:
            for event in d.effective_events(value, part["id"]):
                if event.get("corrected_kind", event["kind"]) != "receipt":
                    continue
                occurred = datetime.fromisoformat(event["occurred_at"]).date()
                if (start and occurred < start) or (end and occurred > end):
                    continue
                for line in event["lines"]:
                    allocation = by_id[line["allocation_id"]]
                    if allocation["leg_ids"][-1] != part["id"]:
                        continue
                    for key in ("quantity", "damaged", "refused"):
                        totals[allocation["id"]][key] += d.decimal(line[key])
        for aid, counts in totals.items():
            allocation = by_id[aid]
            source = value["sources"][str(allocation["shipment_id"])]
            goods = d.source_goods(source["export"])[allocation["goods_id"]]
            rows.append({"delivery_id": record.id, "delivery": record.name, "shipment": source["reference"],
                         "goods": goods.get("description", ""), "unit": goods.get("unit", ""),
                         "movement": value.get("followup", {}).get("kind", "delivery"),
                         **{k: str(v) for k, v in counts.items()}})
    return {"states": dict(states), "rows": rows}


def physical_unit_completed(db, shipment_id, unit_id):
    from app.services.delivery_unloading import released
    relevant = []
    for record in db.query(Delivery).all():
        value = d.data(record)
        for part in value["legs"]:
            if part["status"] not in d.RESERVED:
                continue
            if any(a["shipment_id"] == shipment_id for a in d.selected(value, part["id"])) and unit_id in d.occupied_units(value, part):
                relevant.append(released(value, part, unit_id))
    return bool(relevant) and all(relevant)
