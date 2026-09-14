"""Writing and reading the audit log.

``record`` is called from the routes and never raises: an audit line that
cannot be written is logged as an error and the action it describes goes
through regardless, because refusing to keep a shipment over a full disk
in the audit table would be the wrong way round. ``prune`` applies the
retention an administrator set. ``page`` and ``rows`` read it back for the
administrator's screen and its export.

What goes in is fixed here in one place — the action codes with a word on
what their summary may say — so a new route cannot quietly start writing
something the privacy page did not promise.
"""
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.ratelimit import client_address
from app.models.audit import AuditEvent
from app.models.user import User

logger = logging.getLogger(__name__)

#: Every action the log can carry, and what its summary is allowed to hold.
#: The interface translates the codes; the summaries are short and factual.
ACTIONS: dict[str, str] = {
    "dg_review.submitted": "a shipment submitted for specialist review (reference only)",
    "dg_review.decided": "specialist release or request for changes (status only)",
    "dg_review.forgotten": "a review and its release removed",
    "auth.login": "signed in (the second factor's method when one was used)",
    "auth.login_failed": "a sign-in refused: unknown name, wrong password, inactive account, wrong code",
    "auth.logout": "signed out",
    "auth.password_changed": "changed their own password",
    "auth.password_reset": "set a new password through a reset link",
    "auth.two_factor_enabled": "enabled their second factor (the method)",
    "auth.two_factor_disabled": "disabled their second factor",
    "auth.recovery_codes_replaced": "replaced their recovery codes after second-factor verification",
    "user.created": "an account created (the name and role)",
    "user.updated": "an account changed (which fields)",
    "user.deleted": "an account deleted (the name)",
    "user.two_factor_cleared": "an account's second factor cleared by an administrator",
    "settings.changed": "the installation's settings changed (which keys, never the values)",
    "settings.history_discarded": "every kept shipment and trip deleted before switching the history off (the counts)",
    "shipment.kept": "a shipment kept (its reference)",
    "shipment.updated": "a kept shipment kept again (its reference)",
    "shipment.work_changed": "office task assignment or completion changed (record identity only)",
    "shipment.forgotten": "a kept shipment deleted (its reference)",
    "shipment.documents": "a kept shipment's documents handed out again",
    "shipment.export": "a kept shipment's structured export handed out",
    "trip.kept": "a groupage trip kept (its name)",
    "trip.updated": "a kept trip kept again (its name)",
    "trip.forgotten": "a kept trip deleted (its name)",
    "documents.exported": "a document rendered and handed out (the document key)",
    "documents.bundle": "the bundle handed out (how many documents)",
    "documents.mailed": "the bundle mailed (how many recipients, never who)",
    "report.rendered": "the safety adviser's report handed out (the year and the form)",
}

#: How much is kept by default when no administrator set a retention.
DEFAULT_RETENTION_DAYS = 365


def record(db: Session, action: str, *, actor: User | None = None, actor_username: str = "",
           target: tuple[str, Any] | None = None, summary: str = "",
           request: Request | None = None) -> None:
    """Write one line. Never raises; an audit failure must not fail the action.
    """
    if action not in ACTIONS:
        raise ValueError(f"unknown audit action: {action}")
    try:
        event = AuditEvent(
            actor_id=actor.id if actor is not None and actor.id else None,
            actor_username=(actor.username if actor is not None else actor_username or "")[:150],
            action=action,
            target_type=(target[0] if target else "")[:32],
            target_id=str(target[1] if target else "")[:64],
            summary=(summary or "")[:255],
            client=(client_address(request) if request is not None else "")[:64],
        )
        db.add(event)
        db.commit()
    except Exception:  # pragma: no cover - the one place a broad catch is the point
        logger.exception("The audit line for %s could not be written", action)
        try:
            db.rollback()
        except Exception:
            pass


def prune(db: Session, days: int) -> int:
    """Delete what is older than the retention. Returns how many lines went."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    removed = db.query(AuditEvent).filter(AuditEvent.at < cutoff).delete(synchronize_session=False)
    db.commit()
    return int(removed or 0)


def _query(db: Session, *, actor: str = "", action: str = "", since: datetime | None = None,
           until: datetime | None = None):
    stmt = select(AuditEvent)
    if actor:
        stmt = stmt.where(AuditEvent.actor_username == actor)
    if action:
        stmt = stmt.where(AuditEvent.action == action) if "." in action \
            else stmt.where(AuditEvent.action.like(f"{action}.%"))
    if since is not None:
        stmt = stmt.where(AuditEvent.at >= since)
    if until is not None:
        stmt = stmt.where(AuditEvent.at <= until)
    return stmt


def as_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "at": event.at.isoformat() if event.at else None,
        "actor_id": event.actor_id,
        "actor_username": event.actor_username,
        "action": event.action,
        "target_type": event.target_type,
        "target_id": event.target_id,
        "summary": event.summary,
        "client": event.client,
    }


def page(db: Session, *, actor: str = "", action: str = "", since: datetime | None = None,
         until: datetime | None = None, number: int = 1, per_page: int = 50) -> dict[str, Any]:
    stmt = _query(db, actor=actor, action=action, since=since, until=until)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    items = db.execute(
        stmt.order_by(AuditEvent.at.desc(), AuditEvent.id.desc())
        .offset((number - 1) * per_page).limit(per_page)).scalars().all()
    return {"items": [as_dict(e) for e in items], "total": int(total),
            "page": number, "per_page": per_page}


def actors(db: Session) -> list[str]:
    rows = db.execute(select(AuditEvent.actor_username).distinct()
                      .order_by(AuditEvent.actor_username)).scalars().all()
    return [r for r in rows if r]


#: What a spreadsheet reads as the start of a formula rather than as text.
FORMULA_LEADS = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(value: Any) -> str:
    """A cell a spreadsheet will show, not run.

    A shipment reference "=1+1" or a user name "@cmd" arrives in the log as
    typed; opened in a spreadsheet, a cell that starts that way is a
    formula, and a formula can reach out of the file. A leading apostrophe
    makes it text again — the convention every spreadsheet understands and
    strips on display.
    """
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_LEADS) else text


def export_csv(db: Session, *, actor: str = "", action: str = "", since: datetime | None = None,
               until: datetime | None = None) -> str:
    """The filtered log as CSV, oldest first, for whoever keeps records elsewhere."""
    stmt = _query(db, actor=actor, action=action, since=since, until=until)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["at", "actor", "action", "target_type", "target_id", "summary", "client"])
    for e in db.execute(stmt.order_by(AuditEvent.at.asc(), AuditEvent.id.asc())).scalars():
        writer.writerow([csv_cell(cell) for cell in (
            e.at.isoformat() if e.at else "", e.actor_username, e.action,
            e.target_type, e.target_id, e.summary, e.client)])
    return out.getvalue()
