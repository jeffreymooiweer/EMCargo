"""Departments: who sees whose kept shipments.

The rule, in one place so the routes cannot each keep their own version:

- An **administrator** sees every kept shipment, and may narrow the list to
  one department or to the shipments nobody's department claims.
- Anybody else sees the shipments of **their own department** — and a user
  without a department sees the shipments without one. An organisation that
  never makes a department therefore keeps today's behaviour, everybody
  seeing everything, without anyone having to set anything.

A shipment's department is the keeper's department at the moment it was
kept, copied onto the row. Somebody moving departments does not take last
year's shipments along, and a department removed leaves its shipments and
its people without one rather than deleting either.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.shipment import Shipment
from app.models.trip import Trip
from app.models.delivery import Delivery
from app.models.user import Department, User


class DepartmentError(ValueError):
    """A name that is empty or already taken."""


def visible_to(query: Query, viewer: User, department: str = "",
               model: type = Shipment) -> Query:
    """Narrow a query over kept records to what ``viewer`` may see.

    ``department`` is the administrator's filter: ``""`` for everything,
    ``"none"`` for the unassigned, or an id. Anybody else's filter is their
    own department, whatever they ask for. ``model`` is the table — the
    shipments by default, the kept trips carry the same column.
    """
    column = model.department_id
    if viewer.role in {"admin", "super_user", "dg_specialist"}:
        if department == "none":
            return query.filter(column.is_(None))
        if department:
            try:
                return query.filter(column == int(department))
            except ValueError:
                return query.filter(column.is_(None))
        return query
    if viewer.department_id is None:
        return query.filter(column.is_(None))
    return query.filter(column == viewer.department_id)


def may_see(record: Any, viewer: User) -> bool:
    if viewer.role in {"admin", "super_user", "dg_specialist"}:
        return True
    return record.department_id == viewer.department_id


def listing(db: Session) -> list[dict]:
    """Every department with how many people and shipments it holds."""
    users = dict(db.query(User.department_id, func.count(User.id))
                 .filter(User.department_id.isnot(None)).group_by(User.department_id).all())
    shipments = dict(db.query(Shipment.department_id, func.count(Shipment.id))
                     .filter(Shipment.department_id.isnot(None),
                             Shipment.is_draft.is_(False))
                     .group_by(Shipment.department_id).all())
    return [
        {"id": d.id, "name": d.name,
         "users": int(users.get(d.id, 0)), "shipments": int(shipments.get(d.id, 0))}
        for d in db.query(Department).order_by(Department.name).all()
    ]


def _clean_name(db: Session, name: str, except_id: int | None = None) -> str:
    cleaned = " ".join((name or "").split())
    if not cleaned:
        raise DepartmentError("A department needs a name.")
    taken = db.query(Department).filter(func.lower(Department.name) == cleaned.lower())
    if except_id is not None:
        taken = taken.filter(Department.id != except_id)
    if taken.first() is not None:
        raise DepartmentError(f"There is already a department called {cleaned}.")
    return cleaned[:80]


def create(db: Session, name: str) -> Department:
    department = Department(name=_clean_name(db, name))
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def rename(db: Session, department: Department, name: str) -> Department:
    department.name = _clean_name(db, name, except_id=department.id)
    db.commit()
    db.refresh(department)
    return department


def remove(db: Session, department: Department) -> dict:
    """Delete the department; its people, shipments and trips become unassigned.

    Done explicitly rather than left to ``ON DELETE SET NULL``: SQLite only
    honours that with a pragma this application does not set, and a rule that
    silently depends on the engine is a rule that breaks on the other one.
    Every table that names a department is cleared here — a row left with
    the old id would be handed to whichever department is created next
    under that id, which is how v1.187.0 to v1.189.0 treated kept trips.
    """
    counts = {}
    for name, model in (("users", User), ("shipments", Shipment), ("trips", Trip), ("deliveries", Delivery)):
        counts[name] = int(db.query(model).filter(model.department_id == department.id)
                           .update({model.department_id: None}, synchronize_session=False))
    db.delete(department)
    db.commit()
    return {"ok": True, **counts}
