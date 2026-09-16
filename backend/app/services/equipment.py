"""Typed library records, frozen shipment selections and confirmed movements."""
from __future__ import annotations

import hashlib
import io
import json
import math
import re
import uuid

from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError
from pypdf import PdfReader
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.messages import error as api_error
from app.models.equipment import EquipmentEvent, EquipmentFile
from app.models.user import Equipment, User
from app.schemas.equipment import EquipmentBase, EquipmentDetails, EquipmentMovement, EquipmentSnapshot

BASE_FIELDS = {"specifications", "kind", "asset_code", "container_number", "length_cm", "width_cm", "height_cm",
               "wall_thickness_mm", "weight_kg", "source", "notes", "active"}
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_FILES = 12


def get(db: Session, item_id: int) -> Equipment:
    item = db.get(Equipment, item_id)
    if item is None:
        raise api_error(404, "equipment.not_found")
    return item


def details(item: Equipment) -> dict:
    return EquipmentDetails.model_validate(json.loads(item.details_json or "{}")).model_dump(mode="json")


def to_dict(item: Equipment, files: list[EquipmentFile] | None = None) -> dict:
    attached = files or []
    photo = next((file for file in attached if file.kind == "photo"), None)
    base = {key: getattr(item, key) for key in BASE_FIELDS}
    # Older imports accepted zero/invalid optional dimensions as unknown. Keep
    # those rows readable without weakening validation for new measurements.
    for key in ("length_cm", "width_cm", "height_cm", "wall_thickness_mm"):
        value = base[key]
        if value is not None and (not math.isfinite(value) or value <= 0):
            base[key] = None
    return {**details(item), **base,
            "asset_code": item.asset_code or "", "container_number": item.container_number or "",
            "id": item.id, "version": item.version or 1,
            "aliases": json.loads(item.aliases_json or "[]"),
            "language_labels": json.loads(item.language_labels_json or "{}"),
            "photo_url": f"/api/equipment/{item.id}/files/{photo.id}" if photo else None,
            "file_count": len(attached)}


def snapshot(item: Equipment) -> dict:
    return EquipmentSnapshot.model_validate({**to_dict(item), "equipment_id": item.id}).model_dump(mode="json")


def list_files(db: Session, item_id: int) -> list[EquipmentFile]:
    return db.query(EquipmentFile).filter_by(equipment_id=item_id).order_by(EquipmentFile.created_at.desc(), EquipmentFile.id).all()


def file_info(file: EquipmentFile) -> dict:
    return {key: getattr(file, key) for key in ("id", "name", "media_type", "kind", "size", "sha256", "created_at")}


def add_event(db: Session, item: Equipment, user: User | None, action: str, *, previous_location: str = "",
              reference: str = "", notes: str = "") -> None:
    data = details(item)
    db.add(EquipmentEvent(equipment_id=item.id, actor_id=user.id if user else None,
                          actor_name=user.username if user else "", action=action,
                          from_location=previous_location, to_location=data["current_location"],
                          availability=data["availability"], reference=reference, notes=notes))


def save(db: Session, payload: dict, user: User | None, existing: Equipment | None = None,
         *, allow_location: bool = False) -> Equipment:
    """Use a compare-and-swap update so a stale edit cannot undo a movement."""
    previous = to_dict(existing) if existing else {}
    expected = payload.get("version", existing.version if existing else 1)
    if existing and expected is not None and expected != existing.version:
        raise api_error(409, "equipment.changed")
    if "inspection_due" in payload and "inspections" not in payload:
        # Legacy clients maintain only their original generic inspection; they
        # must never overwrite electrical, cooling or vehicle inspections.
        inspections = [entry for entry in previous.get("inspections", []) if entry["id"] != "legacy-inspection"]
        if payload["inspection_due"]:
            inspections.append({"id": "legacy-inspection", "kind": "general", "due_on": payload["inspection_due"]})
        payload = {**payload, "inspections": inspections}
    try:
        data = EquipmentBase.model_validate({**previous, **payload}).model_dump(mode="json")
    except ValidationError as exc:
        code = exc.errors()[0]["type"]
        if code.startswith("equipment."):
            raise api_error(422, code) from exc
        raise api_error(422, "equipment.invalid", reason="; ".join(error["msg"] for error in exc.errors())) from exc
    if existing and data["current_location"] != previous["current_location"] and not allow_location:
        raise api_error(409, "equipment.move_required")
    for key in ("asset_code", "container_number"):
        if data[key]:
            match = db.query(Equipment).filter(getattr(Equipment, key) == data[key])
            if existing:
                match = match.filter(Equipment.id != existing.id)
            if match.first():
                raise api_error(409, "equipment.identifier_used", identifier=data[key])
    values = {key: data[key] for key in BASE_FIELDS}
    for key in ("asset_code", "container_number"):
        values[key] = values[key] or None
    values.update(aliases_json=json.dumps(data["aliases"]), language_labels_json=json.dumps(data["language_labels"]),
                  details_json=json.dumps({key: data[key] for key in EquipmentDetails.model_fields}),
                  version=(existing.version + 1) if existing else 1)
    if existing:
        changed = db.query(Equipment).filter(Equipment.id == existing.id, Equipment.version == existing.version).update(values, synchronize_session=False)
        if not changed:
            raise api_error(409, "equipment.changed")
        db.refresh(existing)
        item = existing
    else:
        item = Equipment(**values)
        db.add(item)
        db.flush()
    if existing is None:
        add_event(db, item, user, "created")
    elif previous["active"] != data["active"]:
        add_event(db, item, user, "restored" if data["active"] else "archived", previous_location=previous["current_location"])
    elif not allow_location and any(previous[key] != data[key] for key in ("availability", "planned_reference", "planned_date", "condition")):
        add_event(db, item, user, "status", previous_location=previous["current_location"], reference=data["planned_reference"])
    if existing is not None and previous["inspections"] != data["inspections"]:
        add_event(db, item, user, "inspections")
    return item


def move(db: Session, item: Equipment, payload: EquipmentMovement, user: User) -> Equipment:
    before = details(item)["current_location"]
    item = save(db, {"version": payload.version, "current_location": payload.to_location,
                     "availability": payload.availability, "planned_reference": "", "planned_date": None}, user,
                existing=item, allow_location=True)
    add_event(db, item, user, "moved", previous_location=before, reference=payload.reference, notes=payload.notes)
    return item


def attach(db: Session, item: Equipment, content: bytes, filename: str) -> EquipmentFile:
    """Keep bounded PDFs or normalised bitmap photos; filenames are never paths."""
    if not content or len(content) > MAX_FILE_BYTES:
        raise api_error(413, "equipment.file_size")
    if db.query(func.count(EquipmentFile.id)).filter_by(equipment_id=item.id).scalar() >= MAX_FILES:
        raise api_error(409, "equipment.file_limit")
    name = re.sub(r"[\x00-\x1f\x7f]", "", filename.replace("\\", "/").rsplit("/", 1)[-1]).strip()[:180] or "document"
    if content.startswith(b"%PDF-"):
        try:
            pdf = PdfReader(io.BytesIO(content))
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 200:
                raise ValueError("Unreadable PDF")
        except Exception as exc:
            raise api_error(422, "equipment.file_invalid") from exc
        kind, media_type = "document", "application/pdf"
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
    else:
        try:
            with Image.open(io.BytesIO(content)) as picture:
                if picture.format not in {"JPEG", "PNG", "WEBP"} or getattr(picture, "n_frames", 1) != 1 or picture.width * picture.height > 25_000_000:
                    raise ValueError("Unsupported photo")
                picture.load()
                from PIL import ImageOps
                picture = ImageOps.exif_transpose(picture).convert("RGB")
                picture.thumbnail((1600, 1600))
                output = io.BytesIO()
                picture.save(output, format="JPEG", quality=88)
                content = output.getvalue()
        except (UnidentifiedImageError, ValueError, OSError, Image.DecompressionBombError) as exc:
            raise api_error(422, "equipment.file_invalid") from exc
        kind, media_type = "photo", "image/jpeg"
        name = name.rsplit(".", 1)[0] + ".jpg"
    record = EquipmentFile(id=str(uuid.uuid4()), equipment_id=item.id, name=name, media_type=media_type,
                           kind=kind, size=len(content), sha256=hashlib.sha256(content).hexdigest(), content=content)
    db.add(record)
    db.flush()
    return record


def commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(409, "equipment.identifier_conflict") from exc
