"""What the application can say about itself: version and release notes.

Split off from ``/api/health`` deliberately. Health is unauthenticated because
a Docker HEALTHCHECK has no session; the changelog is behind the same login as
everything else — not because release notes are secret, but because nothing
that is not needed for monitoring should be readable from outside.
"""
import logging
from datetime import datetime, timezone
import threading

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.messages import error
from app.core.deps import get_current_user, require_admin
from app.models.user import User
from app.services import changelog, settings_store, updater, updates
from app.version import get_version

logger = logging.getLogger(__name__)

router = APIRouter(tags=["meta"])
_apply_lock = threading.Lock()


@router.get("/changelog")
def release_notes(
    since: str = Query(default="", max_length=32),
    user: User = Depends(get_current_user),
):
    """The releases newer than ``since``, for the what's-new card.

    ``version`` is the version actually running, which is what the caller
    stores as seen — not the newest entry in the file, so a changelog that is
    ahead of or behind the binary can never wedge the card open.
    """
    result = changelog.entries_since(since)
    return {"version": get_version(), **result}


@router.get("/update-status")
def update_status(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Whether a newer release exists, for the one person who could pull it.

    Admin-only on both grounds: the toast is only useful to whoever operates
    the container, and a signed-in user must not be able to make this
    installation call GitHub when its administrator switched that off — the
    switch is checked here, per request, not once at startup.

    Three shapes of answer, kept distinct on purpose: the check is off
    (``enabled`` false), GitHub could not say (``reachable`` false — which is
    *not* "you are up to date"), or a real comparison.
    """
    current = get_version()
    if not settings_store.instance_settings(db).update_check_enabled:
        return {"enabled": False, "current": current}
    release = updates.latest_release()
    if release is None:
        return {"enabled": True, "reachable": False, "current": current}
    ours = updates.version_key(current)
    theirs = updates.version_key(release["version"])
    return {
        "enabled": True,
        "reachable": True,
        "current": current,
        "latest": release["version"],
        "url": release["url"],
        "update_available": ours is not None and theirs is not None and theirs > ours,
    }


@router.post("/update-check")
def update_check_now(admin: User = Depends(require_admin),
                     db: Session = Depends(get_db)):
    """A fresh look at the release feed, on the administrator's click.

    The passive status call lives off a six-hour cache so settings visits
    stay cheap; this one empties that cache first, because a person who
    presses "check now" is asking GitHub, not the cache.
    """
    if not settings_store.instance_settings(db).update_check_enabled:
        raise error(409, "update.check_disabled")
    updates.clear_cache()
    return update_status(admin=admin, db=db)


@router.get("/update-capability")
def update_capability(admin: User = Depends(require_admin)):
    """Whether this installation can update itself, and if not, why not.

    Missing socket access, container identity and unsupported installation
    methods need different fixes; the screen names the actual prerequisite.
    """
    return updater.capability()


@router.get("/update-state")
def update_state(response: Response, admin: User = Depends(require_admin)):
    """How the last in-app update went, surviving the restart it caused.

    Reads must neither consume completion for other browsers nor clear a
    newer operation written after this request read the file. The next update
    replaces the record. Progress and the running version must not be cached
    across the restart, or an old browser can keep resuming an old operation.
    """
    state = updater.read_state()
    response.headers["Cache-Control"] = "private, no-store"
    return {"state": state, "current": get_version()}


@router.post("/update-apply")
def update_apply(admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    """Update to the newest release and restart on a supported installation.

    The version is never caller input: it is whatever the check found,
    compared against what runs. The pull and the swap happen in the
    background — the response returns before the restart, and the client
    follows progress through the state endpoint until the connection
    drops and the new instance answers.
    """
    ability = updater.capability()
    if not ability["available"]:
        raise error(409, "update.unavailable", reason=ability["reason"])
    status = update_status(admin=admin, db=db)
    if not status.get("update_available"):
        raise error(409, "update.no_update")
    target = status["latest"]
    if not _apply_lock.acquire(blocking=False):
        raise error(409, "update.in_progress")
    previous = updater.read_state()
    if previous and previous.get("phase") in ("pulling", "handed_over", "stopping"):
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(previous["at"].replace("Z", "+00:00"))).total_seconds()
        except (ValueError, KeyError, TypeError):
            age = float("inf")
        if age < 20 * 60:
            _apply_lock.release()
            raise error(409, "update.in_progress")
    updater.write_state({"phase": "pulling", "to": target})

    def run() -> None:
        try:
            updater.start_update(target)
        except Exception as exc:
            # Socket disconnects and filesystem failures must also terminate
            # progress visibly, rather than leave the screen polling forever.
            logger.exception("In-app update to %s failed", target)
            updater.write_state({"phase": "failed", "to": target, "error": str(exc)})
        finally:
            _apply_lock.release()

    try:
        threading.Thread(target=run, name="update-apply", daemon=True).start()
    except Exception:
        _apply_lock.release()
        updater.write_state({"phase": "failed", "to": target, "error": "Could not start the update worker"})
        raise
    return {"started": True, "to": target}
