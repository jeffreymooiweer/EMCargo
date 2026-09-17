"""Authenticated access to the UN cards a transport-document QR code opens.

The administrator's switch enables card links, never anonymous access. Both
lookup and direct PDF requests require the same active session and second
factor policy as the rest of the application. The frontend retains the scan's
full URL through sign-in.

A card that is not in the store is reported absent. It is never substituted
from another modality: the regimes print different obligations, and a card
that answers for the wrong one is worse than no card at all.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.ratelimit import CARD_LINKS, limiter
from app.services.documents.un_card_store import MODALITIES, card_path
from app.services.settings_store import instance_settings

router = APIRouter(prefix="/cards", tags=["cards"], dependencies=[Depends(get_current_user)])

#: How many UN numbers one link may ask about. A transport document does not
#: carry fifty, and a cap keeps the route from being turned into a
#: bulk reader of the whole store.
MAX_NUMBERS = 30


def _enabled(db: Session) -> None:
    if not instance_settings(db).card_links_enabled:
        # A disabled feature stays absent even for a signed-in account.
        raise HTTPException(status_code=404, detail="Not found")


def _numbers(raw: str) -> list[str]:
    found: list[str] = []
    for part in re.split(r"[,\s]+", raw or ""):
        digits = re.sub(r"\D", "", part)
        if len(digits) == 4 and digits not in found:
            found.append(digits)
    return found[:MAX_NUMBERS]


@router.get("/lookup")
@limiter.limit(CARD_LINKS)
def card_lookup(
    request: Request,
    un: str = Query(default="", max_length=400),
    modality: str = Query(default="ADR", max_length=10),
    db: Session = Depends(get_db),
):
    """Which of these UN numbers this installation holds a card for.

    Reports the absent ones as plainly as the present ones. Somebody standing
    at a vehicle needs to know that a card is missing, not to be shown a
    shorter list and left to assume it was complete.
    """
    _enabled(db)
    wanted = str(modality).strip().upper()
    if wanted not in MODALITIES:
        raise HTTPException(status_code=400, detail="Unknown modality")
    numbers = _numbers(un)
    return {
        "modality": wanted,
        "cards": [
            {"un_number": number, "available": card_path(number, wanted) is not None}
            for number in numbers
        ],
    }


@router.get("/{un}/{modality}.pdf")
@limiter.limit(CARD_LINKS)
def card_file(
    request: Request,
    un: str,
    modality: str,
    db: Session = Depends(get_db),
):
    _enabled(db)
    path = card_path(un, str(modality).strip().upper())
    if path is None:
        raise HTTPException(status_code=404, detail="No card for this UN number")
    return FileResponse(path, media_type="application/pdf",
                        filename=path.name)
