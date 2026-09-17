"""Transactional cargo revision and identity retention inside shipment history."""
from __future__ import annotations
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.messages import error
from app.models.cargo import CargoIdentity, CargoUse
from app.models.shipment import Shipment
from app.schemas.cargo import CargoManifest
from app.services.cargo import assess


def canonical(manifest) -> str:
    if manifest is not None and not isinstance(manifest, CargoManifest):
        manifest = CargoManifest.model_validate(manifest)
    if hasattr(manifest, "model_dump"):
        manifest = manifest.model_dump(mode="json")
    value = dict(manifest or {})
    value.pop("revision", None)
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def validate_payload(payload, existing: Shipment | None, db: Session) -> bool:
    """Validate before mutation; return whether the cargo content changed."""
    previous = json.loads(existing.export_json or "{}") if existing else {}
    old = previous.get("cargo")
    if payload.cargo is None:
        if old is not None:
            raise error(409, "cargo.conflict")
        return False
    if existing is not None and existing.cargo_id and existing.cargo_id != payload.cargo.shipment_id:
        raise error(409, "cargo.identity_conflict")
    assess(payload.cargo, payload.lines)
    if payload.snapshot.get("cargo") is not None and canonical(payload.snapshot["cargo"]) != canonical(payload.cargo):
        raise error(422, "cargo.snapshot_mismatch")
    if payload.bundle and (canonical(payload.bundle.cargo) != canonical(payload.cargo) or any(canonical(document.cargo) != canonical(payload.cargo) for document in payload.bundle.documents)):
        raise error(422, "cargo.snapshot_mismatch")
    def goods_state(lines):
        return [{key: line.get(key) for key in ("line_id", "cargo_goods_id", "include", "quantity", "unit", "description", "weight_total_kg", "transport_volume_m3", "package_transport_volume_m3", "material_volume_m3", "dimensions", "length_cm", "width_cm", "height_cm", "equipment", "equipment_role", "cargo_form", "dangerous_goods", "detected_un_numbers")} for line in lines]
    changed = canonical(old) != canonical(payload.cargo) or goods_state(previous.get("goods", [])) != goods_state(payload.lines)
    if existing is not None:
        expected = payload.expected_cargo_revision
        # A read-only retry of identical cargo is safe. Every actual change
        # uses a conditional SQL write, so racing sessions cannot both win.
        if changed and old is not None and expected != existing.cargo_revision:
            raise error(409, "cargo.conflict")
        if changed:
            old_revision = existing.cargo_revision or 0
            updated = db.query(Shipment).filter_by(id=existing.id, cargo_revision=old_revision).update(
                {Shipment.cargo_revision: old_revision + 1}, synchronize_session=False)
            if not updated:
                raise error(409, "cargo.conflict")
            db.refresh(existing)
    return changed


def remember(db: Session, record: Shipment, manifest: CargoManifest | None) -> None:
    """Only called by opt-in history saving; pure assessment stores nothing."""
    if manifest is None:
        return
    previous_unit_ids = {use.unit_id for use in db.query(CargoUse).filter_by(shipment_id=record.id).all()}
    db.query(CargoUse).filter_by(shipment_id=record.id).delete(synchronize_session=False)
    for unit in manifest.units:
        if unit.equipment_id is not None:
            from app.models.user import Equipment
            if db.get(Equipment, unit.equipment_id) is None:
                raise error(404, "equipment.not_found")
        identity = db.get(CargoIdentity, unit.id)
        by_code = db.query(CargoIdentity).filter_by(code=unit.code).first()
        by_equipment = db.query(CargoIdentity).filter_by(equipment_id=unit.equipment_id).first() if unit.equipment_id else None
        if ((by_code and by_code.id != unit.id) or (by_equipment and by_equipment.id != unit.id)
                or (identity and (identity.code != unit.code or identity.reusable != unit.reusable
                                 or identity.equipment_id != unit.equipment_id))):
            raise error(409, "cargo.identity_conflict")
        if identity and not identity.reusable:
            if db.query(CargoUse).filter(CargoUse.unit_id == unit.id, CargoUse.shipment_id != record.id).first():
                raise error(409, "cargo.identity_conflict")
        if unit.reusable and not record.is_draft:
            from app.services.deliveries import unit_in_transit
            if unit_in_transit(db, unit.id) and unit.id not in previous_unit_ids:
                raise error(409, "cargo.unit_in_use")
            active = db.query(CargoUse).join(Shipment, CargoUse.shipment_id == Shipment.id).filter(
                CargoUse.unit_id == unit.id, Shipment.id != record.id,
                Shipment.is_draft.is_(False), Shipment.work_completed_at.is_(None)).all()
            from app.services.delivery_inventory import physical_unit_completed
            if any(not physical_unit_completed(db, use.shipment_id, unit.id) for use in active):
                raise error(409, "cargo.unit_in_use")
        created_identity = identity is None
        if created_identity:
            identity = CargoIdentity(id=unit.id, code=unit.code, reusable=unit.reusable, equipment_id=unit.equipment_id)
            db.add(identity)
        # Do not retain parent references or contents outside shipment storage.
        master = unit.model_dump(mode="json")
        for key in ("parent_id", "group_id", "loaded_dimensions_mm", "measured_gross_kg", "legacy_goods_id"):
            master[key] = None
        if created_identity:
            identity.unit_json = json.dumps(master)
        db.add(CargoUse(shipment_id=record.id, unit_id=unit.id))
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise error(409, "cargo.identity_conflict") from exc


def forget(db: Session, shipment_ids: list[int]) -> None:
    if not shipment_ids:
        return
    db.query(CargoUse).filter(CargoUse.shipment_id.in_(shipment_ids)).delete(synchronize_session=False)
    # Identities have no content, but single-use boxes are also removed with
    # their last retained shipment. Reusable master identities remain useful.
    used = db.query(CargoUse.unit_id)
    db.query(CargoIdentity).filter(CargoIdentity.reusable.is_(False), ~CargoIdentity.id.in_(used)).delete(synchronize_session=False)
