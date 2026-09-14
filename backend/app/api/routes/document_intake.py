"""Local document intake for the installed shipment assistant."""
from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.deps import get_current_user
from app.core.messages import error
from app.core.ratelimit import limiter
from app.models.user import User
from app.services import document_intake
from app.services.assistant import runtime
from app.services.spreadsheet_io import ImportLimitError, read_limited_upload

router = APIRouter(prefix="/assistant/documents", tags=["assistant documents"])


@router.post("/read")
@limiter.limit("6/minute")
async def read_document(request: Request, file: UploadFile = File(...),
                        language: str = Query(default="nl", pattern="^(nl|en|de|fr)$"),
                        user: User = Depends(get_current_user)):
    if not runtime.installed():
        raise error(409, "assistant.model_required")
    try:
        data = await read_limited_upload(file, document_intake.MAX_BYTES)
    except ImportLimitError as exc:
        raise error(413, "intake.file_large") from exc
    finally:
        await file.close()
    return await run_in_threadpool(document_intake.read_document, data, file.filename or "", language)


@router.post("/propose")
@limiter.limit("30/minute")
def propose_document(request: Request, payload: document_intake.ProposalRequest,
                     user: User = Depends(get_current_user)):
    return document_intake.propose(payload)
