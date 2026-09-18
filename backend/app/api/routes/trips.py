"""Kept groupage trips: the list, the record, keeping and forgetting.

Mounted with the history routers behind ``require_history``, so an
installation whose administrator has not switched *Keep shipments* on
answers 404 here — the same promise the shipments page keeps, enforced the
same way.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.messages import error
from app.models.trip import Trip
from app.models.user import User
from app.schemas.trips import TripDetail, TripPage
from app.services import audit, departments, trips

router = APIRouter(prefix="/trips", tags=["trips"])


def _record(trip_id: int, db: Session, viewer: User) -> Trip:
    record = db.get(Trip, trip_id)
    # Another department's trip is, for this viewer, not there.
    if record is None or not departments.may_see(record, viewer):
        raise HTTPException(status_code=404, detail="Trip not found")
    return record


@router.get("", response_model=TripPage)
def list_trips(
    q: str = Query(default="", max_length=120),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, ge=1, le=trips.PER_PAGE_MAX),
    department: str = Query(default="", max_length=16),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows, total = trips.search(db, user, q=q, date_from=date_from, date_to=date_to,
                               page=page, per_page=per_page, department=department)
    return TripPage(items=[trips.summary(r) for r in rows], total=total,
                    page=page, per_page=per_page)


@router.post("")
def keep_trip(user: User = Depends(get_current_user)):
    raise error(409, "delivery.legacy_readonly")


@router.put("/{trip_id}")
def update_trip(trip_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _record(trip_id, db, user)
    raise error(409, "delivery.legacy_readonly")


@router.get("/{trip_id}", response_model=TripDetail)
def get_trip(trip_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return trips.detail(_record(trip_id, db, user))


@router.delete("/{trip_id}")
def forget_trip(request: Request, trip_id: int,
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    record = _record(trip_id, db, user)
    gone_id, name = record.id, record.name or ""
    trips.forget(db, record)
    audit.record(db, "trip.forgotten", actor=user, target=("trip", gone_id),
                 summary=name, request=request)
    return {"ok": True}
