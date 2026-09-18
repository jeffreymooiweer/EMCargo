"""Versioned delivery API. Assignment filtering is enforced before serialization."""
import io
import json
import secrets
import zipfile
from datetime import date, timedelta
from uuid import uuid4
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_user, require_history, require_manager
from app.core.messages import error
from app.core.ratelimit import limiter, DOCUMENT_BUNDLE_MAIL
from app.models.delivery import Delivery, DeliveryAccount, DeliveryFile, DeliveryGrant
from app.models.shipment import Shipment
from app.models.user import User
from app.schemas.deliveries import DeliveryIn, ActionIn, ReviewIn, EventIn, GrantIn, AccountIn, UnloadingIn
from app.services import deliveries as d, delivery_documents as documents, departments

router = APIRouter(prefix="/deliveries/v1", tags=["deliveries"], dependencies=[Depends(require_history)])


@router.get("")
def listing(q: str = Query(default="", max_length=120), page: int = Query(default=1, ge=1),
            user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    records = db.query(Delivery).filter(Delivery.name.ilike(f"%{q}%")).order_by(Delivery.updated_at.desc()).all()
    visible = [r for r in records if d.internal(db, user, r) or d.grants(db, user, r)]
    return {"items": [{k: v for k, v in d.view(db, user, r).items() if k in {"id", "name", "version", "status", "department_id", "can_plan"}} for r in visible[(page-1)*25:page*25]],
            "total": len(visible), "page": page, "can_plan": user.role not in d.LIMITED_ROLES and "planner" in d.tasks(db, user)[0]}


@router.get("/sources/{shipment_id}")
def source(shipment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d.planner(db, user)
    row = db.get(Shipment, shipment_id)
    if not row or row.is_draft or not departments.may_see(row, user):
        raise error(404, "delivery.source")
    export = json.loads(row.export_json)
    from app.services.delivery_cargo import roots, chosen
    groups = roots(export)
    occupied = {uid for record in db.query(Delivery).all() for value in [d.data(record)]
                if not value.get("followup") for a in d.active_allocations(value)
                if a["shipment_id"] == shipment_id for uid in chosen(a, groups)}
    from app.services.delivery_routing import balances as distribution_balances
    from app.services.shipment_routing import legacy
    return {"routing": legacy(export).model_dump(mode="json"), "distributions": distribution_balances(db, shipment_id, export), "id": row.id, "reference": row.reference, "department_id": row.department_id,
            "goods": [{**g, "delivery_goods_id": gid} for gid, g in d.source_goods(export).items()],
            "packing_units": [{**group, "goods": {gid: str(qty) for gid, qty in group["goods"].items()}, "available": uid not in occupied} for uid, group in groups.items()],
            "consignment": export.get("consignment", {})}


@router.get("/sources/{shipment_id}/balances")
def balances(shipment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.delivery_inventory import balances as calculate
    row = db.get(Shipment, shipment_id)
    if not row or row.is_draft or d.execution_only(db, user) or not departments.may_see(row, user):
        raise error(404, "delivery.source")
    return calculate(db, shipment_id, json.loads(row.export_json), user)


@router.get("/operations")
def operations(date_from: date | None = None, date_to: date | None = None,
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.delivery_inventory import operations as calculate
    if d.execution_only(db, user):
        raise error(403, "delivery.permission")
    return calculate(db, user, date_from, date_to)


@router.post("")
def create(payload: DeliveryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return d.create(db, user, payload)


@router.post("/import")
async def import_delivery(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.delivery_import import restore
    d.planner(db, user)
    content = await file.read(d.MAX_RECORD + 1)
    return restore(db, user, content)


@router.get("/accounts/{user_id}")
def account(user_id: int, manager: User = Depends(require_manager), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise error(404, "delivery.not_found")
    roles, modes = d.tasks(db, target)
    return {"roles": sorted(roles), "modes": sorted(modes)}


@router.put("/accounts/{user_id}")
def account_update(user_id: int, payload: AccountIn, manager: User = Depends(require_manager), db: Session = Depends(get_db)):
    from app.api.routes.users import _ensure_manageable
    target = db.get(User, user_id)
    if target is None:
        raise error(404, "delivery.not_found")
    _ensure_manageable(manager, target)
    if "assessor" in payload.roles and manager.role != "admin":
        raise error(403, "delivery.permission")
    if target.role in d.LIMITED_ROLES and not set(payload.roles) <= {"operator", "recipient"}:
        raise error(403, "delivery.permission")
    row = db.get(DeliveryAccount, user_id) or DeliveryAccount(user_id=user_id)
    row.roles_json, row.modes_json = json.dumps(payload.roles), json.dumps(payload.modes)
    db.add(row)
    db.commit()
    from app.services import audit
    audit.record(db, "delivery.access", actor=manager, target=("user", user_id), summary="task_permissions")
    return payload


@router.post("/from-trip/{trip_id}")
def from_trip(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.routes.trips import _record
    trip = _record(trip_id, db, user)
    result = d.create(db, user, DeliveryIn(name=trip.name or f"#{trip_id}"))
    record = d.get(db, user, result["id"], write=True)
    value = d.data(record)
    value["legacy_trip_id"] = trip.id
    value["legacy_consignments"] = json.loads(trip.consignments_json)
    return d.save(db, record, value, user, "converted_from_trip")


@router.get("/{delivery_id}")
def detail(delivery_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return d.view(db, user, d.get(db, user, delivery_id))


@router.post("/{delivery_id}/legs/{leg_id}/unloading")
def unloading(delivery_id: str, leg_id: str, payload: UnloadingIn,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.delivery_unloading import register
    return register(db, user, d.get(db, user, delivery_id, write=True), leg_id, payload)


@router.put("/{delivery_id}")
def edit(delivery_id: str, payload: DeliveryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id, write=True)
    if not d.internal(db, user, record):
        raise error(403, "delivery.permission")
    return d.edit(db, user, record, payload)


@router.post("/{delivery_id}/legs/{leg_id}/action")
def action(delivery_id: str, leg_id: str, payload: ActionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id, write=True)
    if not d.internal(db, user, record):
        raise error(403, "delivery.permission")
    return d.action(db, user, record, leg_id, payload)


@router.get("/{delivery_id}/legs/{leg_id}/assessment")
def assessment(delivery_id: str, leg_id: str, language: str = Query(default="en", pattern="^(nl|en|de|fr)$"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id)
    if not d.internal(db, user, record):
        raise error(403, "delivery.permission")
    value = d.data(record)
    return d.assessment(value, d.leg(value, leg_id), language)


@router.post("/{delivery_id}/legs/{leg_id}/review")
def review(delivery_id: str, leg_id: str, payload: ReviewIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return d.review(db, user, d.get(db, user, delivery_id, write=True), leg_id, payload)


@router.post("/{delivery_id}/legs/{leg_id}/events")
def event(delivery_id: str, leg_id: str, payload: EventIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return d.event(db, user, d.get(db, user, delivery_id, write=True), leg_id, payload)


class IssueIn(BaseModel):
    version: int = Field(ge=1)
    shipment_id: int = Field(gt=0)
    allocation_ids: list[str] = Field(default_factory=list, max_length=2000)
    document_key: str = Field(max_length=80)
    language: str = Field(default="nl", pattern="^(nl|en|de|fr)$")
    leg_ids: list[str] = Field(default_factory=list, max_length=100)
    contract_reference: str = Field(default="", max_length=120)


@router.post("/{delivery_id}/legs/{leg_id}/documents")
def issue(delivery_id: str, leg_id: str, payload: IssueIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id, write=True)
    if not d.internal(db, user, record):
        raise error(403, "delivery.permission")
    d.check_version(record, payload.version)
    documents.issue(db, user, record, leg_id, payload.shipment_id, payload.document_key, payload.language, payload.leg_ids, payload.contract_reference.strip(), payload.allocation_ids)
    return d.save(db, record, d.data(record), user, "document_issued")


@router.post("/{delivery_id}/legs/{leg_id}/files")
async def upload(delivery_id: str, leg_id: str, version: int = Form(...), kind: str = Form(...),
                 shipment_ids: str = Form(...), file: UploadFile = File(...), allocation_ids: str = Form("[]"),
                 user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id, write=True)
    d.check_version(record, version)
    value = d.data(record)
    part = d.leg(value, leg_id)
    try:
        sids = json.loads(shipment_ids)
        if not isinstance(sids, list) or not sids or any(type(s) is not int for s in sids):
            raise ValueError()
    except (ValueError, TypeError):
        raise error(422, "delivery.document")
    if not set(sids) <= {a["shipment_id"] for a in d.selected(value, leg_id)}:
        raise error(422, "delivery.document")
    try:
        aids = json.loads(allocation_ids)
        if not isinstance(aids, list) or any(not isinstance(a, str) for a in aids):
            raise ValueError()
    except (ValueError, TypeError):
        raise error(422, "delivery.document")
    selected_ids = {a["id"] for a in d.selected(value, leg_id) if a["shipment_id"] in sids}
    aids = set(aids) if aids else selected_ids
    if not aids or not aids <= selected_ids:
        raise error(422, "delivery.document")
    if kind == "external":
        d.planner(db, user)
        if not d.internal(db, user, record) or part["status"] not in {"draft", "planned"}:
            raise error(409, "delivery.state")
    elif kind == "proof":
        allowed = d.allowed_allocations(db, user, record, value, leg_id, "recipient") | d.allowed_allocations(db, user, record, value, leg_id, "operator")
        if not aids <= allowed or part["status"] not in {"released", "in_progress", "completed"}:
            raise error(403, "delivery.permission")
    else:
        raise error(422, "delivery.document")
    content = await file.read(documents.MAX_FILE_BYTES + 1)
    content, media, name = documents.validate_upload(content, file.filename or "attachment")
    documents.store(db, record, part, sids, content, name, media, kind, {"uploaded_by": user.id, "uploaded_at": d.stamp()}, sorted(aids))
    return d.save(db, record, value, user, "file_uploaded")


def visible_file(db, user, record, file_id):
    visible = {f["id"] for f in d.view(db, user, record)["files"]}
    file = db.get(DeliveryFile, file_id)
    if file_id not in visible or not file or file.delivery_id != record.id:
        raise error(404, "delivery.not_found")
    return file


class FileSelection(BaseModel):
    version: int = Field(ge=1)
    file_ids: list[str] = Field(min_length=1, max_length=100)


class FileMail(FileSelection):
    to: list[EmailStr] = Field(min_length=1, max_length=10)
    message: str = Field(default="", max_length=4000)
    language: str = Field(default="nl", pattern="^(nl|en|de|fr)$")


def selected_files(db, user, record, payload):
    d.check_version(record, payload.version)
    visible = {f["id"]: f for f in d.view(db, user, record)["files"]}
    if len(set(payload.file_ids)) != len(payload.file_ids) or any(
        fid not in visible or not visible[fid]["current"] for fid in payload.file_ids
    ):
        raise error(409, "delivery.document")
    return [visible_file(db, user, record, fid) for fid in payload.file_ids]


@router.post("/{delivery_id}/bundle")
def file_bundle(delivery_id: str, payload: FileSelection, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id)
    files = selected_files(db, user, record, payload)
    return Response(documents.bundle(files), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="delivery-documents.zip"', "Cache-Control": "private, no-store"})


@router.post("/{delivery_id}/bundle/mail")
@limiter.limit(DOCUMENT_BUNDLE_MAIL)
def file_mail(delivery_id: str, payload: FileMail, request: Request,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services import audit, mail, mail_templates
    from app.services.settings_store import instance_settings
    d.planner(db, user)
    record = d.get(db, user, delivery_id, write=True)
    if not d.internal(db, user, record):
        raise error(403, "delivery.permission")
    content = documents.bundle(selected_files(db, user, record, payload))
    settings = instance_settings(db)
    if not mail.is_configured(settings):
        raise error(409, "delivery.mail")
    message = mail_templates.documents_message(payload.language, user.username, record.name, payload.message)
    try:
        mail.send(settings, [str(address) for address in payload.to], message.subject, message.text,
                  [("delivery-documents.zip", content, "application/zip")], html=message.html)
    except mail.MailError as exc:
        raise error(409, "delivery.mail") from exc
    audit.record(db, "documents.mailed", actor=user, target=("delivery", record.id),
                 summary=f"{len(payload.file_ids)} files to {len(payload.to)} recipients", request=request)
    return {"ok": True}


@router.get("/{delivery_id}/files/{file_id}")
def download(delivery_id: str, file_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    file = visible_file(db, user, d.get(db, user, delivery_id), file_id)
    from urllib.parse import quote
    return Response(file.content, media_type=file.media_type,
                    headers={"Content-Disposition": "attachment; filename*=UTF-8''" + quote(file.filename),
                             "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@router.get("/{delivery_id}/export")
def export(delivery_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = d.get(db, user, delivery_id)
    value = d.view(db, user, record)
    output = io.BytesIO()
    if d.internal(db, user, record):
        for metadata in value["files"]:
            metadata["metadata"] = json.loads(db.get(DeliveryFile, metadata["id"]).metadata_json)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("delivery.json", d.canonical({"format": "emcargo.delivery", "format_version": "2.0", "delivery": value}))
        for metadata in value["files"]:
            file = visible_file(db, user, record, metadata["id"])
            archive.writestr(f"documents/{file.id}/{file.filename}", file.content)
    return Response(output.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="delivery-{record.id}.zip"', "Cache-Control": "private, no-store"})


@router.get("/{delivery_id}/grants")
def grants(delivery_id: str, manager: User = Depends(require_manager), db: Session = Depends(get_db)):
    record = d.get(db, manager, delivery_id)
    return [{"id": g.id, "user_id": g.user_id, "leg_id": g.leg_id, "role": g.role,
             "shipment_ids": json.loads(g.shipment_ids_json), "allocation_ids": json.loads(g.allocation_ids_json or "[]"), "expires_at": g.expires_at,
             "revoked": g.revoked_at is not None} for g in db.query(DeliveryGrant).filter_by(delivery_id=record.id).all()]


@router.post("/{delivery_id}/grants")
def grant(delivery_id: str, payload: GrantIn, request: Request, manager: User = Depends(require_manager), db: Session = Depends(get_db)):
    from app.core.security import hash_password
    from app.services import mail, mail_templates, password_reset
    from app.services.settings_store import instance_settings
    from app.api.routes.auth import _public_base_url
    from pydantic import TypeAdapter
    record = d.get(db, manager, delivery_id, write=True)
    value = d.data(record)
    part = d.leg(value, payload.leg_id)
    if not payload.expires_at.tzinfo or payload.expires_at <= d.now() or payload.expires_at > d.now() + timedelta(days=90):
        raise error(422, "delivery.time")
    selected = d.selected(value, part["id"])
    ids = set(payload.allocation_ids)
    if not ids:
        # Legacy callers may select a whole shipment only when it has no
        # address distributions; v3 access must be explicit.
        if any(value["sources"][str(s)]["export"].get("routing") for s in payload.shipment_ids if str(s) in value["sources"]):
            raise error(422, "delivery.source")
        ids = {a["id"] for a in selected if a["shipment_id"] in payload.shipment_ids}
    if not ids or not ids <= {a["id"] for a in selected}:
        raise error(422, "delivery.source")
    if payload.role == "recipient" and any(a["leg_ids"][-1] != part["id"] for a in selected if a["id"] in ids):
        raise error(422, "delivery.source")
    shipment_ids = sorted({a["shipment_id"] for a in selected if a["id"] in ids})
    current = instance_settings(db)
    target = db.get(User, payload.user_id) if payload.user_id else None
    new_account = False
    if not payload.user_id:
        try:
            email = str(TypeAdapter(EmailStr).validate_python(payload.email))
        except ValueError:
            raise error(422, "delivery.invite")
        if not mail.is_configured(current):
            raise error(409, "delivery.invite")
        target = db.query(User).filter(User.email == email).first()
        if target is None:
            target = User(username="external-" + secrets.token_hex(8), email=email,
                          password_hash=hash_password(secrets.token_urlsafe(32)), role="external", active=True)
            db.add(target)
            db.flush()
            new_account = True
    if not target or not target.active:
        raise error(404, "delivery.not_found")
    expires_at = payload.expires_at
    if part.get("completed_at"):
        from datetime import datetime
        expires_at = min(expires_at, datetime.fromisoformat(part["completed_at"]) + timedelta(days=7))
        if expires_at <= d.now():
            raise error(422, "delivery.time")
    row = DeliveryGrant(id=str(uuid4()), delivery_id=record.id, user_id=target.id,
                        leg_id=part["id"], role=payload.role, shipment_ids_json=json.dumps(shipment_ids), allocation_ids_json=json.dumps(sorted(ids)), expires_at=expires_at)
    db.add(row)
    db.commit()
    if new_account or (not payload.user_id and target.role == "external"):
        token = password_reset.issue(db, target, ttl_minutes=password_reset.INVITE_TTL_MINUTES)
        link = password_reset.link_for(_public_base_url(request, current), token)
        message = mail_templates.invite_message("nl", target.username, link, 7)
        try:
            mail.send(current, target.email, message.subject, message.text, html=message.html)
        except mail.MailError as exc:
            row.revoked_at = d.now()
            db.commit()
            raise error(409, "delivery.invite") from exc
    from app.services import audit
    audit.record(db, "delivery.access", actor=manager, target=("delivery", record.id), summary="assigned")
    return {"id": row.id, "user_id": target.id, "invited": new_account}


@router.delete("/{delivery_id}/grants/{grant_id}")
def revoke(delivery_id: str, grant_id: str, manager: User = Depends(require_manager), db: Session = Depends(get_db)):
    d.get(db, manager, delivery_id, write=True)
    row = db.get(DeliveryGrant, grant_id)
    if not row or row.delivery_id != delivery_id:
        raise error(404, "delivery.not_found")
    row.revoked_at = d.now()
    db.commit()
    from app.services import audit
    audit.record(db, "delivery.access", actor=manager, target=("delivery", delivery_id), summary="revoked")
    return {"ok": True}
