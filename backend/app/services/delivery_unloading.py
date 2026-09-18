"""Physical availability requires receipt evidence or an explicit empty-unit record."""
from datetime import timedelta

from app.core.messages import error
from app.services import deliveries as d
from app.services.delivery_cargo import roots, chosen


def contents(value, part, unit_id):
    if part.get("load_unit_id") == unit_id:
        return d.selected(value, part["id"])
    if value.get("unpacked"):
        return []
    allocations = []
    for allocation in d.selected(value, part["id"]):
        groups = roots(value["sources"][str(allocation["shipment_id"])]["export"])
        if any(unit_id in groups[uid]["unit_ids"] for uid in chosen(allocation, groups)):
            allocations.append(allocation)
    return allocations


def released(value, part, unit_id):
    if part["status"] not in {"completed", "closed"}:
        return False
    if any(e["kind"] == "unload" and e["leg_id"] == part["id"] and unit_id in e["unit_ids"] for e in value["events"]):
        return True
    allocations = contents(value, part, unit_id)
    totals = d.receipt_totals(value, part["id"])
    return bool(allocations) and all(totals[a["id"]]["quantity"] == d.decimal(a["quantity"]) for a in allocations)


def register(db, user, record, leg_id, payload):
    value = d.data(record)
    part = d.leg(value, leg_id)
    allowed = d.allowed_allocations(db, user, record, value, leg_id, "operator")
    selected = {}
    for uid in payload.unit_ids:
        allocations = contents(value, part, uid)
        if not allocations or not {a["id"] for a in allocations} <= allowed:
            raise error(403, "delivery.permission")
        selected.update({a["id"]: a for a in allocations})
    body = payload.model_dump(mode="json", exclude={"version"})
    previous = next((e for e in value["events"] if e["request_id"] == payload.request_id), None)
    if previous:
        if previous.get("request_hash") != d.digest(body) or previous["actor"] != user.id:
            raise error(409, "delivery.conflict")
        return d.view(db, user, record)
    d.check_version(record, payload.version)
    if part["status"] not in {"in_progress", "completed", "closed"}:
        raise error(409, "delivery.state")
    if payload.occurred_at > d.now() + timedelta(minutes=5):
        raise error(422, "delivery.time")
    body.update(kind="unload", leg_id=leg_id, actor=user.id, recorded_at=d.stamp(), request_hash=d.digest(body),
                lines=[{"allocation_id": aid, "quantity": "0", "damaged": "0", "refused": "0"} for aid in selected])
    value["events"].append(body)
    return d.save(db, record, value, user, "unload")
