"""Resolve the authenticated account and enforce its access policy."""
from fastapi import Cookie, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.messages import ApiError
from app.core.security import (
    CHALLENGE_CLAIM,
    decode_access_token_claims,
    token_matches_password,
)
from app.models.user import User

#: What an account that owes this installation a second factor may still
#: reach: who it is, the second factor itself, its own preferences and the
#: public settings the screen is drawn from — enough to set the factor up
#: and to sign out, nothing to work with. Prefixes, matched against the path.
ENROLMENT_PATHS = (
    "/api/auth/me",
    "/api/auth/logout",
    "/api/auth/two-factor",
    "/api/settings/me",
    "/api/settings/public",
    "/api/settings/options",
)


def owes_second_factor(db: Session, user: User) -> bool:
    """Whether the installation's policy demands a second factor this
    account does not have."""
    from app.services import two_factor
    from app.services.settings_store import instance_settings

    policy = instance_settings(db).two_factor_policy
    return two_factor.required_for(user, policy) and not two_factor.is_active(db, user.id)


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    access_token: str | None = Cookie(default=None, alias="access_token"),
) -> User:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    claims = decode_access_token_claims(access_token)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if claims.get(CHALLENGE_CLAIM):
        # A half-finished sign-in, presented as a whole one. Without this the
        # second factor would be a formality: anybody could stop at the
        # challenge and use it as a session cookie.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Two-factor verification not finished")
    user = db.query(User).filter(User.username == claims["sub"]).first()
    if not user or not user.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    if not token_matches_password(claims, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    # A required second factor is required here, on every call, not only
    # mentioned at sign-in. Until v1.190.0 the screen asked and the server
    # let everything through regardless, so the policy was advice with a
    # stern face. The account is not locked out: it signs in, is sent to the
    # panel, and can reach nothing else until the factor is confirmed.
    if not request.url.path.startswith(ENROLMENT_PATHS) and owes_second_factor(db, user):
        raise ApiError(
            status.HTTP_403_FORBIDDEN, "auth.two_factor_required",
            "This installation requires two-factor verification for your account. "
            "Set it up under User settings, Security, before doing anything else")
    # Execution-only accounts must never inherit the broad access granted by
    # older routes merely because they successfully authenticated.
    from app.services.deliveries import execution_only
    if execution_only(db, user):
        prefixes = ("/api/deliveries/v1", "/api/auth", "/api/settings/me",
                    "/api/settings/public", "/api/settings/options")
        if not any(request.url.path == p or request.url.path.startswith(p + "/") for p in prefixes):
            from app.core.messages import error
            raise error(403, "delivery.permission")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")
    return user


def require_history(db: Session = Depends(get_db)) -> None:
    """The shipment history's routes exist only while an administrator has
    the history switched on. Off, they answer 404 like any address the
    installation does not have — the promise "nothing is kept" is enforced
    by what answers, not described in a setting somebody has to find."""
    from app.services.settings_store import history_enabled

    if not history_enabled(db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


def require_manager(user: User = Depends(get_current_user)) -> User:
    """Operational management never implies installation administration."""
    from app.core.messages import error
    if user.role not in {"admin", "super_user"}:
        raise error(403, "permissions.manager_required")
    return user


def require_dg_specialist(user: User = Depends(get_current_user)) -> User:
    from app.core.messages import error
    if user.role != "dg_specialist":
        raise error(403, "permissions.specialist_required")
    return user


def require_dgsa(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    from app.core.messages import error
    from app.services.settings_store import instance_settings
    if user.role in {"admin", "dg_specialist"}:
        return user
    if user.role == "super_user" and instance_settings(db).super_user_dgsa_enabled:
        return user
    raise error(403, "permissions.dgsa_required")
