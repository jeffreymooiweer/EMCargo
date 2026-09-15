"""One administrator screen for the templates used by this installation."""
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.core.messages import error
from app.models.user import User
from app.services import audit, document_templates

router = APIRouter(prefix="/settings/document-templates", tags=["settings"])


@router.get("")
def list_templates(admin: User = Depends(require_admin)):
    return document_templates.status()


@router.post("/{key}")
async def import_template(request: Request, key: str,
                          file: UploadFile = File(...),
                          source: str = Form(..., max_length=1000),
                          rights_basis: str = Form(..., max_length=1000),
                          admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    content = await file.read(document_templates.MAX_BYTES + 1)
    receipt = document_templates.install(key, content, source=source,
                                         rights_basis=rights_basis, actor=admin.username)
    audit.record(db, "templates.imported", actor=admin, target=("template", key),
                 summary=receipt["sha256"], request=request)
    return {"ok": True, "sha256": receipt["sha256"]}


@router.get("/{key}/preview")
def preview_template(key: str, admin: User = Depends(require_admin)):
    path = document_templates.resolve(key)
    if path is None:
        raise error(404, "templates.missing")
    return FileResponse(path, media_type="application/pdf", filename=f"{key}.pdf")
