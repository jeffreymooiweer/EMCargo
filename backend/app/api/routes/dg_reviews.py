"""The specialist's inbox and the submitter's review status."""
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, defer
from app.core.database import get_db
from app.core.deps import get_current_user, require_dg_specialist
from app.core.messages import error
from app.core.ratelimit import DRAFT_SAVE, limiter
from app.models.dg_review import DgReview
from app.models.user import User
from app.schemas.history import ShipmentIn
from app.services import audit, dg_review

router = APIRouter(prefix="/dg-reviews", tags=["DG reviews"])


@router.get("")
def list_reviews(status: str = Query(default="", pattern="^(pending|approved|changes_requested)?$"),
                 page: int = Query(default=1, ge=1), user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    query = db.query(DgReview).options(defer(DgReview.payload_json))
    if user.role not in {"admin", "dg_specialist"}:
        query = query.filter_by(created_by_id=user.id, created_by=user.username)
    if status:
        query = query.filter_by(status=status)
    total = query.count()
    records = query.order_by(DgReview.created_at.desc(), DgReview.id).offset((page - 1) * 25).limit(25).all()
    return {"items": [dg_review.summary(record) for record in records], "total": total, "page": page}


@router.post("/status")
@limiter.limit(DRAFT_SAVE)
def review_status(request: Request, payload: ShipmentIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    record = db.query(DgReview).filter_by(created_by_id=user.id, created_by=user.username,
                                          fingerprint=dg_review.fingerprint(payload)).order_by(DgReview.created_at.desc()).first()
    return dg_review.summary(record) if record else None


@router.post("")
@limiter.limit(DRAFT_SAVE)
def submit_review(request: Request, payload: ShipmentIn, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    record = dg_review.submit(db, user, payload)
    audit.record(db, "dg_review.submitted", actor=user, target=("dg_review", record.id),
                 summary=record.reference, request=request)
    return dg_review.summary(record)


@router.get("/{review_id}")
def get_review(review_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = dg_review.get_visible(db, review_id, user)
    return {**dg_review.summary(record), "shipment": json.loads(record.payload_json)}


class ReviewDecision(BaseModel):
    status: Literal["approved", "changes_requested"]
    comment: str = Field(default="", max_length=4000)


@router.post("/{review_id}/decision")
def decide_review(request: Request, review_id: str, payload: ReviewDecision,
                  user: User = Depends(require_dg_specialist), db: Session = Depends(get_db)):
    record = dg_review.get_visible(db, review_id, user)
    if payload.status == "changes_requested" and not payload.comment.strip():
        raise error(422, "review.comment_required")
    if payload.status == "approved":
        from app.services.dg.source_verification import require_verified_payload
        require_verified_payload(json.loads(record.payload_json))
    # A conditional UPDATE prevents two open tabs overwriting one decision.
    updated = db.query(DgReview).filter_by(id=record.id, status="pending").update({
        "status": payload.status, "comment": payload.comment.strip(), "reviewed_by": user.username,
        "reviewed_at": datetime.now(timezone.utc).replace(tzinfo=None)}, synchronize_session=False)
    if not updated:
        db.rollback()
        raise error(409, "review.already_decided")
    db.commit()
    db.refresh(record)
    audit.record(db, "dg_review.decided", actor=user, target=("dg_review", record.id),
                 summary=payload.status, request=request)
    return dg_review.summary(record)


@router.delete("/{review_id}")
def forget_review(request: Request, review_id: str, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    record = dg_review.get_visible(db, review_id, user)
    if not dg_review.owns(record, user) and user.role != "admin":
        raise error(403, "review.owner_required")
    db.delete(record)
    db.commit()
    audit.record(db, "dg_review.forgotten", actor=user, target=("dg_review", review_id), request=request)
    return {"ok": True}
