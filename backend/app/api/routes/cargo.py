"""Authenticated cargo contract; assessment never retains a shipment."""
import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_manager
from app.core.messages import error
from app.models.cargo import CargoIdentity, PackagingTemplate
from app.models.user import User
from app.schemas.cargo import CargoAssessmentIn, PackagingTemplateIn
from app.services import cargo, packaging

router = APIRouter(prefix="/cargo", tags=["cargo"], dependencies=[Depends(get_current_user)])


@router.get("/templates")
def templates(active_only: bool = True, db: Session = Depends(get_db)):
    return packaging.list_templates(db, active_only)


@router.post("/templates")
def create_template(payload: PackagingTemplateIn, user: User = Depends(require_manager), db: Session = Depends(get_db)):
    return packaging.save(db, payload)


@router.put("/templates/{template_id}")
def update_template(template_id: str, payload: PackagingTemplateIn, user: User = Depends(require_manager), db: Session = Depends(get_db)):
    return packaging.save(db, payload, template_id)


@router.delete("/templates/{template_id}")
def archive_template(template_id: str, version: int = Query(ge=1), user: User = Depends(require_manager), db: Session = Depends(get_db)):
    record = db.get(PackagingTemplate, template_id)
    if record is None:
        raise error(404, "cargo.template_missing")
    return packaging.save(db, PackagingTemplateIn(**{**json.loads(record.data_json), "active": False, "version": version}), template_id)


@router.post("/v1/assess")
def assess(payload: CargoAssessmentIn):
    return cargo.assess(payload.cargo, payload.lines)


@router.get("/v1/contract")
def contract():
    return {"schema_version": 1, "units": {"dimensions": "mm", "mass": "kg", "volume": "m3"},
            "capabilities": ["mixed_contents", "nested_units", "partial_allocation", "unpacked_cargo", "unknown_measurements", "revision_checks"],
            "schema": CargoAssessmentIn.model_json_schema()}


@router.get("/units")
def reusable_units(q: str = Query(default="", max_length=120), equipment_id: int | None = Query(default=None, gt=0), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Physical-unit master data follows the shared equipment library's access.
    # It carries no shipment, customer, contents, parent or historic load data.
    # Keeping masters reachable after history deletion avoids stranding a
    # permanent identity and assigning a second number to the same equipment.
    query = db.query(CargoIdentity).filter(CargoIdentity.reusable.is_(True))
    if equipment_id is not None:
        query = query.filter(CargoIdentity.equipment_id == equipment_id)
    if q.strip():
        query = query.filter(CargoIdentity.unit_json.contains(q.strip(), autoescape=True))
    return [json.loads(item.unit_json) for item in query.order_by(CargoIdentity.code).limit(200)]
