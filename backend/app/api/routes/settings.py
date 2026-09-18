"""Settings for the account, signed-in users and administrators.

The shared router provides options and installation defaults to authenticated
users. Personal settings belong to the account; instance settings require an
administrator and control retention, connections and organisation defaults.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin, require_manager
from app.models.user import User
from app.schemas.settings import (
    MODALITIES,
    InstanceSettings,
    OrganisationSettings,
    MailTestRequest,
    MailTestResult,
    PublicSettings,
    UserPreferences,
)
from app.services import audit, history, mail, settings_store
from app.services.units import UNITS
from app.core.languages import SUPPORTED as SUPPORTED_LANGUAGES

router = APIRouter(prefix="/settings", tags=["settings"])
public_router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/me", response_model=UserPreferences)
def my_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_store.user_preferences(db, user.id)


@router.put("/me", response_model=UserPreferences)
def save_my_settings(
    payload: UserPreferences,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return settings_store.save_user_preferences(db, user.id, payload)


@public_router.get("/public", response_model=PublicSettings)
def public_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return settings_store.public_settings(db)


@public_router.get("/options")
def settings_options(user: User = Depends(get_current_user)):
    """What the settings screen may offer, from the backend that owns the lists.

    The languages, transport modes and units all already exist on the server.
    Repeating them in the interface is how two lists drift apart, so the screen
    asks instead.
    """
    return {
        "languages": list(SUPPORTED_LANGUAGES),
        "modalities": list(MODALITIES),
        "units": [{"code": unit.code, "symbol": unit.symbol} for unit in UNITS.values()],
    }


@router.get("/instance", response_model=InstanceSettings)
def instance_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return settings_store.redacted(settings_store.instance_settings(db))


@router.put("/instance", response_model=InstanceSettings)
def save_instance_settings(
    request: Request,
    payload: InstanceSettings,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    before = settings_store.instance_settings(db).model_dump()
    stored = settings_store.save_instance_settings(db, payload)
    # The keys that changed and nothing of what they changed to: the mail
    # password is in here, and so is everything an outsider would like.
    changed = sorted(key for key, value in stored.model_dump().items()
                     if before.get(key) != value)
    if changed:
        audit.record(db, "settings.changed", actor=admin, target=("settings", "instance"),
                     summary=", ".join(changed), request=request)
    return settings_store.redacted(stored)


@router.get("/instance/history")
def history_counts(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """What switching the history off would destroy, for the confirmation."""
    return history.kept_counts(db)


@router.post("/instance/history/discard")
def discard_history(
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete every kept shipment and trip, so the history may be switched
    off. The screen asks first and names the counts; this is the answer."""
    counts = history.discard_kept(db)
    audit.record(db, "settings.history_discarded", actor=admin,
                 target=("settings", "history"),
                 summary=f"{counts['shipments']} shipment(s), {counts['trips']} trip(s)",
                 request=request)
    return {"ok": True, **counts}


@router.post("/instance/mail-test", response_model=MailTestResult)
def send_test_mail(
    payload: MailTestRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Prove the mail settings work, using the settings as they are stored.

    Deliberately not "test these values I am about to save": a test that
    passes on unsaved values and then fails on the saved ones would be worse
    than no test. Save first, then send.

    The recipient defaults to the administrator asking — the person who will
    know within seconds whether it arrived.
    """
    to = (payload.to or "").strip() or (admin.email or "")
    current = settings_store.instance_settings(db)
    try:
        mail.send_test(current, to)
    except mail.MailError as exc:
        # A refused password or an unreachable host is a fact about the
        # configuration, not a server fault: 400, with what the server said.
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MailTestResult(ok=True, to=to)


@router.get("/organisation", response_model=OrganisationSettings)
def organisation_settings(user: User = Depends(require_manager), db: Session = Depends(get_db)):
    return OrganisationSettings(**{key: getattr(settings_store.instance_settings(db), key)
                                   for key in OrganisationSettings.model_fields})


@router.put("/organisation", response_model=OrganisationSettings)
def save_organisation_settings(request: Request, payload: OrganisationSettings,
                               user: User = Depends(require_manager), db: Session = Depends(get_db)):
    current = settings_store.instance_settings(db)
    values = payload.model_dump()
    settings_store.save_instance_settings(db, current.model_copy(update=values))
    audit.record(db, "settings.changed", actor=user, target=("settings", "organisation"),
                 summary=", ".join(sorted(values)), request=request)
    return payload
