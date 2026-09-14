"""An indexed office work list; it never declares that freight has departed."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone

from sqlalchemy import String, and_, case, cast, false, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.dates import utc_timestamp
from app.core.messages import error
from app.models.dg_review import DgReview
from app.models.shipment import Shipment
from app.models.user import User, UserProfile
from app.schemas.history import ShipmentIn
from app.services import departments, dg_review
from app.services.settings_store import instance_settings

FILTERS = ("attention", "waiting", "today", "ready", "closed", "all")


def loading_date(values: dict) -> str | None:
    """Only an explicit calendar date, never the save time or a guessed deadline."""
    raw = str(values.get("loading_date") or "").strip()
    try:
        return date.fromisoformat(raw).isoformat() if len(raw) == 10 else None
    except ValueError:
        return None


def index_shipment(record: Shipment, payload: ShipmentIn) -> None:
    from app.services.documents import get_document, validate_document

    previous = record.work_fingerprint or ""
    fingerprint = dg_review.fingerprint(payload)
    issues = []
    lines = [line for line in payload.lines if line.get("include", True)]
    if not lines:
        issues.append("goods")
    elif any(line.get("status") == "error" or line.get("quantity_unconfirmed")
             or line.get("unconfirmed_weight_kg") is not None for line in lines):
        issues.append("goods_check")
    if not payload.documents:
        issues.append("documents")
    else:
        for key in payload.documents:
            definition = get_document(key)
            if definition is None:
                issues.append("documents")
                break
            document_errors, _ = validate_document(
                definition, payload.values, payload.lines, payload.dangerous_goods, payload.language)
            if document_errors:
                issues.append("document_fields")
                break
    record.work_status = "prepare" if issues or payload.draft else "ready" if payload.bundle else "documents"
    record.work_issues_json = json.dumps(issues)
    record.work_due_date = loading_date(payload.values)
    record.work_review_id = payload.dg_review_id or (payload.bundle.dg_review_id if payload.bundle else None)
    record.work_fingerprint = fingerprint
    if not record.work_version:
        record.work_owner_id = record.created_by_id
    if previous and previous != fingerprint:
        record.work_completed_at = None
    record.work_version = (record.work_version or 0) + 1


def backfill(conn) -> None:
    """Upgrade existing records once; the list itself reads only small columns."""
    from app.services.history import _loads

    with Session(bind=conn) as db:
        for record in db.query(Shipment).yield_per(25):
            snapshot, exported = _loads(record.snapshot_json), _loads(record.export_json)
            bundle = _loads(record.bundle_json)
            documents = bundle.get("documents") or []
            document = documents[0] if documents and isinstance(documents[0], dict) else {}
            values = exported.get("consignment") or snapshot.get("docValues") or document.get("values") or {}
            raw = {
                "modality": record.modality, "language": record.language,
                "profiles": exported.get("regulations") or bundle.get("profiles") or [], "values": values,
                "lines": (snapshot.get("result") or {}).get("lines") or document.get("lines") or [],
                "dangerous_goods": snapshot.get("dgEntries") or bundle.get("dangerous_goods") or document.get("dangerous_goods") or [],
                "documents": snapshot.get("selectedDocs") or [],
                "snapshot": snapshot, "draft": bool(record.is_draft),
                "bundle": bundle or None,
                "dg_review_id": bundle.get("dg_review_id"),
            }
            if bundle:
                raw["documents"] = [item.get("document_key") for item in bundle.get("documents", [])]
            try:
                index_shipment(record, ShipmentIn(**raw))
            except (ValueError, TypeError, KeyError, AttributeError):
                record.work_status = "prepare"
                record.work_issues_json = '["reopen"]'
                record.work_due_date = loading_date(values) if isinstance(values, dict) else None
                record.work_owner_id = record.created_by_id
                record.work_version = 1
        for review in db.query(DgReview).yield_per(25):
            saved = _loads(review.payload_json)
            values = saved.get("values") or {}
            try:
                review.work_draft_fingerprint = dg_review.fingerprint(ShipmentIn(**saved).model_copy(update={"bundle": None}))
            except (ValueError, TypeError):
                pass
            if isinstance(values, dict):
                review.work_due_date = loading_date(values)
                review.work_consignee = str(values.get("consignee_name") or "")[:255]
        db.flush()


def _name(user, profile):
    return func.coalesce(func.nullif(profile.display_name, ""),
                         func.nullif(func.trim(func.coalesce(profile.first_name, "") + " " +
                                               func.coalesce(profile.last_name, "")), ""), user.username, "")


def _source(db: Session, viewer: User):
    settings = instance_settings(db)
    owner, profile, release = aliased(User), aliased(UserProfile), aliased(DgReview)
    status = case(
        (and_(Shipment.has_dangerous_goods.is_(True), literal(settings.dg_review_enabled),
              or_(release.id.is_(None), release.status != "approved")), "review_required"),
        else_=Shipment.work_status)
    # A submitted copy replaces the matching private draft in the work list.
    # A changed draft has a different fingerprint and remains visible.
    submitted = select(DgReview.id).where(
        DgReview.created_by_id == viewer.id, DgReview.created_by == viewer.username,
        or_(DgReview.fingerprint == Shipment.work_fingerprint,
            DgReview.work_draft_fingerprint == Shipment.work_fingerprint),
        DgReview.work_completed_at.is_(None)).exists()
    private = and_(Shipment.is_draft.is_(True), Shipment.created_by_id == viewer.id, ~submitted)
    shared = and_(Shipment.is_draft.is_(False),
                  literal(True) if viewer.role in {"admin", "super_user", "dg_specialist"}
                  else Shipment.department_id == viewer.department_id)
    shipments = select(
        literal("shipment").label("kind"), cast(Shipment.id, String).label("id"),
        Shipment.reference.label("reference"), Shipment.modality.label("modality"),
        Shipment.consignor_name.label("consignor"), Shipment.consignee_name.label("consignee"),
        status.label("status"), Shipment.work_due_date.label("due_date"),
        Shipment.work_owner_id.label("owner_id"), _name(owner, profile).label("owner_name"),
        Shipment.work_completed_at.label("completed_at"), Shipment.work_version.label("version"),
        Shipment.work_issues_json.label("issues"), Shipment.updated_at.label("updated_at"),
        Shipment.is_draft.label("is_draft"), literal("").label("review_status"),
    ).outerjoin(owner, owner.id == Shipment.work_owner_id).outerjoin(
        profile, profile.user_id == owner.id).outerjoin(release, release.id == Shipment.work_review_id)
    shipments = shipments.where(or_(private, shared) if settings.history_enabled else false())

    submitter, person = aliased(User), aliased(UserProfile)
    own = and_(DgReview.created_by_id == viewer.id, DgReview.created_by == viewer.username)
    specialist = viewer.role == "dg_specialist"
    sees_pending = viewer.role in {"admin", "dg_specialist"}
    # Once the approved submission has become a kept shipment it has a single
    # row, with the shipment's assignment and office-completion controls.
    published = select(Shipment.id).where(
        Shipment.id == DgReview.shipment_id, Shipment.work_review_id == DgReview.id,
        Shipment.is_draft.is_(False)).exists()
    review_status = case((DgReview.status == "pending", "review" if specialist else "waiting"),
                         (DgReview.status == "changes_requested", "changes"), else_="approved")
    reviews = select(
        literal("review").label("kind"), DgReview.id.label("id"),
        DgReview.reference.label("reference"), DgReview.modality.label("modality"),
        literal("").label("consignor"), DgReview.work_consignee.label("consignee"),
        review_status.label("status"), DgReview.work_due_date.label("due_date"),
        DgReview.created_by_id.label("owner_id"), _name(submitter, person).label("owner_name"),
        DgReview.work_completed_at.label("completed_at"), literal(0).label("version"),
        literal("[]").label("issues"), DgReview.created_at.label("updated_at"),
        literal(False).label("is_draft"), DgReview.status.label("review_status"),
    ).outerjoin(submitter, submitter.id == DgReview.created_by_id).outerjoin(
        person, person.user_id == submitter.id).where(
            or_(own, DgReview.status == "pending" if sees_pending else false()),
            ~published if settings.history_enabled else literal(True))
    return shipments.union_all(reviews).subquery()


def listing(db: Session, viewer: User, *, day: date, bucket: str = "attention",
            q: str = "", mine: bool = False, page: int = 1, per_page: int = 20) -> dict:
    source = _source(db, viewer)
    c = source.c
    opened = c.completed_at.is_(None)
    actionable = c.status.in_(("prepare", "documents", "review_required", "review", "changes", "approved"))
    overdue = and_(c.due_date < day.isoformat(), c.status == "ready")
    filters = {
        "attention": and_(opened, or_(actionable, overdue)),
        "waiting": and_(opened, c.status == "waiting"),
        "today": and_(opened, c.due_date == day.isoformat()),
        "ready": and_(opened, c.status == "ready"),
        "closed": c.completed_at.isnot(None), "all": opened,
    }
    scope = []
    if mine:
        scope.append(or_(c.owner_id == viewer.id, c.status == "review"))
    if q.strip():
        scope.append(or_(*(func.lower(column).contains(q.strip().lower(), autoescape=True)
                           for column in (c.reference, c.consignor, c.consignee, c.owner_name))))
    counts = db.execute(select(*(func.coalesce(func.sum(case((condition, 1), else_=0)), 0).label(name)
                                 for name, condition in filters.items())).select_from(source).where(*scope)).mappings().one()
    priority = case((c.status == "changes", 0), (overdue, 1), (c.status == "review", 2),
                    (c.due_date == day.isoformat(), 3), else_=4)
    rows = db.execute(select(source).where(*scope, filters[bucket]).order_by(
        priority, c.due_date.is_(None), c.due_date, c.updated_at.desc(), c.kind, c.id
    ).offset((page - 1) * per_page).limit(per_page)).mappings()
    items = []
    for row in rows:
        item = dict(row)
        try:
            item["issues"] = json.loads(item["issues"])
        except (ValueError, TypeError):
            item["issues"] = ["reopen"]
        for key in ("updated_at", "completed_at"):
            if item[key] is not None:
                item[key] = utc_timestamp(item[key])
        item["overdue"] = bool(item["due_date"] and item["due_date"] < day.isoformat()
                               and item["completed_at"] is None)
        items.append(item)
    return {"items": items, "counts": dict(counts), "total": counts[bucket],
            "page": page, "per_page": per_page, "day": day.isoformat(),
            "history_enabled": instance_settings(db).history_enabled}


def people(db: Session, viewer: User, shipment: Shipment, q: str = "") -> list[dict]:
    if shipment.is_draft:
        return [{"id": viewer.id, "name": viewer.display_name or viewer.username}]
    query = db.query(User).filter(User.active.is_(True), or_(
        User.role.in_(("admin", "super_user", "dg_specialist")), User.department_id == shipment.department_id))
    if q:
        query = query.filter(func.lower(User.username).contains(q.lower(), autoescape=True))
    return [{"id": user.id, "name": user.display_name or user.username}
            for user in query.order_by(User.username).limit(100).all()]


def change(db: Session, viewer: User, record: Shipment, *, version: int,
           owner_id: int | None = None, completed: bool | None = None) -> Shipment:
    updates = {Shipment.work_version: version + 1, Shipment.updated_at: datetime.now(timezone.utc)}
    if owner_id is not None:
        owner = db.get(User, owner_id)
        if (not owner or not owner.active or not departments.may_see(record, owner)
                or (record.is_draft and owner.id != viewer.id)):
            raise error(422, "work.owner_invalid")
        updates[Shipment.work_owner_id] = owner.id
    if completed is not None:
        if completed:
            if record.is_draft or record.work_status != "ready":
                raise error(409, "work.not_ready")
            from app.schemas import DocumentBundleRequest
            from app.services.history import bundle_of
            bundle = bundle_of(record)
            if not bundle:
                raise error(409, "work.not_ready")
            dg_review.enforce_bundle(db, viewer, DocumentBundleRequest(**bundle), required=record.has_dangerous_goods)
        updates[Shipment.work_completed_at] = datetime.now(timezone.utc) if completed else None
    changed = db.query(Shipment).filter(Shipment.id == record.id, Shipment.work_version == version).update(
        updates, synchronize_session=False)
    if not changed:
        db.rollback()
        raise error(409, "work.changed")
    db.commit()
    db.refresh(record)
    return record
