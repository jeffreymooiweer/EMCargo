from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    DG_SPECIALIST = "dg_specialist"
    SUPER_USER = "super_user"
    SHIPMENT = "shipment"
    PLANNER = "planner"
    OPERATOR = "operator"
    RECIPIENT = "recipient"
    ASSESSOR = "assessor"
    EXTERNAL = "external"


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    #: Optional when an invitation is sent: the colleague then chooses their
    #: own password through the link, so it never travels by chat or note —
    #: and the administrator never knows it either.
    password: str | None = Field(default=None, min_length=8)
    role: UserRole = UserRole.USER
    send_welcome: bool = False


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: UserRole | None = None
    active: bool | None = None
    # An administrator setting a new password for someone who lost theirs.
    # Unlike PasswordChange there is no current_password: the admin does
    # not know it, which is the whole reason for the reset.
    password: str | None = Field(default=None, min_length=8)
    #: The department, or ``null`` to take somebody out of theirs. Read via
    #: ``model_fields_set``: absent means "leave it", null means "none".
    department_id: int | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    active: bool
    department_id: int | None = None
    avatar_url: str | None = None
    display_name: str = ""
    execution_only: bool = False


class PersonalProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)

    display_name: str = Field(default="", max_length=80)
    first_name: str = Field(default="", max_length=80)
    last_name: str = Field(default="", max_length=80)
    job_title: str = Field(default="", max_length=120)
    phone_number: str = Field(default="", max_length=40)


class UserCreateResult(UserOut):
    """The account, plus what became of the invitation.

    Named rather than silent: an administrator who ticked "send an
    invitation" has to know whether it went out — if it did not, the new
    colleague is waiting for a message that will never arrive.
    """

    #: "sent", "not_requested", "no_mail_server", or the mail server's own
    #: refusal, passed through as it came.
    welcome_mail: str = "not_requested"


class PasswordResetRequest(BaseModel):
    """Who forgot their password. A user name or an address — both are what
    people remember, and the answer is the same either way."""

    identifier: str = Field(default="", max_length=254)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=8)


class TwoFactorLogin(BaseModel):
    """The second half of a sign-in. ``code`` is a six-digit code or one of
    the recovery codes; the same field takes both, because somebody whose
    phone is in a canal should not have to find a different form."""

    challenge: str = Field(min_length=16, max_length=2048)
    code: str = Field(min_length=4, max_length=32)


class TwoFactorStart(BaseModel):
    method: str = Field(pattern="^(totp|email)$")


class TwoFactorConfirm(BaseModel):
    code: str = Field(min_length=4, max_length=32)


class TwoFactorStatus(BaseModel):
    active: bool
    method: str = ""
    required: bool = False
    recovery_codes_left: int = 0


class TwoFactorSetup(BaseModel):
    """What the setup screen needs. The secret is shown once, here, and the
    QR carries the same thing in a form a phone camera can read."""

    method: str
    secret: str = ""
    qr_svg: str = ""
    code_sent: bool = False
