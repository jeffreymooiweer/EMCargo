"""Approval is bound to the actual document inputs, never a client status flag."""
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from app.core.messages import error
from app.models.dg_review import DgReview
from app.models.user import User
from app.schemas import DocumentBundleRequest, DocumentExportRequest
from app.schemas.history import ShipmentIn
# Compatibility export for integrations configuring the legacy review workspace.
from app.services.settings_store import instance_settings as instance_settings

__all__ = ["instance_settings"]

MAX_BYTES = 3 * 1024 * 1024


def canonical(value) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise error(422, "review.inconsistent") from exc


def document_data(payload: DocumentExportRequest, signature: str | None = None) -> dict:
    data = payload.model_dump(exclude={"dg_review_id"})
    data["signature_image"] = signature or payload.signature_image or None
    if data.get("cargo") is not None:
        data["cargo"].pop("revision", None)
    else:
        data.pop("cargo", None)
    data["dangerous_goods"] = data.get("dangerous_goods") or []
    return data


def bundle_data(payload: DocumentBundleRequest) -> dict:
    data = payload.model_dump(exclude={"dg_review_id", "documents"})
    if data.get("cargo") is not None:
        data["cargo"].pop("revision", None)
    else:
        data.pop("cargo", None)
    data["dangerous_goods"] = data.get("dangerous_goods") or []
    data["signature_image"] = payload.signature_image or None
    data["documents"] = [document_data(doc, payload.signature_image) for doc in payload.documents]
    return data


def shipment_data(payload: ShipmentIn) -> dict:
    data = payload.model_dump(exclude={"snapshot", "draft", "dg_review_id", "bundle", "expected_cargo_revision"})
    if data.get("cargo") is not None:
        data["cargo"].pop("revision", None)
    else:
        data.pop("cargo", None)
    data["dangerous_goods"] = data.get("dangerous_goods") or []
    data["bundle"] = bundle_data(payload.bundle) if payload.bundle else None
    return data


def fingerprint(payload: ShipmentIn) -> str:
    return hashlib.sha256(canonical(shipment_data(payload)).encode()).hexdigest()


def has_dg(payload) -> bool:
    # The declaration can travel at bundle or document level. Neither may be
    # dropped to bypass the other. Calculated line markers count as well.
    if payload.dangerous_goods:
        return True
    if any(line.get("dangerous_goods") or line.get("un_number") or line.get("is_dangerous")
           for line in getattr(payload, "lines", [])):
        return True
    bundle = getattr(payload, "bundle", None)
    if bundle is not None and has_dg(bundle):
        return True
    return any(has_dg(doc) for doc in getattr(payload, "documents", []) if not isinstance(doc, str))


def owns(record: DgReview, user: User) -> bool:
    return record.created_by_id == user.id and record.created_by == user.username


def get_visible(db: Session, review_id: str, user: User) -> DgReview:
    record = db.get(DgReview, review_id)
    if record is None or not (owns(record, user) or user.role in {"admin", "dg_specialist"}):
        raise error(404, "review.not_found")
    return record


def approved(db: Session, review_id: str | None, user: User) -> DgReview:
    if not review_id:
        raise error(409, "review.required")
    record = db.get(DgReview, review_id)
    # Approval of an identical document can be used by colleagues who may
    # access the kept shipment. It confers no ability to inspect the queue.
    creator = db.get(User, record.created_by_id) if record and record.created_by_id else None
    visible = record and (owns(record, user) or user.role in {"admin", "dg_specialist", "super_user"}
                          or (creator and creator.username == record.created_by
                              and creator.department_id == user.department_id))
    if not visible or record.status != "approved":
        raise error(409, "review.required")
    return record


def enforce_document(db: Session, user: User, payload: DocumentExportRequest) -> None:
    """Preparation exports are drafts; source verification still applies."""
    from app.services.dg.source_verification import require_verified_payload
    require_verified_payload(payload.model_dump())


def enforce_bundle(db: Session, user: User, payload: DocumentBundleRequest, *, required: bool = False) -> None:
    from app.services.dg.source_verification import require_verified_payload
    require_verified_payload(payload.model_dump())
    for document in payload.documents:
        require_verified_payload(document.model_dump())


def enforce_shipment(db: Session, user: User, payload: ShipmentIn) -> None:
    if not payload.draft:
        from app.services.dg.source_verification import require_verified_payload
        require_verified_payload(payload.model_dump())
    # Keeping goods is preparation, not permission to transport them. Execution
    # release and final documents are approved against the actual delivery leg.


def submit(db: Session, user: User, payload: ShipmentIn) -> DgReview:
    from app.services.documents import get_document, validate_document
    if not has_dg(payload) or not payload.dangerous_goods or not payload.bundle or not payload.bundle.documents:
        raise error(422, "review.incomplete")
    for entry in payload.dangerous_goods:
        products = entry.get("products")
        if not isinstance(products, list) or not products or any(
            not isinstance(product, dict) or not str(product.get("un_number") or "").strip()
            for product in products
        ):
            raise error(422, "review.incomplete")
    if (payload.bundle.cargo != payload.cargo
            or payload.bundle.dangerous_goods != payload.dangerous_goods
            or payload.bundle.profiles != payload.profiles
            or payload.bundle.output_language != payload.language
            or sorted(payload.documents) != sorted(item.document_key for item in payload.bundle.documents)):
        raise error(422, "review.inconsistent")
    from app.services.documents.signature import decode_signature_image
    if payload.bundle.signature_image:
        try:
            decode_signature_image(payload.bundle.signature_image)
        except ValueError as exc:
            raise error(422, "review.incomplete") from exc
    for item in payload.bundle.documents:
        if item.signature_image and item.signature_image != payload.bundle.signature_image:
            raise error(422, "review.inconsistent")
        if (item.dangerous_goods != payload.dangerous_goods or item.lines != payload.lines
                or item.profiles != payload.profiles or item.modality != payload.modality
                or item.output_language != payload.language or item.cargo != payload.cargo):
            raise error(422, "review.inconsistent")
        document = get_document(item.document_key)
        if document is None:
            raise error(422, "review.incomplete")
        errors, _ = validate_document(document, item.values, item.lines, item.dangerous_goods, item.output_language)
        if errors:
            raise error(422, "review.incomplete")
    serialized = canonical(payload.model_dump())
    if len(serialized.encode()) > MAX_BYTES:
        raise error(413, "review.too_large")
    digest = fingerprint(payload)
    existing = db.query(DgReview).filter_by(created_by_id=user.id, created_by=user.username,
                                           fingerprint=digest).filter(DgReview.status.in_(["pending", "approved"])).first()
    if existing:
        return existing
    record = DgReview(id=str(uuid4()), created_by_id=user.id, created_by=user.username,
                      reference=str(payload.values.get("shipment_reference") or payload.values.get("reference") or "")[:255],
                      modality=payload.modality, fingerprint=digest, payload_json=serialized)
    from app.services.work_queue import loading_date
    record.work_due_date = loading_date(payload.values)
    record.work_draft_fingerprint = fingerprint(payload.model_copy(update={"bundle": None}))
    record.work_consignee = str(payload.values.get("consignee_name") or "")[:255]
    if payload.dg_review_id:
        previous = db.get(DgReview, payload.dg_review_id)
        if previous and owns(previous, user) and previous.id != record.id:
            previous.work_completed_at = datetime.now(timezone.utc)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def summary(record: DgReview) -> dict:
    return {key: getattr(record, key) for key in ("id", "shipment_id", "reference", "modality", "status", "created_by", "created_at",
                                                  "reviewed_by", "reviewed_at", "comment")}
