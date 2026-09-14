"""An authenticated overview, with independent history and DG-review visibility."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.api.routes.history import _record
from app.core.database import get_db
from app.core.deps import get_current_user, require_history
from app.models.user import User
from app.services import audit, work_queue

router = APIRouter(prefix="/work", tags=["work"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_work(day: date, bucket: Literal["attention", "waiting", "today", "ready", "closed", "all"] = "attention",
              q: str = Query(default="", max_length=120), mine: bool = False,
              page: int = Query(default=1, ge=1), per_page: int = Query(default=20, ge=1, le=50),
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return work_queue.listing(db, user, day=day, bucket=bucket, q=q, mine=mine, page=page, per_page=per_page)


@router.get("/people", dependencies=[Depends(require_history)])
def list_people(shipment_id: int, q: str = Query(default="", max_length=80),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return work_queue.people(db, user, _record(shipment_id, db, user), q)


class WorkChange(BaseModel):
    version: int = Field(ge=0)
    owner_id: int | None = Field(default=None, gt=0)
    completed: bool | None = None

    @model_validator(mode="after")
    def action_required(self):
        if self.owner_id is None and self.completed is None:
            raise ValueError("Choose an assignment or completion action")
        return self


@router.patch("/shipments/{shipment_id}", dependencies=[Depends(require_history)])
def change_work(request: Request, shipment_id: int, payload: WorkChange,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    record = work_queue.change(db, user, _record(shipment_id, db, user), **payload.model_dump())
    audit.record(db, "shipment.work_changed", actor=user, target=("shipment", record.id), request=request)
    return {"ok": True, "version": record.work_version}
