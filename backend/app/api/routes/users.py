import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File
from sqlalchemy.orm import Session, selectinload

from app.api.routes.auth import _public_base_url
from app.core.database import get_db
from app.core.deps import get_current_user, require_manager
from app.core.messages import error
from app.core.security import hash_password
from app.models.user import Department, User, UserAvatar, UserProfile
from app.schemas.users import (
    UserCreate,
    UserCreateResult,
    UserOut,
    UserRole,
    UserUpdate,
    PersonalProfile,
)
from app.services import audit, avatars, mail, mail_templates, password_reset, two_factor
from app.services.settings_store import instance_settings, language_for

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/profile", response_model=PersonalProfile)
def my_profile(user: User = Depends(get_current_user)):
    return user.personal_profile or PersonalProfile()


@router.put("/me/profile", response_model=UserOut)
def save_my_profile(payload: PersonalProfile, request: Request,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The signed-in account owns the target; payloads cannot choose another user."""
    if user.personal_profile is None:
        user.personal_profile = UserProfile(**payload.model_dump())
    else:
        for name, value in payload.model_dump().items():
            setattr(user.personal_profile, name, value)
    db.commit()
    db.refresh(user)
    audit.record(db, "user.updated", summary="personal profile", actor=user,
                 target=("user", user.id), request=request)
    return user


@router.post("/me/avatar", response_model=UserOut)
def upload_my_avatar(request: Request, file: UploadFile = File(...),
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = file.file.read(avatars.MAX_UPLOAD_BYTES + 1)
    image, etag = avatars.normalize(data)
    if user.avatar is None:
        user.avatar = UserAvatar(image=image, etag=etag)
    else:
        user.avatar.image, user.avatar.etag = image, etag
    db.commit()
    db.refresh(user)
    audit.record(db, "user.updated", summary="avatar", actor=user, target=("user", user.id), request=request)
    return user


@router.delete("/me/avatar", response_model=UserOut)
def delete_my_avatar(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.avatar = None
    db.commit()
    db.refresh(user)
    audit.record(db, "user.updated", summary="avatar removed", actor=user, target=("user", user.id), request=request)
    return user


@router.get("/{user_id}/avatar")
def get_avatar(user_id: int, request: Request, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    # Photos are for their owner and the administrator's user directory.
    # Authorize before cache validation, including responses without a body.
    if user.id != user_id and user.role not in {"admin", "super_user"}:
        raise error(404, "avatar.not_found")
    avatar = db.get(UserAvatar, user_id)
    if avatar is None:
        raise error(404, "avatar.not_found")
    headers = {"ETag": f'"{avatar.etag}"', "Cache-Control": "private, no-cache",
               "X-Content-Type-Options": "nosniff"}
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=304, headers=headers)
    return Response(avatar.image, media_type="image/webp", headers=headers)


def _ensure_manageable(actor: User, target: User | None = None, role: str | None = None) -> None:
    # Resetting a specialist's password also grants report/approval access.
    # Super Users therefore cannot manage either privileged role, including
    # their own promotion or the creation of a privileged replacement account.
    if actor.role != "admin" and (
        role in {"admin", "dg_specialist"}
        or (target is not None and target.role in {"admin", "dg_specialist"})
    ):
        raise error(403, "permissions.protected_account")


def _is_active_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN.value and bool(user.active)


def _active_admin_count(db: Session) -> int:
    return db.query(User).filter(User.role == UserRole.ADMIN.value, User.active.is_(True)).count()


def _ensure_update_is_safe(
    target: User,
    acting_admin: User,
    next_role: str,
    next_active: bool,
    active_admin_count: int,
) -> None:
    _ensure_manageable(acting_admin, target, next_role)
    removes_admin_access = next_role != acting_admin.role or not next_active

    if target.id == acting_admin.id and removes_admin_access:
        raise HTTPException(status_code=400, detail="Cannot deactivate or demote yourself")

    if _is_active_admin(target) and removes_admin_access and active_admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last active administrator")


def _ensure_delete_is_safe(target: User, acting_admin: User, active_admin_count: int) -> None:
    _ensure_manageable(acting_admin, target)
    if target.id == acting_admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if _is_active_admin(target) and active_admin_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove the last active administrator")


@router.get("", response_model=list[UserOut])
def list_users(admin: User = Depends(require_manager), db: Session = Depends(get_db)):
    # Batch avatar metadata only where it is displayed. Global eager loading
    # would add photo queries to shipment and trip ownership lookups too.
    return db.query(User).options(selectinload(User.avatar), selectinload(User.personal_profile)).order_by(User.id).all()


@router.post("", response_model=UserCreateResult)
def create_user(
    request: Request,
    payload: UserCreate,
    admin: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Make an account, optionally inviting its owner to set a password.

    With an invitation there is no password to type here at all: the new
    colleague chooses their own through the link, so it never travels by
    chat or note and the administrator never knows it. Until they do, the
    account carries an unguessable random hash — an account nobody can sign
    in to, rather than one with a password somebody might guess.
    """
    _ensure_manageable(admin, role=payload.role.value)
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username exists")

    current = instance_settings(db)
    invite = payload.send_welcome and mail.is_configured(current)
    if payload.password is None and not invite:
        raise HTTPException(
            status_code=400,
            detail="Give a password, or send an invitation so the account's "
                   "owner can choose one. That needs a mail server.")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password or secrets.token_urlsafe(32)),
        role=payload.role.value,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.record(db, "user.created", actor=admin, target=("user", user.id),
                 summary=f"{user.username} ({user.role})", request=request)

    result = UserCreateResult.model_validate(user, from_attributes=True)
    if not payload.send_welcome:
        return result
    if not invite:
        result.welcome_mail = "no_mail_server"
        return result

    token = password_reset.issue(db, user,
                                 ttl_minutes=password_reset.INVITE_TTL_MINUTES)
    link = password_reset.link_for(_public_base_url(request, current), token)
    # A brand-new account has no language of its own yet, so the
    # installation's default is what it gets. Deliberately not the
    # administrator's: they are not the reader.
    message = mail_templates.invite_message(
        language_for(db, user), user.username, link,
        password_reset.INVITE_TTL_MINUTES // (24 * 60))
    try:
        mail.send(current, user.email, message.subject, message.text,
                  html=message.html)
        result.welcome_mail = "sent"
    except mail.MailError as exc:
        # The account exists either way — deleting it again would be worse
        # than an administrator who now knows to pass the link on by hand.
        logger.warning("Could not send the invitation for %s: %s",
                       user.username, exc)
        result.welcome_mail = str(exc)
    return result


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    request: Request,
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    next_role = payload.role.value if payload.role is not None else user.role
    next_active = payload.active if payload.active is not None else bool(user.active)
    _ensure_update_is_safe(user, admin, next_role, next_active, _active_admin_count(db))

    if payload.email is not None:
        user.email = payload.email
    if payload.role is not None:
        user.role = payload.role.value
    if payload.active is not None:
        user.active = payload.active
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if "department_id" in payload.model_fields_set:
        # Null takes them out of their department; an id must be a real one.
        if payload.department_id is not None and db.get(Department, payload.department_id) is None:
            raise HTTPException(status_code=404, detail="No such department")
        user.department_id = payload.department_id
    db.commit()
    db.refresh(user)
    # Which fields, never their values: a new password is "password".
    changed = ", ".join(sorted(payload.model_fields_set)) or "nothing"
    audit.record(db, "user.updated", actor=admin, target=("user", user.id),
                 summary=f"{user.username}: {changed}", request=request)
    return user


@router.delete("/{user_id}/two-factor")
def clear_two_factor(
    request: Request,
    user_id: int,
    admin: User = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """Remove somebody's second factor: the phone is gone and the recovery
    codes with it.

    Deliberately available to any administrator rather than only to the
    account's owner — that is the whole point of a way back in. It is also
    why an installation should have more than one administrator.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_manageable(admin, user)
    two_factor.disable(db, user.id)
    logger.info("%s cleared the second factor of %s", admin.username, user.username)
    audit.record(db, "user.two_factor_cleared", actor=admin, target=("user", user.id),
                 summary=user.username, request=request)
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(request: Request, user_id: int, admin: User = Depends(require_manager),
                db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    _ensure_delete_is_safe(user, admin, _active_admin_count(db))
    name, gone_id = user.username, user.id
    # SQLite installations may not enforce foreign keys. Do not let a reused
    # account id inherit another person’s submitted review data.
    from app.models.dg_review import DgReview
    from app.models.shipment import Shipment
    db.query(DgReview).filter_by(created_by_id=user.id).update({DgReview.created_by_id: None})
    db.query(Shipment).filter_by(created_by_id=user.id, is_draft=True).delete()
    db.query(Shipment).filter_by(created_by_id=user.id).update({Shipment.created_by_id: None})
    db.query(Shipment).filter_by(work_owner_id=user.id).update({Shipment.work_owner_id: None})
    db.delete(user)
    db.commit()
    audit.record(db, "user.deleted", actor=admin, target=("user", gone_id),
                 summary=name, request=request)
    return {"ok": True}
