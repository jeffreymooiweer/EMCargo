"""Link physical return/redelivery attempts without creating extra source stock."""
import copy
from uuid import uuid4

from app.core.messages import error
from app.models.delivery import Delivery
from app.services import deliveries as d


def create(db, user, parent, value, part, event):
    """Create an unplanned attempt; no loading or receipt is inferred."""
    kind = event["resolution"]
    next_part = {k: copy.deepcopy(v) for k, v in part.items()
                 if k not in {"review", "assessment", "completed_at"}}
    next_part.update(id=str(uuid4()), status="draft", planned_start=None,
                     planned_end=None, vehicle="", equipment_ids=[], document_values={}, load_unit_id=None)
    next_part.pop("load_unit", None)
    if kind == "return":
        next_part["origin"], next_part["destination"] = part["destination"], part["origin"]
    allocations, mapping = [], {}
    for line in event["lines"]:
        original = next(a for a in value["allocations"] if a["id"] == line["allocation_id"])
        allocation = {**original, "id": str(uuid4()), "quantity": line["quantity"], "leg_ids": [next_part["id"]], "leg_quantities": {}}
        mapping[allocation["id"]] = original["id"]
        allocations.append(allocation)
    source_ids = {str(a["shipment_id"]) for a in allocations}
    body = {"legs": [next_part], "allocations": allocations, "events": [],
            "history": [{"at": d.stamp(), "actor": user.id, "action": "created"}],
            "sources": {sid: copy.deepcopy(value["sources"][sid]) for sid in source_ids},
            "followup": {"parent_id": parent.id, "leg_id": part["id"], "event_id": event["request_id"],
                         "kind": kind, "allocation_map": mapping}}
    if value.get("unpacked"):
        body["unpacked"] = True
    child = Delivery(id=str(uuid4()), name=parent.name[:110] + (" ↩" if kind == "return" else " ↻"),
                     department_id=parent.department_id, created_by_id=user.id, version=1,
                     data_json=d.canonical(body))
    db.add(child)
    event["followup_id"] = child.id
    event["followup_complete"] = False
    db.flush()


def preserve(previous, value):
    """The server owns provenance and quantities; planning cannot forge stock."""
    if "followup" not in previous:
        return
    if (len(value["legs"]) != 1 or value["legs"][0]["id"] != previous["legs"][0]["id"]
            or value["allocations"] != previous["allocations"] or value["sources"] != previous["sources"]):
        raise error(409, "delivery.frozen")
    value["followup"] = previous["followup"]
    if previous.get("unpacked"):
        value["unpacked"] = previous["unpacked"]


def ancestors(db, value):
    """An attempt continues an ancestor's physical load, never a sibling's load."""
    result = set()
    while value.get("followup"):
        identity = value["followup"]["parent_id"]
        if identity in result:
            raise error(409, "delivery.conflict")
        result.add(identity)
        parent = db.get(Delivery, identity)
        if parent is None:
            raise error(409, "delivery.source_changed")
        value = d.data(parent)
    return result


def sync_parent(db, record, value, actor):
    """Update every ancestor within the child's transaction, including corrections."""
    link = value.get("followup")
    if not link:
        return
    parent = db.get(Delivery, link["parent_id"], populate_existing=True)
    if parent is None:
        raise error(409, "delivery.source_changed")
    original = d.data(parent)
    event = next((e for e in original["events"] if e["request_id"] == link["event_id"]), None)
    if not event or event.get("followup_id") != record.id:
        raise error(409, "delivery.conflict")
    complete = d.aggregate(value) in {"completed", "closed"}
    if event.get("followup_complete", False) == complete:
        return
    part = d.leg(original, link["leg_id"])
    if part["status"] == "closed" and not complete:
        raise error(409, "delivery.frozen")
    event["followup_complete"] = complete
    original.setdefault("history", []).append({"at": d.stamp(), "actor": actor.id, "action": "followup_updated"})
    if not d.unresolved(original, part["id"]):
        part.update(status="completed", completed_at=d.stamp())
        d.shorten_grants(db, parent.id, part["id"])
    else:
        part["status"] = "in_progress"
        part.pop("completed_at", None)
    parent.data_json = d.canonical(original)
    parent.version += 1
    parent.updated_at = d.now()
    sync_parent(db, parent, original, actor)
