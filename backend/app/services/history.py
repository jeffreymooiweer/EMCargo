"""The shipment history: keeping, listing and letting go.

Everything else in EMCargo forgets a shipment the moment its papers are
downloaded. This module is the one place that remembers, and it does so only
while an administrator of the organisation application has *Keep shipments*
switched on — the routes that call it answer 404 otherwise, and
:func:`adopt_kept_data` at start-up makes sure a database cannot hold
shipments the running application refuses to acknowledge.

**Switching the history off destroys data, and says so first.** The settings
route refuses to switch it off while shipments or trips are in the table; the
administrator has them deleted first, on the screen, after a confirmation
that names the counts. Nothing is deleted by a switch alone; a table kept
while the interface claims it does not exist would be the one outcome worse
than either choice.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, defer, joinedload

from app.core.dates import utc_filter_bound, utc_timestamp
from app.models.shipment import Shipment
from app.models.user import Department, User
from app.schemas.history import ShipmentDetail, ShipmentIn, ShipmentSummary
from app.services import departments
from app.services.documents.shipment_export import build_shipment_export

logger = logging.getLogger(__name__)

#: What one kept shipment may weigh, all three documents together. A
#: signature is tens of kilobytes; a large consignment's bundle a few hundred.
#: Four megabytes is not a shipment.
MAX_RECORD_BYTES = 4 * 1024 * 1024

PER_PAGE_MAX = 100


class RecordTooLarge(ValueError):
    """More than :data:`MAX_RECORD_BYTES` of snapshot, bundle and export."""


# --- the switch --------------------------------------------------------------


def count(db: Session) -> int:
    """How many shipments are kept. Drafts are entry in progress, not a
    record of a consignment, so they are not counted as one — but they are
    rows all the same, and :func:`discard_kept` removes them too."""
    return int(db.query(func.count(Shipment.id))
               .filter(Shipment.is_draft.is_(False)).scalar() or 0)


def kept_counts(db: Session) -> dict[str, int]:
    """What switching the history off would destroy: the shipments and the
    trips. The address book, the articles and the adviser's reports stay
    where they are — they are not a record of any consignment."""
    from app.services import trips

    return {"shipments": count(db), "trips": trips.count(db)}


def discard_kept(db: Session) -> dict[str, int]:
    """Delete every kept shipment and trip. The administrator's deliberate
    act, after a confirmation that named these counts."""
    from app.services import trips

    counts = kept_counts(db)
    db.query(Shipment).delete()
    db.commit()
    trips.discard_all(db)
    logger.warning("Shipment history emptied on the administrator's request: "
                   "%s kept shipment(s) and %s kept trip(s) deleted",
                   counts["shipments"], counts["trips"])
    return counts


def adopt_kept_data(db: Session) -> bool:
    """At start-up: a database that holds kept shipments or trips while the
    setting says off gets the setting switched on, never the data hidden.

    That is what an upgrade from the deploy-time variable looks like — the
    variable was the starting value and is still read as one, but an
    installation that dropped it from its environment must not wake up with
    a table the interface claims does not exist. Returns whether it acted.
    """
    from app.services.settings_store import instance_settings, save_instance_settings

    current = instance_settings(db)
    if current.history_enabled:
        return False
    counts = kept_counts(db)
    if not counts["shipments"] and not counts["trips"]:
        return False
    save_instance_settings(db, current.model_copy(update={"history_enabled": True}))
    logger.warning("Shipment history switched on: the database holds %s kept "
                   "shipment(s) and %s kept trip(s) that the setting did not cover. "
                   "An administrator switches it off under Settings, Administration, "
                   "after deleting them there.", counts["shipments"], counts["trips"])
    return True


# --- keeping -----------------------------------------------------------------


def _index(record: Shipment, export: dict[str, Any], payload: ShipmentIn) -> None:
    consignment = export.get("consignment") or {}
    # The wizard's field is shipment_reference; "reference" is read as well for
    # exports written by hand or by an older reader. Until v1.176.0 only the
    # latter was read, so every kept shipment listed as "(no reference)".
    record.reference = str(consignment.get("shipment_reference")
                           or consignment.get("reference") or "")[:120]
    record.consignor_name = str(consignment.get("consignor_name") or "")[:255]
    record.consignee_name = str(consignment.get("consignee_name") or "")[:255]
    record.modality = (payload.modality or "")[:16]
    record.language = (payload.language or "nl")[:8]
    record.regulations = ",".join(export.get("regulations") or [])[:64]
    record.goods_count = sum(1 for line in payload.lines if line.get("include", True))
    record.has_dangerous_goods = bool(payload.dangerous_goods)


def keep(db: Session, user: User, payload: ShipmentIn,
         existing: Shipment | None = None, *, commit: bool = True) -> Shipment:
    """Keep a shipment — a new row, or the same row brought up to date."""
    export = build_shipment_export(
        payload.values, payload.lines, payload.dangerous_goods,
        language=payload.language, profiles=payload.profiles,
        modality=payload.modality or None, documents=payload.documents or None)
    snapshot_json = json.dumps(payload.snapshot, ensure_ascii=False)
    bundle_json = (json.dumps(payload.bundle.model_dump(), ensure_ascii=False)
                   if payload.bundle and payload.bundle.documents else None)
    export_json = json.dumps(export, ensure_ascii=False)
    size = len(snapshot_json) + len(bundle_json or "") + len(export_json)
    if size > MAX_RECORD_BYTES:
        raise RecordTooLarge(
            f"The shipment is {size / 1024 / 1024:.1f} MB, more than the "
            f"{MAX_RECORD_BYTES // 1024 // 1024} MB one kept shipment may be.")

    # A private draft is not yet shared with any department. Its first
    # publication uses the author's current department, even after a move;
    # once kept, a shipment retains that department through later edits.
    record = existing or Shipment(created_by_id=user.id if user.id else None,
                                  department_id=getattr(user, "department_id", None))
    if existing is not None and existing.is_draft and not payload.draft:
        record.department_id = getattr(user, "department_id", None)
    _index(record, export, payload)
    # Saving the same row without the draft flag is what turns entry in
    # progress into a kept shipment; there is no separate act.
    record.is_draft = bool(payload.draft)
    record.snapshot_json = snapshot_json
    record.bundle_json = bundle_json
    record.export_json = export_json
    from app.services.work_queue import index_shipment
    index_shipment(record, payload)
    if existing is None:
        db.add(record)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(record)
    return record


def forget(db: Session, record: Shipment) -> None:
    db.delete(record)
    db.commit()


def discard_drafts(db: Session) -> int:
    """Delete every draft. Entry in progress is not a kept shipment, so it
    does not stand in the way of switching the history off — but it is a row
    all the same, and an installation that says it keeps nothing must not be
    holding somebody's half-typed consignment."""
    gone = int(db.query(func.count(Shipment.id))
               .filter(Shipment.is_draft.is_(True)).scalar() or 0)
    if gone:
        db.query(Shipment).filter(Shipment.is_draft.is_(True)).delete()
        db.commit()
        logger.info("Shipment history switched off: %s draft(s) discarded", gone)
    return gone


def running_draft(db: Session, user: User) -> Shipment | None:
    """The draft this user was last working on, if there is one.

    Only their own: a draft is unfinished entry, not a record anybody else
    has business reading, so the department rules that open a kept shipment
    to colleagues deliberately do not apply here.
    """
    if not getattr(user, "id", None):
        return None
    return (db.query(Shipment)
            .filter(Shipment.is_draft.is_(True), Shipment.created_by_id == user.id)
            .order_by(Shipment.updated_at.desc(), Shipment.id.desc())
            .first())


# --- reading -----------------------------------------------------------------


def _loads(text: str | None) -> dict[str, Any]:
    try:
        value = json.loads(text or "{}")
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def summary(record: Shipment) -> ShipmentSummary:
    return ShipmentSummary(
        id=record.id,
        reference=record.reference,
        modality=record.modality,
        language=record.language,
        regulations=[r for r in (record.regulations or "").split(",") if r],
        consignor_name=record.consignor_name,
        consignee_name=record.consignee_name,
        goods_count=record.goods_count,
        has_dangerous_goods=record.has_dangerous_goods,
        has_documents=bool(record.has_documents),
        is_draft=bool(record.is_draft),
        created_by=record.creator.username if record.creator else "",
        department_id=record.department_id,
        department=record.department.name if record.department else "",
        created_at=utc_timestamp(record.created_at),
        updated_at=utc_timestamp(record.updated_at),
    )


def detail(record: Shipment) -> ShipmentDetail:
    return ShipmentDetail(
        **summary(record).model_dump(),
        snapshot=_loads(record.snapshot_json),
        export=_loads(record.export_json),
    )


def bundle_of(record: Shipment) -> dict[str, Any] | None:
    return _loads(record.bundle_json) if record.bundle_json else None


def search(db: Session, viewer: User, q: str = "", modality: str = "",
           date_from: datetime | None = None, date_to: datetime | None = None,
           page: int = 1, per_page: int = 25,
           department: str = "") -> tuple[list[Shipment], int]:
    """The page of shipments ``viewer`` may see that match the filters,
    newest first, and the total across all pages."""
    # A draft is entry somebody is still doing; the shipments page lists what
    # was finished, and the draft's own author reaches it from the wizard.
    query = departments.visible_to(
        db.query(Shipment).filter(Shipment.is_draft.is_(False)), viewer, department)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        query = query.filter(or_(Shipment.reference.ilike(like),
                                 Shipment.consignor_name.ilike(like),
                                 Shipment.consignee_name.ilike(like)))
    if modality:
        query = query.filter(Shipment.modality == modality)
    if date_from:
        query = query.filter(Shipment.created_at >= utc_filter_bound(date_from))
    if date_to:
        query = query.filter(Shipment.created_at <= utc_filter_bound(date_to))
    total = int(query.with_entities(func.count(Shipment.id)).scalar() or 0)
    per_page = max(1, min(int(per_page), PER_PAGE_MAX))
    page = max(1, int(page))
    # Large saved documents stay on detail routes. Names are joined once
    # rather than fetched again for every author and department in the page.
    rows = (query.options(
                defer(Shipment.snapshot_json), defer(Shipment.export_json),
                defer(Shipment.bundle_json),
                joinedload(Shipment.creator).load_only(User.username),
                joinedload(Shipment.department).load_only(Department.name))
            .order_by(Shipment.created_at.desc(), Shipment.id.desc())
            .offset((page - 1) * per_page).limit(per_page).all())
    return rows, total
