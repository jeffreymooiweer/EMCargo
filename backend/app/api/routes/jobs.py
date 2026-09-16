from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas import CalculateRequest, ParseRequest
from app.services.pipeline import parse_and_calculate

router = APIRouter(tags=["workflow"])


@router.post("/parse")
def parse_text(payload: ParseRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return parse_and_calculate(
        payload.text,
        db,
        column_map=payload.column_map,
        has_header=payload.has_header,
        input_language=payload.input_language,
        mode="continue",
    )


@router.post("/calculate")
def calculate(payload: CalculateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.lines:
        from app.services.container_loading import assess
        payload.lines, _ = assess(payload.lines)
        result = {
            "success": True,
            "column_map": payload.column_map or {},
            "lines": payload.lines,
            "totals": {},
            "errors": [],
        }
        included = [line for line in payload.lines if line.get("include", True)]
        result["totals"] = {
            "line_count": len(payload.lines),
            "included_count": len(included),
            "total_quantity": sum(line.get("quantity") or 0 for line in included),
            "total_weight_kg": round(sum(line.get("weight_total_kg") or 0 for line in included), 2),
            "total_material_volume_m3": round(sum(line.get("material_volume_m3") or 0 for line in included), 6),
            "total_transport_volume_m3": round(sum(line.get("transport_volume_m3") or 0 for line in included), 6),
            "warning_count": sum(1 for line in payload.lines if line.get("status") in {"warning", "needs_review"}),
            "error_count": sum(1 for line in payload.lines if line.get("status") == "error"),
        }
        return result
    if not payload.text:
        raise HTTPException(status_code=400, detail="text or lines required")
    return parse_and_calculate(
        payload.text,
        db,
        column_map=payload.column_map,
        has_header=payload.has_header,
        input_language=payload.input_language,
        output_language=payload.output_language,
        mode=payload.mode,
        line_overrides=payload.line_overrides,
    )
