import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.messages import error
from app.core.ratelimit import limiter
from app.core.security import (
    create_access_token,
    create_challenge_token,
    decode_access_token_claims,
    decode_challenge_token,
    hash_password,
    token_matches_password,
    verify_password,
)
from app.models.user import User
from app.schemas.users import (
    LoginRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    TwoFactorConfirm,
    TwoFactorLogin,
    TwoFactorSetup,
    TwoFactorStart,
    TwoFactorStatus,
    UserOut,
)
from app.services import audit, mail, mail_templates, password_reset, two_factor
from app.services.settings_store import instance_settings, language_for

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def cookie_is_secure(request: Request, settings: Settings | None = None) -> bool:
    """Determine the Secure flag from explicit config or the actual request."""
    settings = settings or get_settings()
    if settings.cookie_secure is not None:
        return settings.cookie_secure
    if request.url.scheme.lower() == "https":
        return True
    if settings.trusted_proxy_headers:
        forwarded = request.headers.get("x-forwarded-proto", "")
        return forwarded.split(",", 1)[0].strip().lower() == "https"
    return False


def _set_access_cookie(
    response: Response,
    token: str,
    settings: Settings,
    request: Request | None = None,
    expire_minutes: int | None = None,
) -> None:
    secure = cookie_is_secure(request, settings) if request is not None else settings.secure_cookies
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=secure,
        # The cookie must not outlive the token it carries, or the browser keeps
        # sending a session the server has already stopped accepting.
        max_age=(expire_minutes or settings.access_token_expire_minutes) * 60,
        path="/",
    )


def _clear_access_cookie(
    response: Response,
    settings: Settings,
    request: Request | None = None,
) -> None:
    secure = cookie_is_secure(request, settings) if request is not None else settings.secure_cookies
    response.delete_cookie(
        key="access_token",
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


def _sign_in(request: Request, response: Response, db: Session, user: User,
             how: str = "password") -> dict:
    """Hand out the session cookie. The last step of every way in."""
    expire_minutes = instance_settings(db).session_timeout_minutes
    token = create_access_token(
        user.username, password_hash=user.password_hash, expires_minutes=expire_minutes
    )
    _set_access_cookie(response, token, get_settings(), request=request,
                       expire_minutes=expire_minutes)
    audit.record(db, "auth.login", actor=user, summary=how, request=request)
    return {"user": UserOut.model_validate(user)}


def _refused(db: Session, request: Request, username: str, why: str) -> None:
    """A sign-in that did not happen, and why — the one line an
    administrator wants when somebody is guessing at a name."""
    audit.record(db, "auth.login_failed", actor_username=username, summary=why,
                 request=request)


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        _refused(db, request, payload.username,
                 "unknown name" if not user else "wrong password")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.active:
        _refused(db, request, user.username, "inactive account")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")

    if two_factor.is_active(db, user.id):
        return _challenge_for(db, user)

    return _sign_in(request, response, db, user)


def _challenge_for(db: Session, user: User) -> dict:
    """The half-finished sign-in: password accepted, factor still to come.

    The challenge says that and nothing more — it is refused everywhere a
    session is expected, so it cannot be used as a way in by itself.
    """
    enrolment = two_factor.enrolment_for(db, user.id)
    current = instance_settings(db)
    mailed = False
    if enrolment.method == "email" and mail.is_configured(current):
        code = two_factor.issue_email_code(db, user.id)
        message = mail_templates.sign_in_code_message(
            language_for(db, user), code, two_factor.EMAIL_CODE_TTL_MINUTES)
        try:
            mail.send(current, user.email, message.subject, message.text,
                      html=message.html)
            mailed = True
        except mail.MailError as exc:
            # Say so: somebody standing at a sign-in screen waiting for a
            # message that will never arrive is worse than an error.
            logger.warning("Could not send the sign-in code for %s: %s",
                           user.username, exc)
    return {
        "two_factor_required": True,
        "method": enrolment.method,
        "code_sent": mailed,
        "challenge": create_challenge_token(user.username, user.password_hash),
    }


@router.post("/login/two-factor")
@limiter.limit("10/minute")
def login_two_factor(
    request: Request,
    payload: TwoFactorLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    """The second half of a sign-in: the code, or a recovery code."""
    claims = decode_challenge_token(payload.challenge)
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Start signing in again.")
    user = db.query(User).filter(User.username == claims["sub"]).first()
    if not user or not user.active:
        _refused(db, request, claims["sub"], "inactive account")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User inactive")
    # The password may have changed since the challenge was handed out — a
    # reset in another window, say. The fingerprint says so.
    if not token_matches_password(claims, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Start signing in again.")
    if not two_factor.verify(db, user, payload.code):
        _refused(db, request, user.username, "wrong code")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="That code is not right.")
    return _sign_in(request, response, db, user,
                    how=two_factor.enrolment_for(db, user.id).method)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db),
           access_token: str | None = Cookie(default=None, alias="access_token")):
    # Whoever the cookie says, if it still says anybody: signing out with an
    # expired session is allowed and simply goes unattributed.
    if access_token:
        claims = decode_access_token_claims(access_token)
        name = (claims or {}).get("sub") or ""
        if name:
            audit.record(db, "auth.logout", actor_username=name, request=request)
    _clear_access_cookie(response, get_settings(), request=request)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Who is signed in, and whether they still owe this installation a
    second factor. The screen sends them to set one up rather than letting
    them find out at the next sign-in."""
    policy = instance_settings(db).two_factor_policy
    active = two_factor.is_active(db, user.id)
    return {
        "user": UserOut.model_validate(user),
        "admin_ready": True,
        "two_factor_active": active,
        "two_factor_required": two_factor.required_for(user, policy) and not active,
    }


@router.get("/setup-status")
def setup_status(db: Session = Depends(get_db)):
    has_admin = db.query(User).filter(User.role == "admin").first() is not None
    return {"has_admin": has_admin}


def _public_base_url(request: Request, settings_row) -> str:
    """Where to point the links in outgoing mail.

    The configured address wins, because only an administrator knows what
    the outside world calls this installation. Without one the request is
    read — including the proxy's own headers when those are trusted, which
    is the difference between a working link and one pointing at an
    internal container name.
    """
    configured = (settings_row.public_url or "").strip()
    if configured:
        return configured.rstrip("/")
    scheme = request.url.scheme
    host = request.url.netloc
    if get_settings().trusted_proxy_headers:
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        forwarded_host = request.headers.get("x-forwarded-host", "")
        if forwarded_proto:
            scheme = forwarded_proto.split(",", 1)[0].strip()
        if forwarded_host:
            host = forwarded_host.split(",", 1)[0].strip()
    return f"{scheme}://{host}"


@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(
    request: Request,
    payload: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """Ask for a reset link.

    The answer never changes. Whether the account exists, whether it is
    active, whether it has an address, whether the mail server accepted the
    message: none of it is visible here, or this form becomes a way to
    enumerate who has an account, one guess at a time. What went wrong is
    written to the log, where the administrator can see it and an outsider
    cannot.
    """
    user = password_reset.find_account(db, payload.identifier)
    current = instance_settings(db)
    if user is not None and mail.is_configured(current):
        token = password_reset.issue(db, user)
        link = password_reset.link_for(_public_base_url(request, current), token)
        message = mail_templates.reset_message(
            language_for(db, user), user.username, link,
            password_reset.TOKEN_TTL_MINUTES)
        try:
            mail.send(current, user.email, message.subject, message.text,
                      html=message.html)
        except mail.MailError as exc:
            logger.warning("Could not send the reset mail for %s: %s",
                           user.username, exc)
    elif user is not None:
        logger.warning(
            "%s asked for a password reset, but no mail server is configured",
            user.username)
    return {"ok": True}


@router.get("/reset-password/check")
@limiter.limit("30/minute")
def reset_password_check(request: Request, token: str = "",
                         db: Session = Depends(get_db)):
    """Whether this link can still be used.

    Asked before the form is drawn. A link that has already been spent used
    to look exactly like a fresh one until somebody had chosen a password,
    typed it twice and pressed the button — and only then learnt it was too
    late. Saying so up front costs one request and saves that.

    It says no more than yes or no: which account the token belongs to, and
    whether it is unknown, expired or spent, are all differences that only
    help somebody guessing.
    """
    return {"valid": password_reset.redeem(db, token) is not None}


@router.post("/reset-password")
@limiter.limit("10/minute")
def reset_password(
    request: Request,
    payload: PasswordResetConfirm,
    response: Response,
    db: Session = Depends(get_db),
):
    """Spend a reset link and set the new password.

    Unknown, expired and already-used tokens get one and the same answer:
    the difference between them is only useful to somebody guessing.
    """
    user = password_reset.redeem(db, payload.token)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="This reset link is no longer valid. Ask for a new one.")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    password_reset.spend(db, payload.token)
    audit.record(db, "auth.password_reset", actor=user, request=request)

    # Signed in straight away. Holding the link is proof of the mailbox, and
    # the password was just chosen on this screen: sending somebody back to a
    # sign-in form to retype what they typed a second ago proves nothing to
    # anybody. Every *other* session signed in with the old password still
    # stops working — the token fingerprint follows the password hash.
    if two_factor.is_active(db, user.id):
        # A second factor is not waived by a mailbox. The password half is
        # done; the other half is still owed.
        return _challenge_for(db, user)
    return _sign_in(request, response, db, user)


@router.post("/change-password")
def change_password(
    request: Request,
    payload: PasswordChange,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.password_hash):
        raise error(400, "auth.current_password_incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    audit.record(db, "auth.password_changed", actor=user, request=request)
    _clear_access_cookie(response, get_settings(), request=request)
    return {"ok": True, "reauthenticate": True}


# --- the second factor, for the person who owns the account -----------------


@router.get("/two-factor", response_model=TwoFactorStatus)
def two_factor_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = two_factor.enrolment_for(db, user.id)
    policy = instance_settings(db).two_factor_policy
    return TwoFactorStatus(
        active=bool(row and row.confirmed),
        method=row.method if row and row.confirmed else "",
        required=two_factor.required_for(user, policy),
        recovery_codes_left=two_factor.unused_recovery_codes(db, user.id),
    )


@router.post("/two-factor/start", response_model=TwoFactorSetup)
def two_factor_start(
    payload: TwoFactorStart,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Begin setting up a second factor. Nothing changes about signing in
    until the first code has been checked."""
    current = instance_settings(db)
    if payload.method == "email" and not mail.is_configured(current):
        raise HTTPException(
            status_code=400,
            detail="Codes by e-mail need a mail server. An administrator sets "
                   "one under Settings, Administration, Mail server.")

    try:
        row = two_factor.start_enrolment(db, user, payload.method)
    except two_factor.AlreadyEnrolled as exc:
        raise HTTPException(
            status_code=400,
            detail="A second factor is already switched on. Switch it off first, "
                   "which needs a working code.") from exc
    if payload.method == "totp":
        uri = two_factor.provisioning_uri(user, row.secret)
        return TwoFactorSetup(method="totp", secret=row.secret,
                              qr_svg=two_factor.qr_svg(uri))

    code = two_factor.issue_email_code(db, user.id)
    message = mail_templates.sign_in_code_message(
        language_for(db, user), code, two_factor.EMAIL_CODE_TTL_MINUTES)
    try:
        mail.send(current, user.email, message.subject, message.text,
                  html=message.html)
    except mail.MailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TwoFactorSetup(method="email", code_sent=True)


@router.post("/two-factor/confirm")
@limiter.limit("10/minute")
def two_factor_confirm(
    request: Request,
    payload: TwoFactorConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Prove the factor works, and get the recovery codes.

    The codes are returned once and never again — only their hashes stay
    behind. Somebody who loses both their phone and these codes needs an
    administrator, which is the honest trade for not keeping a back door.
    """
    row = two_factor.enrolment_for(db, user.id)
    if row is None:
        raise HTTPException(status_code=400, detail="Nothing is being set up.")
    ok = (two_factor.verify_totp(row.secret, payload.code) if row.method == "totp"
          else two_factor.verify_email_code(db, user.id, payload.code))
    if not ok:
        raise HTTPException(status_code=400, detail="That code is not right.")
    codes = two_factor.confirm_enrolment(db, user)
    audit.record(db, "auth.two_factor_enabled", actor=user, summary=row.method,
                 request=request)
    return {"ok": True, "recovery_codes": codes}


@router.post("/two-factor/recovery-codes")
@limiter.limit("10/minute")
def two_factor_new_recovery_codes(
    request: Request,
    payload: TwoFactorConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fresh codes, after proving possession of the existing second factor.

    A session alone must not be enough to mint a replacement second factor:
    that would let a stolen session bypass the proof required to disable it.
    """
    if not two_factor.is_active(db, user.id):
        raise error(400, "auth.two_factor_inactive")
    if not two_factor.verify(db, user, payload.code):
        raise error(400, "auth.two_factor_invalid_code")
    codes = two_factor.replace_recovery_codes(db, user)
    audit.record(db, "auth.recovery_codes_replaced", actor=user, request=request)
    return {"recovery_codes": codes}


@router.post("/two-factor/send-code")
@limiter.limit("5/minute")
def two_factor_send_code(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mail a fresh code to somebody who is already signed in.

    Needed to switch the mail method *off*: turning it off asks for a code,
    and with this method a code only exists once one has been sent. Without
    this the setting could be switched on and never off again.
    """
    row = two_factor.enrolment_for(db, user.id)
    if row is None or not row.confirmed or row.method != "email":
        raise HTTPException(
            status_code=400,
            detail="This account does not use codes by e-mail.")
    current = instance_settings(db)
    if not mail.is_configured(current):
        raise HTTPException(status_code=400,
                            detail="No mail server is configured.")
    code = two_factor.issue_email_code(db, user.id)
    message = mail_templates.sign_in_code_message(
        language_for(db, user), code, two_factor.EMAIL_CODE_TTL_MINUTES)
    try:
        mail.send(current, user.email, message.subject, message.text,
                  html=message.html)
    except mail.MailError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@router.delete("/two-factor")
@limiter.limit("10/minute")
def two_factor_disable(
    request: Request,
    payload: TwoFactorConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Switch it off, which needs a working code — otherwise a borrowed
    session is enough to strip the very protection it should be facing."""
    policy = instance_settings(db).two_factor_policy
    if two_factor.required_for(user, policy):
        raise HTTPException(
            status_code=400,
            detail="This installation requires two-factor verification for "
                   "your account. An administrator can change that.")
    if not two_factor.verify(db, user, payload.code):
        raise HTTPException(status_code=400, detail="That code is not right.")
    two_factor.disable(db, user.id)
    audit.record(db, "auth.two_factor_disabled", actor=user, request=request)
    return {"ok": True}
