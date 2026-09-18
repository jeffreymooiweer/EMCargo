"""Delivery planning, inventory reservations and append-only execution evidence.

Every write first acquires the inventory lock. This matters when two different
deliveries reserve the same shipment: a per-delivery revision alone is not enough.
Source exports are snapshots, never pointers that silently change issued papers.
"""
from __future__ import annotations
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from sqlalchemy import update
from app.core.messages import error
from app.models.delivery import Delivery, DeliveryAccount, DeliveryFile, DeliveryGrant, DeliveryLock
from app.models.shipment import Shipment
from app.schemas.deliveries import DeliveryIn, ActionIn, ReviewIn, EventIn
from app.services import departments

MODES = {"road": "ADR", "rail": "RID", "inland": "ADN", "sea": "IMDG", "air": "IATA_DGR"}
LIMITED_ROLES = {"operator", "recipient", "external"}
RESERVED = {"planned", "released", "in_progress", "completed", "closed"}
MAX_RECORD = 16 * 1024 * 1024


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def decimal(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite():
            raise ValueError()
        return result
    except (ValueError, InvalidOperation, TypeError):
        raise error(422, "delivery.quantity")


def tasks(db, user):
    row = db.get(DeliveryAccount, user.id)
    if row:
        return set(json.loads(row.roles_json)), set(json.loads(row.modes_json))
    roles = {"operator": {"operator"}, "recipient": {"recipient"}, "external": set(),
             "shipment": {"shipment"}, "planner": {"shipment", "planner"},
             "assessor": {"assessor"}}.get(user.role, {"shipment", "planner"})
    if user.role in {"admin", "dg_specialist"}:
        roles = roles | {"assessor"}
    return roles, set(MODES) if user.role in {"admin", "dg_specialist"} else set()


def planner(db, user):
    if user.role in LIMITED_ROLES or "planner" not in tasks(db, user)[0]:
        raise error(403, "delivery.permission")


def execution_only(db, user):
    return user.role in LIMITED_ROLES or (user.role not in {"admin", "super_user", "dg_specialist"} and not bool(tasks(db, user)[0] & {"shipment", "planner", "assessor"}))


def lock(db):
    # INSERT OR IGNORE also covers fresh databases created directly in tests.
    from sqlalchemy.dialects.sqlite import insert
    if db.bind.dialect.name == "sqlite":
        db.execute(insert(DeliveryLock).values(id=1, version=0).on_conflict_do_nothing())
    elif db.get(DeliveryLock, 1) is None:
        db.add(DeliveryLock(id=1, version=0))
        db.flush()
    db.execute(update(DeliveryLock).where(DeliveryLock.id == 1).values(version=DeliveryLock.version + 1))


def grants(db, user, record):
    return db.query(DeliveryGrant).filter(
        DeliveryGrant.user_id == user.id, DeliveryGrant.delivery_id == record.id,
        DeliveryGrant.revoked_at.is_(None), DeliveryGrant.expires_at > now()).all()


def internal(db, user, record):
    return user.role not in LIMITED_ROLES and bool(tasks(db, user)[0] & {"shipment", "planner", "assessor"}) and departments.may_see(record, user)


def get(db, user, delivery_id, *, write=False):
    if write:
        lock(db)
    record = db.get(Delivery, delivery_id, populate_existing=True)
    if not record or not (internal(db, user, record) or grants(db, user, record)):
        raise error(404, "delivery.not_found")
    return record


def data(record):
    return json.loads(record.data_json)


def leg(data, leg_id):
    result = next((l for l in data["legs"] if l["id"] == leg_id), None)
    if result is None:
        raise error(404, "delivery.not_found")
    return result


def check_version(record, version):
    if record.version != version:
        raise error(409, "delivery.conflict")


def save(db, record, value, actor, action):
    value.setdefault("history", []).append({"at": stamp(), "actor": actor.id, "action": action})
    encoded = canonical(value)
    if len(encoded.encode()) > MAX_RECORD:
        raise error(413, "delivery.too_large")
    record.data_json = encoded
    record.version += 1
    record.updated_at = now()
    from app.services.delivery_followups import sync_parent
    sync_parent(db, record, value, actor)
    db.commit()
    db.refresh(record)
    from app.services import audit
    audit.record(db, "delivery.changed", actor=actor, target=("delivery", record.id), summary=action)
    return view(db, actor, record)


def source_goods(export):
    return {str(g.get("cargo_goods_id") if g.get("cargo_goods_id") is not None else g.get("line_id", f"line-{i}")): g
            for i, g in enumerate(export.get("goods", [])) if g.get("include", True)}


def source_fingerprint(export):
    return digest({**{k: export.get(k) for k in ("consignment", "goods", "cargo", "dangerous_goods")}, **({"routing": export["routing"]} if export.get("routing") is not None else {})})


def selected(value, leg_id):
    return [{**{k: v for k, v in a.items() if k != "leg_quantities"}, "quantity": a.get("leg_quantities", {}).get(leg_id, a["quantity"])}
            for a in value["allocations"] if leg_id in a["leg_ids"]]


def active_allocations(value):
    states = {l["id"]: l["status"] for l in value["legs"]}
    return [a for a in value["allocations"] if any(states[x] in RESERVED for x in a["leg_ids"])]


def reserved_quantity(value, allocation):
    # Retries move existing goods. The original reservation remains consumed;
    # an administrative disposition must never create new warehouse stock.
    return Decimal(0) if value.get("followup") else decimal(allocation["quantity"])


def occupied_units(value, part):
    from app.services.delivery_cargo import occupied
    return occupied(value, part)


def unit_in_transit(db, unit_id):
    from app.services.delivery_unloading import released
    return any(unit_id in occupied_units(value, part) and not released(value, part, unit_id)
               for record in db.query(Delivery).all() for value in [data(record)]
               for part in value["legs"] if part["status"] in RESERVED)


def fingerprint(value, part):
    return digest({**({"stops": value["stops"]} if value.get("stops") else {}), "unpacked": bool(value.get("unpacked")), "leg": {k: v for k, v in part.items() if k not in {"status", "review", "assessment", "completed_at"}},
                   "allocations": selected(value, part["id"]),
                   "sources": {str(a["shipment_id"]): value["sources"][str(a["shipment_id"])]
                               for a in selected(value, part["id"])}})


def load_sources(db, user, payload):
    sources = {}
    department = user.department_id
    for allocation in payload.allocations:
        key = str(allocation.shipment_id)
        if key in sources:
            continue
        source = db.get(Shipment, allocation.shipment_id)
        if not source or source.is_draft or not departments.may_see(source, user):
            raise error(404, "delivery.source")
        if sources and source.department_id != department:
            raise error(422, "delivery.department")
        department = source.department_id
        export = json.loads(source.export_json)
        sources[key] = {"reference": source.reference, "export": export, "fingerprint": source_fingerprint(export)}
    return sources, department


def validate_sources(db, value):
    for sid, source in value["sources"].items():
        current = db.get(Shipment, int(sid), populate_existing=True)
        if not current or current.is_draft or source_fingerprint(json.loads(current.export_json)) != source["fingerprint"]:
            raise error(409, "delivery.source_changed")


def validate_quantities(value):
    from app.services.delivery_routing import validate as validate_routing
    validate_routing(value)
    from app.services.cargo import DISCRETE
    totals = defaultdict(Decimal)
    paths = {p["id"]: p for p in value["legs"]}
    for allocation in value["allocations"]:
        export = value["sources"][str(allocation["shipment_id"])]["export"]
        goods = source_goods(export).get(allocation["goods_id"])
        if goods is None:
            raise error(422, "delivery.source")
        qty = decimal(allocation["quantity"])
        if str(goods.get("unit", "")).strip().lower() in DISCRETE and qty != qty.to_integral_value():
            raise error(422, "cargo.whole_items")
        totals[(allocation["shipment_id"], allocation["goods_id"])] += qty
        if totals[(allocation["shipment_id"], allocation["goods_id"])] > decimal(goods.get("quantity")):
            raise error(409, "delivery.overallocated")
        itinerary = [paths[x] for x in allocation["leg_ids"]]
        for before, after in zip(itinerary, itinerary[1:]):
            if before["destination"].strip().casefold() != after["origin"].strip().casefold():
                raise error(422, "delivery.itinerary")
            if before.get("planned_end") and after.get("planned_start") and datetime.fromisoformat(before["planned_end"]) > datetime.fromisoformat(after["planned_start"]):
                raise error(422, "delivery.itinerary")
            earlier = decimal(allocation.get("leg_quantities", {}).get(before["id"], allocation["quantity"]))
            onward = decimal(allocation.get("leg_quantities", {}).get(after["id"], allocation["quantity"]))
            if onward < earlier and (before["status"] not in {"completed", "closed"}
                    or receipt_totals(value, before["id"])[allocation["id"]]["quantity"] != onward):
                raise error(409, "delivery.quantity")
            if str(goods.get("unit", "")).strip().lower() in DISCRETE and onward != onward.to_integral_value():
                raise error(422, "cargo.whole_items")
    from app.services.delivery_cargo import validate
    validate(value)


def reserve(db, record, value):
    validate_quantities(value)
    totals = defaultdict(Decimal)
    other_records = db.query(Delivery).filter(Delivery.id != record.id).all()
    for current in [value] + [data(r) for r in other_records]:
        for a in active_allocations(current):
            totals[(a["shipment_id"], a["goods_id"])] += reserved_quantity(current, a)
    from app.services.delivery_routing import reserve as reserve_distributions
    reserve_distributions([value] + [data(r) for r in other_records], value)
    from app.services.delivery_cargo import reserve_units
    reserve_units([value] + [data(r) for r in other_records])
    for a in active_allocations(value):
        goods = source_goods(value["sources"][str(a["shipment_id"])]["export"])[a["goods_id"]]
        if totals[(a["shipment_id"], a["goods_id"])] > decimal(goods.get("quantity")):
            raise error(409, "delivery.overallocated")
    from app.services.delivery_unloading import released as unit_released
    from app.services.delivery_followups import ancestors
    predecessors = ancestors(db, value)
    for part in value["legs"]:
        if part["status"] not in {"planned", "released", "in_progress"}:
            continue
        from app.services.delivery_load_units import available
        available(db, value, part)
        from app.models.user import Equipment
        if any(db.get(Equipment, eid) is None for eid in part.get("equipment_ids", [])):
            raise error(404, "equipment.not_found")
        for other in other_records:
            if other.id in predecessors:
                continue
            other_value = data(other)
            for occupied in other_value["legs"]:
                shared_units = occupied_units(value, part) & occupied_units(other_value, occupied)
                live_units = {uid for uid in shared_units if occupied["status"] in RESERVED and not unit_released(other_value, occupied, uid)}
                shared_equipment = set(part.get("equipment_ids", [])) & set(occupied.get("equipment_ids", []))
                if live_units or (shared_equipment and occupied["status"] in {"planned", "released", "in_progress"}):
                    # A planned end is not evidence that an actual load has ended.
                    separate = occupied["status"] in {"planned", "released"} and part["status"] in {"planned", "released"} and (
                        (part.get("planned_end") and occupied.get("planned_start") and datetime.fromisoformat(part["planned_end"]) <= datetime.fromisoformat(occupied["planned_start"]))
                        or (occupied.get("planned_end") and part.get("planned_start") and datetime.fromisoformat(occupied["planned_end"]) <= datetime.fromisoformat(part["planned_start"])))
                    if not separate:
                        raise error(409, "cargo.unit_in_use")



def create(db, user, payload: DeliveryIn):
    planner(db, user)
    lock(db)
    sources, department = load_sources(db, user, payload)
    value = payload.model_dump(mode="json", exclude={"version", "name"})
    value.update(sources=sources, events=[], history=[])
    from app.services.delivery_routing import hydrate as hydrate_stops
    hydrate_stops(value, None, user)
    from app.services.delivery_load_units import hydrate
    hydrate(db, value)
    for part in value["legs"]:
        part["status"] = "draft"
    validate_quantities(value)
    record = Delivery(id=str(uuid4()), name=payload.name, department_id=department,
                      created_by_id=user.id, version=0, data_json="{}")
    db.add(record)
    return save(db, record, value, user, "created")


def edit(db, user, record, payload: DeliveryIn):
    planner(db, user)
    check_version(record, payload.version)
    previous = data(record)
    old_legs = {l["id"]: l for l in previous["legs"]}
    sources, department = load_sources(db, user, payload)
    if previous["allocations"] and department != record.department_id:
        raise error(422, "delivery.department")
    value = payload.model_dump(mode="json", exclude={"version", "name"})
    value.update(sources=sources, events=previous["events"], history=previous["history"])
    from app.services.delivery_routing import hydrate as hydrate_stops
    hydrate_stops(value, previous, user)
    from app.services.delivery_load_units import hydrate
    hydrate(db, value)
    for key in ("decisions", "legacy_trip_id", "legacy_consignments"):
        if key in previous:
            value[key] = previous[key]
    from app.services.delivery_followups import preserve
    preserve(previous, value)
    for part in value["legs"]:
        old = old_legs.get(part["id"])
        part["status"] = old["status"] if old else "draft"
        if old and old["status"] != "draft":
            if fingerprint(value, part) != fingerprint(previous, old):
                raise error(409, "delivery.frozen")
            part.update(old)
    if any(l["status"] != "draft" and l["id"] not in {p["id"] for p in value["legs"]} for l in previous["legs"]):
        raise error(409, "delivery.frozen")
    reserve(db, record, value)
    record.name = payload.name
    record.department_id = department
    return save(db, record, value, user, "updated")


def assessment(value, part, language="en"):
    from app.services.dg.trip import check_trip
    from app.services.dg.compliance import check_compliance
    from app.services.regulatory_manifest import summary
    consignments = []
    for sid in sorted({str(a["shipment_id"]) for a in selected(value, part["id"])}):
        source = value["sources"][sid]
        from app.services.delivery_dg import selected_entries
        entries = selected_entries(value, part, int(sid))
        consignments.append({"name": source["reference"], "entries": entries})
    entries = [entry for c in consignments for entry in c["entries"]]
    profiles = [MODES[part["mode"]]]
    trip = check_trip(consignments, profiles, language, float(part["max_mass_tonnes"]) if part.get("max_mass_tonnes") else None) if entries else {}
    checks = check_compliance(entries, profiles, language) if entries else {}
    def forbidden(node):
        if isinstance(node, dict):
            if node.get("severity") in {"error", "blocking", "forbidden"} or node.get("status") in {"forbidden", "prohibited", "not_permitted"}:
                return True
            return any(forbidden(v) for v in node.values())
        return isinstance(node, list) and any(forbidden(v) for v in node)
    manual = bool(entries) or part["mode"] != "road" or not part.get("max_mass_tonnes")
    return {"has_dg": bool(entries), "manual_required": manual,
            "blocked": forbidden(checks) or forbidden(trip), "trip": trip, "checks": checks,
            "coverage": "partial" if manual else "ordinary_goods",
            "editions": summary().get("editions", {}), "fingerprint": fingerprint(value, part)}


def validate_cargo(value, part):
    """Unknown mass and known capacity violations cannot receive a manual pass."""
    from app.services.cargo import assess
    from app.schemas.cargo import CargoManifest
    from app.services.delivery_documents import payload_for
    total = Decimal(0)
    counted_units = set()
    shared_content = Decimal(0)
    for sid in {str(a["shipment_id"]) for a in selected(value, part["id"])}:
        export = value["sources"][sid]["export"]
        goods = source_goods(export)
        migrated = set()
        if (export.get("cargo") and not value.get("unpacked")) or part.get("load_unit"):
            projected = payload_for(value, part, int(sid), "packing_list", "en")
            manifest = CargoManifest.model_validate(projected.cargo)
            migrated = {str(u.legacy_goods_id) for u in manifest.units if u.legacy_goods_id is not None}
            result = assess(manifest, projected.lines)
            if result["totals"]["transport_gross_kg"] is None:
                raise error(422, "cargo.documents_incomplete")
            if any(issue["code"] in {"cargo.payload_exceeded", "cargo.gross_exceeded"} for issue in result["issues"]):
                raise error(422, "cargo.payload_exceeded")
            if part.get("load_unit"):
                shared_content += decimal(next(u["content_kg"] for u in result["units"] if u["id"] == part["load_unit"]["id"]))
            for unit in manifest.units:
                if unit.id not in counted_units:
                    total += decimal(unit.tare_kg)
                    counted_units.add(unit.id)
        for allocation in selected(value, part["id"]):
            if str(allocation["shipment_id"]) == sid:
                if allocation["goods_id"] in migrated:
                    continue
                line = goods[allocation["goods_id"]]
                if line.get("weight_total_kg") is None or decimal(line["weight_total_kg"]) <= 0:
                    raise error(422, "cargo.documents_incomplete")
                total += decimal(line["weight_total_kg"]) * decimal(allocation["quantity"]) / decimal(line["quantity"])
    shared = part.get("load_unit")
    if shared and ((shared.get("max_payload_kg") is not None and shared_content > decimal(shared["max_payload_kg"])) or (shared.get("max_gross_kg") is not None and shared_content + decimal(shared["tare_kg"]) > decimal(shared["max_gross_kg"]))):
        raise error(422, "cargo.payload_exceeded")
    if part.get("max_mass_tonnes") and total > decimal(part["max_mass_tonnes"]) * 1000:
        raise error(422, "cargo.gross_exceeded")


def review(db, user, record, leg_id, payload: ReviewIn):
    check_version(record, payload.version)
    roles, modes = tasks(db, user)
    value = data(record)
    part = leg(value, leg_id)
    if "assessor" not in roles or part["mode"] not in modes or not internal(db, user, record):
        raise error(403, "delivery.permission")
    if part["status"] != "planned":
        raise error(409, "delivery.state")
    validate_sources(db, value)
    validate_cargo(value, part)
    verify_sources(value, part)
    result = assessment(value, part, payload.language)
    if result["blocked"]:
        raise error(409, "delivery.blocked")
    if result["has_dg"] and user.role != "dg_specialist":
        raise error(403, "delivery.permission")
    for fid in payload.document_ids:
        document = db.get(DeliveryFile, fid)
        if not document or document.delivery_id != record.id or document.leg_id != leg_id or document.fingerprint != result["fingerprint"] or document.kind != "external":
            raise error(409, "delivery.document")
    part["assessment"] = result
    part["review"] = {"actor": user.id, "at": stamp(), "reason": payload.reason,
                      "fingerprint": result["fingerprint"], "editions": result["editions"], "document_ids": payload.document_ids}
    return save(db, record, value, user, "reviewed")


def action(db, user, record, leg_id, payload: ActionIn):
    planner(db, user)
    check_version(record, payload.version)
    value = data(record)
    part = leg(value, leg_id)
    status = part["status"]
    if payload.action == "plan":
        if status != "draft" or not selected(value, leg_id) or not part["origin"] or not part["destination"]:
            raise error(409, "delivery.state")
        validate_sources(db, value)
        part["status"] = "planned"
        reserve(db, record, value)
    elif payload.action in {"unplan", "reopen"}:
        if status not in {"planned", "released"} or (status == "released" and not payload.reason):
            raise error(409, "delivery.state")
        guard_following(value, leg_id)
        part["status"] = "draft"
        part.pop("review", None)
        part.pop("assessment", None)
    elif payload.action == "release":
        if status != "planned" or not part["carrier"] or not part.get("planned_start"):
            raise error(409, "delivery.state")
        validate_sources(db, value)
        validate_cargo(value, part)
        result = assessment(value, part, payload.language)
        if result["blocked"]:
            raise error(409, "delivery.blocked")
        verify_sources(value, part)
        if result["manual_required"] and part.get("review", {}).get("fingerprint") != result["fingerprint"]:
            raise error(409, "delivery.review")
        part["assessment"] = result
        part["status"] = "released"
    elif payload.action == "start":
        if status != "released":
            raise error(409, "delivery.state")
        validate_sources(db, value)
        part["status"] = "in_progress"
    elif payload.action == "cancel":
        if value.get("followup") or status not in {"draft", "planned", "released"} or not payload.reason:
            raise error(409, "delivery.state")
        guard_following(value, leg_id)
        part["status"] = "cancelled"
    elif payload.action == "close":
        if status != "completed" or unresolved(value, leg_id):
            raise error(409, "delivery.state")
        part["status"] = "closed"
    value.setdefault("decisions", []).append({"leg_id": leg_id, "action": payload.action, "reason": payload.reason, "actor": user.id, "at": stamp()})
    return save(db, record, value, user, payload.action)


def guard_following(value, leg_id):
    """A predecessor cannot silently invalidate an already planned transfer."""
    if any(leg(value, following)["status"] not in {"draft", "cancelled"}
           for allocation in selected(value, leg_id)
           for following in allocation["leg_ids"][allocation["leg_ids"].index(leg_id) + 1:]):
        raise error(409, "delivery.frozen")


def verify_sources(value, part):
    from app.services.dg.source_verification import require_verified_payload
    for sid in {str(a["shipment_id"]) for a in selected(value, part["id"])}:
        require_verified_payload({**value["sources"][sid]["export"],
                                  "profiles": [MODES[part["mode"]]], "modality": part["mode"]})


def effective_events(value, leg_id):
    events = [e for e in value["events"] if e["leg_id"] == leg_id]
    replaced = {e.get("corrects") for e in events if e["kind"] == "correction"}
    return [e for e in events if e["request_id"] not in replaced and e["kind"] != "resolution"]


def receipt_totals(value, leg_id):
    totals = defaultdict(lambda: {"quantity": Decimal(0), "damaged": Decimal(0), "refused": Decimal(0)})
    for event in effective_events(value, leg_id):
        if event.get("corrected_kind", event["kind"]) != "receipt":
            continue
        for line in event["lines"]:
            for field in totals[line["allocation_id"]]:
                totals[line["allocation_id"]][field] += decimal(line[field])
    return totals


def unresolved(value, leg_id):
    totals = receipt_totals(value, leg_id)
    resolved = {line["allocation_id"] for e in value["events"]
                if e["leg_id"] == leg_id and e["kind"] == "resolution"
                and (e.get("resolution") == "accept" or e.get("followup_complete", False))
                for line in e["lines"]}
    return [a["id"] for a in selected(value, leg_id) if a["id"] not in resolved and
            (totals[a["id"]]["quantity"] != decimal(a["quantity"]) or totals[a["id"]]["damaged"] or totals[a["id"]]["refused"])]


def allowed_allocations(db, user, record, value, leg_id, role):
    if internal(db, user, record) and "planner" in tasks(db, user)[0]:
        return {a["id"] for a in selected(value, leg_id)}
    allowed = set()
    for grant in grants(db, user, record):
        if grant.leg_id == leg_id and grant.role == role:
            from app.services.delivery_routing import grant_ids
            allowed.update(grant_ids(grant, value))
    return allowed


def event(db, user, record, leg_id, payload: EventIn):
    value = data(record)
    part = leg(value, leg_id)
    role = "operator" if payload.kind in {"load", "unpack"} else "recipient"
    allowed = allowed_allocations(db, user, record, value, leg_id, role)
    if payload.kind not in {"load", "unpack"}:
        transfers = {a["id"] for a in selected(value, leg_id) if a["leg_ids"][-1] != leg_id}
        allowed -= transfers
        allowed |= transfers & allowed_allocations(db, user, record, value, leg_id, "operator")
    if not {line.allocation_id for line in payload.lines} <= allowed:
        raise error(403, "delivery.permission")
    if payload.kind in {"correction", "resolution"}:
        planner(db, user)
        if any(leg(value, following)["status"] in {"in_progress", "completed", "closed"}
               for allocation in selected(value, leg_id) for following in allocation["leg_ids"][allocation["leg_ids"].index(leg_id) + 1:]):
            raise error(409, "delivery.frozen")
    body = payload.model_dump(mode="json", exclude={"version"})
    previous = next((e for e in value["events"] if e["request_id"] == payload.request_id), None)
    if previous:
        if previous.get("request_hash") != digest(body) or previous["actor"] != user.id:
            raise error(409, "delivery.conflict")
        return view(db, user, record)
    check_version(record, payload.version)
    if payload.kind == "unpack":
        from app.services.delivery_dg import selected_entries
        if not value.get("followup") or value.get("unpacked") or part["status"] != "draft":
            raise error(409, "delivery.state")
        expected = {a["id"]: decimal(a["quantity"]) for a in selected(value, leg_id)}
        if ({line.allocation_id: line.quantity for line in payload.lines} != expected
                or any(line.damaged or line.refused for line in payload.lines)):
            raise error(409, "delivery.quantity")
        if len(payload.reason) < 10 or payload.occurred_at > now() + timedelta(minutes=5):
            raise error(422, "delivery.time")
        if payload.signature_image or payload.file_ids:
            raise error(422, "delivery.document")
        if any(selected_entries(value, part, sid) for sid in {a["shipment_id"] for a in selected(value, leg_id)}):
            raise error(422, "delivery.dg_split")
        body.pop("signature_image", None)
        body.update(actor=user.id, leg_id=leg_id, recorded_at=stamp(), request_hash=digest(payload.model_dump(mode="json", exclude={"version"})))
        value["unpacked"] = True
        value["events"].append(body)
        return save(db, record, value, user, "unpack")
    if part["status"] not in {"released", "in_progress", "completed"}:
        raise error(409, "delivery.state")
    if part["status"] == "completed" and payload.kind not in {"correction", "resolution"}:
        raise error(409, "delivery.state")
    if payload.occurred_at > now() + timedelta(minutes=5):
        raise error(422, "delivery.time")
    if payload.kind == "correction":
        # Once a disposition has freed stock for another attempt, changing its
        # receipt would resurrect the original reservation and double-book it.
        if any(e["kind"] == "resolution" and e["leg_id"] == leg_id
               and {l["allocation_id"] for l in e["lines"]} & {l.allocation_id for l in payload.lines}
               for e in value["events"]):
            raise error(409, "delivery.frozen")
        target = next((e for e in effective_events(value, leg_id) if e["request_id"] == payload.corrects), None)
        if not target or target["kind"] in {"resolution", "unload", "unpack"} or {l["allocation_id"] for l in target["lines"]} != {l.allocation_id for l in payload.lines}:
            raise error(409, "delivery.state")
        body["corrected_kind"] = target.get("corrected_kind", target["kind"])
    for a in selected(value, leg_id):
        if a["id"] not in {l.allocation_id for l in payload.lines}:
            continue
        index = a["leg_ids"].index(leg_id)
        if index and leg(value, a["leg_ids"][index - 1])["status"] not in {"completed", "closed"}:
            raise error(409, "delivery.itinerary")
        if index and receipt_totals(value, a["leg_ids"][index - 1])[a["id"]]["quantity"] < decimal(a["quantity"]):
            raise error(409, "delivery.quantity")
    if payload.kind == "resolution":
        if not any(e["kind"] == "receipt" or e.get("corrected_kind") == "receipt" for e in effective_events(value, leg_id)):
            raise error(409, "delivery.state")
        if any(e["kind"] == "resolution" and e["leg_id"] == leg_id and {l["allocation_id"] for l in e["lines"]} & {l.allocation_id for l in payload.lines} for e in value["events"]):
            raise error(409, "delivery.state")
        totals = receipt_totals(value, leg_id)
        for line in payload.lines:
            allocation = next(a for a in selected(value, leg_id) if a["id"] == line.allocation_id)
            received = totals[allocation["id"]]
            shortage = decimal(allocation["quantity"]) - received["quantity"]
            discrepancy = shortage + received["damaged"]
            expected = received["refused"] + received["damaged"] if payload.resolution == "return" else discrepancy
            if payload.resolution == "return" and shortage != received["refused"]:
                raise error(409, "delivery.quantity")
            if (line.quantity != expected or expected <= 0 or line.damaged or line.refused
                    or allocation["id"] not in unresolved(value, leg_id)):
                raise error(409, "delivery.quantity")
            if payload.resolution == "redelivery" and received["damaged"]:
                # Replacement stock must come from a new source shipment;
                # the damaged goods are still physically at the receiver.
                raise error(409, "delivery.quantity")
            if payload.resolution != "accept" and leg_id != allocation["leg_ids"][-1]:
                raise error(409, "delivery.itinerary")
    body.update(leg_id=leg_id, actor=user.id, recorded_at=stamp(), request_hash=digest(payload.model_dump(mode="json", exclude={"version"})))
    body.pop("signature_image", None)
    shipment_ids = {a["shipment_id"] for a in selected(value, leg_id) if a["id"] in {line.allocation_id for line in payload.lines}}
    for file_id in payload.file_ids:
        evidence = db.get(DeliveryFile, file_id)
        if not evidence or evidence.delivery_id != record.id or evidence.leg_id != leg_id or evidence.kind != "proof" or not set(json.loads(evidence.shipment_ids_json)) <= shipment_ids or (evidence.allocation_ids_json and not set(json.loads(evidence.allocation_ids_json)) <= {line.allocation_id for line in payload.lines}):
            raise error(403, "delivery.permission")
    value["events"].append(body)
    totals = receipt_totals(value, leg_id)
    load_totals = defaultdict(Decimal)
    for e in effective_events(value, leg_id):
        if e["kind"] == "load" or e.get("corrected_kind") == "load":
            for line in e["lines"]:
                load_totals[line["allocation_id"]] += decimal(line["quantity"])
    for a in selected(value, leg_id):
        received = totals[a["id"]]
        amount = decimal(a["quantity"])
        if load_totals[a["id"]] > amount or received["quantity"] + received["refused"] > load_totals[a["id"]] or received["damaged"] > received["quantity"]:
            raise error(409, "delivery.quantity")
    part["status"] = "in_progress"
    part.pop("completed_at", None)
    if not unresolved(value, leg_id):
        part["status"] = "completed"
        part["completed_at"] = stamp()
        shorten_grants(db, record.id, leg_id)
    if payload.kind == "resolution" and payload.resolution != "accept":
        from app.services.delivery_followups import create as create_followup
        create_followup(db, user, record, value, part, body)
    if payload.signature_image:
        from app.services.delivery_documents import store
        from app.services.documents.signature import decode_signature_image
        try:
            signature = decode_signature_image(payload.signature_image)
        except ValueError as exc:
            raise error(422, "delivery.document") from exc
        evidence = store(db, record, part, shipment_ids, signature, "receipt-signature.png", "image/png", "proof",
                         {"event_id": payload.request_id}, [line.allocation_id for line in payload.lines])
        body["file_ids"] = [*payload.file_ids, evidence.id]
    return save(db, record, value, user, payload.kind)


def shorten_grants(db, delivery_id, leg_id):
    # Completion can only shorten an assignment, never extend it.
    for grant in db.query(DeliveryGrant).filter_by(delivery_id=delivery_id, leg_id=leg_id).all():
        expires = grant.expires_at.replace(tzinfo=timezone.utc) if grant.expires_at.tzinfo is None else grant.expires_at
        grant.expires_at = min(expires, now() + timedelta(days=7))


def aggregate(value):
    statuses = {l["status"] for l in value["legs"]}
    if not statuses or statuses == {"draft"}:
        return "draft"
    if statuses <= {"cancelled"}:
        return "cancelled"
    if statuses <= {"closed", "cancelled"}:
        return "closed"
    if statuses <= {"completed", "closed", "cancelled"}:
        return "completed"
    if any(e["kind"] in {"receipt", "correction"} for e in value["events"]):
        return "partial"
    if "in_progress" in statuses:
        return "in_progress"
    if "released" in statuses:
        return "released"
    return "planned"


def view(db, user, record):
    value = data(record)
    from app.services.delivery_cargo import roots
    from app.services.delivery_unloading import contents, released
    original = data(record)
    full = internal(db, user, record)
    permitted = grants(db, user, record) if not full else []
    allowed = {g.leg_id: set() for g in permitted}
    for grant in permitted:
        from app.services.delivery_routing import grant_ids
        allowed[grant.leg_id].update(grant_ids(grant, original))
    if not full:
        value = {key: value[key] for key in ("legs", "allocations", "events", "sources")}
        value["legs"] = [l for l in value["legs"] if l["id"] in allowed]
        for part in value["legs"]:
            part.pop("review", None)
            part.pop("assessment", None)
            part["document_values"] = {}
        value["allocations"] = [a for a in value["allocations"] if any(a["id"] in allowed.get(l, set()) for l in a["leg_ids"])]
        visible_ids = {lid: {a["id"] for a in value["allocations"]
                             if lid in a["leg_ids"] and a["id"] in sids}
                       for lid, sids in allowed.items()}
        for a in value["allocations"]:
            final_leg = a["leg_ids"][-1]
            a["receivable_leg_ids"] = [lid for lid in a["leg_ids"]
                if a["id"] in allowed_allocations(db, user, record, original, lid, "recipient" if lid == final_leg else "operator")]
            a["leg_ids"] = [l for l in a["leg_ids"] if a["id"] in allowed.get(l, set())]
            a["quantity"] = a.get("leg_quantities", {}).get(a["leg_ids"][0], a["quantity"])
            a["leg_quantities"] = {lid: quantity for lid, quantity in a.get("leg_quantities", {}).items() if lid in a["leg_ids"]}
        value["events"] = [{**{k: v for k, v in e.items() if k not in {"request_hash", "actor", "followup_id", "followup_complete"}},
                            "lines": [line for line in e["lines"] if line["allocation_id"] in visible_ids.get(e["leg_id"], set())]}
                           for e in value["events"] if any(line["allocation_id"] in visible_ids.get(e["leg_id"], set()) for line in e["lines"])]
        # Shared execution remarks and signatures can name another receiver.
        source_events = {e["request_id"]: e for e in original["events"]}
        for event in value["events"]:
            if len(event["lines"]) != len(source_events[event["request_id"]]["lines"]):
                for key in ("signature_image", "signature", "reason", "recipient", "file_ids"):
                    event.pop(key, None)
        own_points = set()
        for a in value["allocations"]:
            from app.services.delivery_routing import distributions
            distribution = distributions(original["sources"][str(a["shipment_id"])] ["export"]).get(a.get("source_distribution_id"))
            if distribution:
                own_points.update((a["shipment_id"], distribution[k]) for k in ("pickup_id", "delivery_id"))
        safe_stops = [s for s in original.get("stops", []) if s["kind"] == "transfer" or (s.get("shipment_id"), s.get("location_id")) in own_points]
        value["stops"] = [{k: v for k, v in stop.items() if k not in {"original", "changes", "override_reason"}} for stop in safe_stops]
        safe_ids = {s["id"] for s in safe_stops}
        for part in value["legs"]:
            if original.get("stops"):
                if part.get("origin_stop_id") not in safe_ids: part["origin"] = ""
                if part.get("destination_stop_id") not in safe_ids: part["destination"] = ""
        value.pop("history", None)
        value.pop("decisions", None)
        ids = {str(a["shipment_id"]) for a in value["allocations"]}
        value["sources"] = {sid: {"reference": s["reference"], "goods": [
            {"id": gid, "description": g.get("description", ""), "unit": g.get("unit", "")}
            for gid, g in source_goods(s["export"]).items() if any(str(a["shipment_id"]) == sid and a["goods_id"] == gid for a in value["allocations"])]}
            for sid, s in value["sources"].items() if sid in ids}
    files = db.query(DeliveryFile).filter_by(delivery_id=record.id).all()
    value["files"] = [file_info(f, data(record), files) for f in files if full or file_visible(f, allowed, original)]
    value.update(id=record.id, name=record.name, version=record.version, status=aggregate(value),
                 department_id=record.department_id if full else None, can_plan=full and "planner" in tasks(db, user)[0],
                 can_review=full and "assessor" in tasks(db, user)[0],
                 assignments=[{"id": g.id, "role": g.role, "leg_id": g.leg_id, "shipment_ids": json.loads(g.shipment_ids_json), "allocation_ids": sorted(grant_ids(g, original))} for g in permitted])
    value["receipt_totals"] = {l["id"]: {a: {k: str(v) for k, v in amounts.items()} for a, amounts in receipt_totals(value, l["id"]).items()} for l in value["legs"]}
    value["packing_units"] = {sid: [{**g, "goods": {gid: str(q) for gid, q in g["goods"].items()}} for g in roots(s["export"]).values()] for sid, s in original["sources"].items()} if full and not original.get("unpacked") else {}
    value["unpack_legs"] = [p["id"] for p in original["legs"] if original.get("followup") and not original.get("unpacked") and p["status"] == "draft" and {a["id"] for a in selected(original, p["id"])} <= allowed_allocations(db, user, record, original, p["id"], "operator")]
    value["cargo_units"] = {}
    for part in value["legs"]:
        source_part = leg(original, part["id"])
        permitted_ids = {a["id"] for a in selected(value, part["id"])}
        units = {u["id"]: u for sid in {str(a["shipment_id"]) for a in selected(original, part["id"])}
                 for u in (original["sources"][sid]["export"].get("cargo") or {}).get("units", [])}
        if source_part.get("load_unit"):
            units[source_part["load_unit"]["id"]] = source_part["load_unit"]
        value["cargo_units"][part["id"]] = [{"id": uid, "code": units[uid]["code"], "name": units[uid]["name"], "released": released(original, source_part, uid)}
            for uid in sorted(occupied_units(original, source_part)) if {a["id"] for a in contents(original, source_part, uid)} <= permitted_ids]
    if not full:
        visible_files = {f["id"] for f in value["files"]}
        for event in value["events"]:
            event["file_ids"] = [fid for fid in event.get("file_ids", []) if fid in visible_files]
            if "unit_ids" in event:
                event["unit_ids"] = [uid for uid in event["unit_ids"] if any(u["id"] == uid for u in value["cargo_units"].get(event["leg_id"], []))]
    return value


def file_visible(file, allowed, value):
    shipments = set(json.loads(file.shipment_ids_json))
    allocations = set(json.loads(file.allocation_ids_json or "[]"))
    if not allocations:
        if any(value["sources"][str(s)]["export"].get("routing") for s in shipments if str(s) in value["sources"]):
            return False
        allocations = {a["id"] for a in selected(value, file.leg_id) if a["shipment_id"] in shipments}
    scope = json.loads(file.metadata_json).get("scope") or {file.leg_id: {}}
    return bool(allocations) and all(allocations <= allowed.get(lid, set()) for lid in scope)


def file_info(file, value, siblings=()):
    part = next((p for p in value["legs"] if p["id"] == file.leg_id), None)
    metadata = json.loads(file.metadata_json)
    current = bool(part and file.fingerprint == fingerprint(value, part)
                   and part["status"] in {"released", "in_progress", "completed", "closed"})
    for lid, snapshot in metadata.get("scope", {}).items():
        scoped = next((p for p in value["legs"] if p["id"] == lid), None)
        current = current and bool(scoped and scoped["status"] in {"released", "in_progress", "completed", "closed"}
                                   and fingerprint(value, scoped) == snapshot["fingerprint"])
    if file.kind == "external":
        current = current and file.id in part.get("review", {}).get("document_ids", [])
    elif file.kind == "issued":
        current = current and not any(other.kind == "issued" and other.leg_id == file.leg_id
            and other.shipment_ids_json == file.shipment_ids_json
            and other.allocation_ids_json == file.allocation_ids_json
            and json.loads(other.metadata_json).get("document_key") == metadata.get("document_key")
            and set(json.loads(other.metadata_json).get("scope", {file.leg_id: {}})) == set(metadata.get("scope", {file.leg_id: {}}))
            and json.loads(other.metadata_json).get("version", 0) > metadata.get("version", 0)
            for other in siblings)
    elif file.kind == "proof":
        # Evidence remains evidence after a subsequent correction or reopening.
        current = True
    return {"id": file.id, "leg_id": file.leg_id, "filename": file.filename, "kind": file.kind,
            "sha256": file.sha256, "created_at": file.created_at.isoformat(),
            "current": current,
            "metadata": {k: v for k, v in metadata.items() if k not in {"inputs", "uploaded_by", "issued_by", "review", "scope"}},
            "leg_ids": list(metadata.get("scope", {file.leg_id: {}}))}


def guard_source(db, source_id):
    """Office edits and deletion cannot invalidate reserved operational goods."""
    lock(db)
    for row in db.query(Delivery).all():
        if any(a["shipment_id"] == source_id for a in active_allocations(data(row))):
            raise error(409, "delivery.source_locked")


def discard_all(db):
    for model in (DeliveryGrant, DeliveryFile, Delivery):
        db.query(model).delete(synchronize_session=False)
    db.flush()
