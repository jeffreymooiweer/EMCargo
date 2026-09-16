from typing import Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.messages import error as api_error
from app.core.database import get_db
from app.core.deps import get_current_user, require_manager
from app.models.user import Equipment, User
from app.models.equipment import EquipmentEvent, EquipmentFile
from app.schemas.equipment import EquipmentBase, EquipmentMovement, EquipmentOut, EquipmentUpdate
from app.services import equipment as library
from app.services.equipment_import import (
    EQUIPMENT_EXAMPLE,
    EQUIPMENT_HEADERS,
    equipment_to_rows,
    import_equipment_rows,
)
from app.services.spreadsheet_io import (
    ImportLimitError,
    MAX_IMPORT_CELL_CHARS,
    MAX_IMPORT_COLUMNS,
    MAX_IMPORT_ROWS,
    build_xlsx,
    build_xlsx_template,
    read_limited_upload,
    read_tabular_file,
)

equipment_router = APIRouter(prefix="/equipment", tags=["equipment"])


class MessageOut(BaseModel):
    """A message the interface translates itself, with an English fallback."""

    code: str
    message: str
    params: dict[str, Any] = Field(default_factory=dict)


class EquipmentImportResultOut(BaseModel):
    created: int
    updated: int
    skipped: int
    #: One entry per unusable row, as ``{"code", "message", "params"}`` so the
    #: interface can render it in its own language.
    errors: list[MessageOut]


def _equipment_out(item: Equipment, db: Session) -> EquipmentOut:
    return EquipmentOut(**library.to_dict(item, library.list_files(db, item.id)))


@equipment_router.get("", response_model=list[EquipmentOut])
def list_equipment(q: str = Query(default="", max_length=120),
                   active_only: bool = False, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    from sqlalchemy import or_
    query = db.query(Equipment)
    if active_only:
        query = query.filter(Equipment.active.is_(True))
    if q.strip():
        needle = f"%{q.strip()}%"
        query = query.filter(or_(Equipment.specifications.ilike(needle), Equipment.asset_code.ilike(needle),
                                 Equipment.container_number.ilike(needle), Equipment.details_json.ilike(needle)))
    items = query.order_by(Equipment.specifications, Equipment.id).all()
    files: dict[int, list[EquipmentFile]] = {}
    for file in db.query(EquipmentFile).order_by(EquipmentFile.created_at.desc(), EquipmentFile.id):
        files.setdefault(file.equipment_id, []).append(file)
    return [library.to_dict(item, files.get(item.id, [])) for item in items]


@equipment_router.post("", response_model=EquipmentOut)
def create_equipment(payload: EquipmentBase, admin: User = Depends(require_manager),
                     db: Session = Depends(get_db)):
    item = library.save(db, payload.model_dump(mode="json"), admin)
    library.commit(db)
    return _equipment_out(item, db)


@equipment_router.get("/import-template")
def download_equipment_template(user: User = Depends(get_current_user)):
    content = build_xlsx_template(EQUIPMENT_HEADERS, EQUIPMENT_EXAMPLE, sheet_name="Materieel import")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="materieel_import_template.xlsx"'},
    )


@equipment_router.get("/export")
def export_equipment_library(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The whole library, in the import's own columns, when someone asks.

    On request only — no scheduled dumps, nothing written anywhere. The file
    round-trips: importing it into an empty installation recreates the
    library, which makes it the backup and the hand-over format in one. An
    empty library exports its headers, which doubles as a template.
    """
    items = db.query(Equipment).order_by(Equipment.specifications).all()
    content = build_xlsx(EQUIPMENT_HEADERS, equipment_to_rows(items), sheet_name="Materieel export")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="materieel_export.xlsx"'},
    )


@equipment_router.post("/import", response_model=EquipmentImportResultOut)
async def import_equipment_file(
    file: UploadFile = File(...),
    admin: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise api_error(400, "import.filename_missing")
    try:
        content = await read_limited_upload(file)
    except ImportLimitError as exc:
        raise api_error(413, exc.code, **exc.params) from exc
    if not content:
        raise api_error(400, "import.empty_file")
    try:
        rows = read_tabular_file(
            content,
            file.filename,
            max_rows=MAX_IMPORT_ROWS,
            max_columns=MAX_IMPORT_COLUMNS,
            max_cell_chars=MAX_IMPORT_CELL_CHARS,
        )
    except ImportLimitError as exc:
        raise api_error(422, exc.code, **exc.params) from exc
    result = import_equipment_rows(db, rows, user=admin)
    if result.created == 0 and result.updated == 0 and not result.errors:
        raise api_error(400, "import.no_usable_lines")
    return EquipmentImportResultOut(
        created=result.created,
        updated=result.updated,
        skipped=result.skipped,
        errors=result.errors,
    )


@equipment_router.get("/{item_id}")
def equipment_detail(item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = library.get(db, item_id)
    files = library.list_files(db, item_id)
    return {**library.to_dict(item, files), "files": [library.file_info(file) for file in files]}


@equipment_router.get("/{item_id}/events")
def equipment_events(item_id: int, before: int | None = Query(default=None, gt=0),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    library.get(db, item_id)
    query = db.query(EquipmentEvent).filter_by(equipment_id=item_id)
    if before:
        query = query.filter(EquipmentEvent.id < before)
    events = query.order_by(EquipmentEvent.id.desc()).limit(51).all()
    return {"events": [{key: getattr(event, key) for key in (
        "id", "actor_name", "action", "from_location", "to_location", "availability", "reference", "notes", "created_at")}
        for event in events[:50]], "next_before": events[49].id if len(events) > 50 else None}


@equipment_router.patch("/{item_id}", response_model=EquipmentOut)
def update_equipment(item_id: int, payload: EquipmentUpdate, admin: User = Depends(require_manager),
                     db: Session = Depends(get_db)):
    item = library.save(db, payload.model_dump(exclude_unset=True), admin, existing=library.get(db, item_id))
    library.commit(db)
    return _equipment_out(item, db)


@equipment_router.post("/{item_id}/movements", response_model=EquipmentOut)
def confirm_movement(item_id: int, payload: EquipmentMovement, admin: User = Depends(require_manager),
                     db: Session = Depends(get_db)):
    item = library.move(db, library.get(db, item_id), payload, admin)
    library.commit(db)
    return _equipment_out(item, db)


@equipment_router.post("/{item_id}/files")
async def upload_equipment_file(item_id: int, file: UploadFile = File(...),
                                admin: User = Depends(require_manager), db: Session = Depends(get_db)):
    item = library.get(db, item_id)
    content = await file.read(library.MAX_FILE_BYTES + 1)
    record = library.attach(db, item, content, file.filename or "document")
    library.commit(db)
    return library.file_info(record)


def _file(db: Session, item_id: int, file_id: str) -> EquipmentFile:
    record = db.query(EquipmentFile).filter_by(id=file_id, equipment_id=item_id).first()
    if record is None:
        raise api_error(404, "equipment.file_missing")
    return record


@equipment_router.get("/{item_id}/files/{file_id}")
def read_equipment_file(item_id: int, file_id: str, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    from urllib.parse import quote
    record = _file(db, item_id, file_id)
    disposition = "inline" if record.kind == "photo" else "attachment"
    return Response(content=record.content, media_type=record.media_type, headers={
        "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(record.name, safe='')}",
        "Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"})


@equipment_router.delete("/{item_id}/files/{file_id}")
def remove_equipment_file(item_id: int, file_id: str, admin: User = Depends(require_manager),
                          db: Session = Depends(get_db)):
    db.delete(_file(db, item_id, file_id))
    library.commit(db)
    return {"ok": True}


@equipment_router.delete("/{item_id}")
def delete_equipment(item_id: int, admin: User = Depends(require_manager), db: Session = Depends(get_db)):
    item = library.get(db, item_id)
    db.query(EquipmentFile).filter_by(equipment_id=item_id).delete(synchronize_session=False)
    db.query(EquipmentEvent).filter_by(equipment_id=item_id).delete(synchronize_session=False)
    db.delete(item)
    library.commit(db)
    return {"ok": True}
