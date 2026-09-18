"""Plan, assess and issue a temporary delivery without retaining cargo or files."""
import hashlib
import io
import zipfile
from datetime import timedelta
from typing import Literal

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.messages import error
from app.core.ratelimit import DOCUMENT_BUNDLE, limiter
from app.models.user import User
from app.schemas.deliveries import StrictModel, LegIn, DeliveryIn
from app.schemas.history import ShipmentIn
from app.services import deliveries as d
from app.services.delivery_documents import payload_for

router = APIRouter(prefix="/temporary-deliveries/v1", tags=["deliveries"])


class TemporaryIn(StrictModel):
    shipment: ShipmentIn
    leg: LegIn
    document_keys: list[str] = Field(min_length=1, max_length=30)
    language: Literal["nl", "en", "de", "fr"] = "en"
    reason: str = Field(default="", max_length=4000)
    review_token: str = Field(default="", max_length=4000)


def prepare(payload):
    source = payload.shipment
    export = {"goods": source.lines, "cargo": source.cargo.model_dump(mode="json") if source.cargo else None,
              "consignment": source.values, "dangerous_goods": source.dangerous_goods}
    part = payload.leg.model_dump(mode="json")
    part["status"] = "planned"
    if not all((part["origin"], part["destination"], part["carrier"], part["planned_start"])):
        raise error(422, "delivery.state")
    goods = d.source_goods(export)
    if not goods:
        raise error(422, "delivery.quantity")
    if len(goods) != sum(g.get("include", True) for g in source.lines):
        raise error(422, "delivery.quantity")
    value = {"legs": [part], "sources": {"1": {"reference": str(source.values.get("reference", "")), "export": export}},
             "allocations": [{"id": str(i), "shipment_id": 1, "goods_id": gid, "quantity": str(g.get("quantity", "")), "leg_ids": [part["id"]]}
                             for i, (gid, g) in enumerate(goods.items())], "events": []}
    if len(d.canonical(value).encode()) > d.MAX_RECORD:
        raise error(413, "delivery.too_large")
    try:
        validated = DeliveryIn(name="temporary", legs=[payload.leg], allocations=value["allocations"])
        value["allocations"] = [a.model_dump(mode="json") for a in validated.allocations]
    except ValueError as exc:
        raise error(422, "delivery.quantity") from exc
    d.validate_quantities(value)
    d.validate_cargo(value, part)
    d.verify_sources(value, part)
    result = d.assessment(value, part, payload.language)
    if result["blocked"]:
        raise error(409, "delivery.blocked")
    return value, part, result


def binding(payload, result):
    return d.digest({"payload": payload.model_dump(mode="json", exclude={"review_token", "reason"}), "editions": result["editions"]})


def may_review(db, user, part, result):
    roles, modes = d.tasks(db, user)
    return "assessor" in roles and part["mode"] in modes and (not result["has_dg"] or user.role == "dg_specialist")


@router.post("/assessment")
def assessment(payload: TemporaryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d.planner(db, user)
    _, part, result = prepare(payload)
    return {**result, "can_review": may_review(db, user, part, result)}


@router.post("/review")
def review(payload: TemporaryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    d.planner(db, user)
    _, part, result = prepare(payload)
    if not may_review(db, user, part, result):
        raise error(403, "delivery.permission")
    if len(payload.reason.strip()) < 10:
        raise error(422, "delivery.review")
    claims = {"purpose": "temporary-delivery-review", "actor": user.id, "binding": binding(payload, result),
              "reason": payload.reason, "at": d.stamp(), "exp": d.now() + timedelta(minutes=30)}
    # No session subject or password claim: this token cannot authenticate.
    return {"token": jwt.encode(claims, get_settings().app_secret_key, algorithm="HS256")}


@router.post("/documents")
@limiter.limit(DOCUMENT_BUNDLE)
def documents(request: Request, payload: TemporaryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.api.routes.documents import _render_export, _card_link_base
    from app.services.documents import get_document, get_registry, validate_document, brand
    from app.services.cargo_documents import validate_for_document
    from fastapi import HTTPException
    d.planner(db, user)
    value, part, result = prepare(payload)
    approved = None
    if result["manual_required"]:
        try:
            approved = jwt.decode(payload.review_token, get_settings().app_secret_key, algorithms=["HS256"], options={"require": ["exp", "purpose", "actor", "binding"]})
        except jwt.PyJWTError as exc:
            raise error(409, "delivery.review") from exc
        if (approved["purpose"] != "temporary-delivery-review" or approved["actor"] != user.id
                or approved["binding"] != binding(payload, result) or not may_review(db, user, part, result)):
            raise error(409, "delivery.review")
    modality = next((m for m in get_registry()["modalities"] if m["key"] == part["mode"]), {})
    prepared = []
    for key in dict.fromkeys(payload.document_keys):
        document = get_document(key)
        if document is None or key not in modality.get("documents", []):
            raise error(422, "delivery.document")
        inputs = payload_for(value, part, 1, key, payload.language)
        validate_for_document(inputs.cargo, inputs.lines, key, inputs.values)
        errors, warnings = validate_document(document, inputs.values, inputs.lines, inputs.dangerous_goods, payload.language)
        if errors:
            raise HTTPException(422, detail={"errors": errors})
        prepared.append((document, inputs, warnings))
    output = io.BytesIO()
    metadata = []
    brand.use(db)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for document, inputs, warnings in prepared:
            path = _render_export(document, inputs, None, _card_link_base(db), draft=False)
            try:
                content = path.read_bytes()
                name = f"{inputs.document_key}{path.suffix}"
                archive.writestr(name, content)
                metadata.append({"path": name, "sha256": hashlib.sha256(content).hexdigest(), "inputs": inputs.model_dump(mode="json"), "warnings": warnings})
            finally:
                path.unlink(missing_ok=True)
        archive.writestr("delivery.json", d.canonical({"format": "emcargo.temporary-delivery", "format_version": "1.0",
            "issued_at": d.stamp(), "issued_by": user.id, "planning": part, "assessment": result,
            "review": {k: v for k, v in approved.items() if k != "exp"} if approved else None, "files": metadata}))
    return Response(output.getvalue(), media_type="application/zip", headers={
        "Content-Disposition": 'attachment; filename="temporary-delivery.zip"', "Cache-Control": "private, no-store"})
