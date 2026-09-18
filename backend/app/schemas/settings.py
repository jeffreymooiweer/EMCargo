"""What can be set, and within which bounds.

Two audiences, two models. :class:`UserPreferences` is what one person chose for
themselves and nobody else sees. :class:`InstanceSettings` is what the
administrator chose for the whole installation, and it is the one that can
switch off outbound network traffic — so every field here is validated rather
than trusted.

Every field carries a default. That is what makes the JSON storage in
``app.models.settings`` upgrade-proof: a database written before a setting
existed simply lacks the key, and the default fills in.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.languages import DEFAULT as DEFAULT_LANGUAGE
from app.core.languages import SUPPORTED as SUPPORTED_LANGUAGES

#: The transport modes the wizard offers, mirrored from ``MODALITIES`` in
#: ``frontend/src/pages/ModalitySelectPage.tsx``. An empty string means "ask me
#: every time", which stays the default: guessing wrong sends someone into the
#: wrong set of forms.
MODALITIES = ("road", "rail", "sea", "inland", "air", "multimodal")

ThemeChoice = Literal["light", "dark", "system"]

#: Who has to sign in with a second factor. "off" leaves it to each person,
#: "admins" covers the accounts that can change other accounts, "everyone"
#: covers the lot. Off by default: switching a security requirement on for
#: an installation is an administrator's decision, not an upgrade's.
TwoFactorPolicy = Literal["off", "admins", "everyone"]

#: How the connection to the mail server is encrypted. "starttls" is the
#: usual port 587, "ssl" the implicit TLS of port 465, and "none" exists for
#: a relay on the local network that expects no encryption at all.
MailSecurity = Literal["starttls", "ssl", "none"]

#: Deliberately not RFC 5322. The purpose is to catch a hostname or a name
#: typed into an address field, not to arbitrate what a mail server accepts —
#: the server itself does that, and its answer is shown as it comes.
EMAIL_ADDRESS = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")

#: A drawn signature is a PNG data URL. The cap is deliberate — the pad produces
#: roughly 10-30 kB, so anything past a quarter of a megabyte is not a signature.
MAX_SIGNATURE_CHARS = 262_144


class UserPreferences(BaseModel):
    """One user's own settings.

    Before v1.45.0 the language and the theme lived in ``localStorage``. That
    worked until the same person opened the app on a second device and found it
    back in Dutch on a white background. Both now travel with the account; the
    browser keeps a copy only so the first paint does not flash.
    """

    #: Empty means: follow the instance default (and, failing that, the browser).
    language: str = ""
    theme: ThemeChoice = "dark"

    #: Skip the transport-mode tiles and open this mode straight away. Empty
    #: keeps the tiles, which is right for anyone who ships by more than one mode.
    default_modality: str = ""

    #: The unit a freshly added line starts with. Used to be the hard-coded
    #: string "stuks" — a Dutch word that reached German and French screens too.
    default_unit: str = "pcs"

    #: Whether the details below are filled in for you at all. Off means they are
    #: kept but never applied, which beats deleting them to stop the prefill.
    prefill_documents: bool = True

    #: The consignor is nearly always the same company for the same person, and
    #: it is retyped on every single shipment.
    consignor_name: str = ""
    consignor_address: str = ""
    consignor_contact: str = ""

    #: Frequently, though not always, the same. Optional on every form.
    carrier_name: str = ""
    loading_point: str = ""

    #: The 24-hour emergency telephone number. IMDG 5.4.1.5.11 and the IATA DGR
    #: shipper's declaration both want it, it never changes, and it was retyped
    #: for every consignment.
    emergency_contact: str = ""

    #: A signature drawn once, kept for reuse. Opt-in by being empty until the
    #: user saves one, and described in ``docs/privacy.md``.
    signature_image: str = Field(default="", max_length=MAX_SIGNATURE_CHARS)

    #: The version whose release notes this user has already seen. The
    #: what's-new card shows the entries between this and the running version,
    #: then writes the running version here. Empty means no marker yet — a new
    #: account, or one from before v1.125.0 — and shows nothing rather than
    #: the whole history.
    last_seen_version: str = ""

    @field_validator("language")
    @classmethod
    def _known_language(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value and value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unknown language: {value}")
        return value

    @field_validator("default_modality")
    @classmethod
    def _known_modality(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value and value not in MODALITIES:
            raise ValueError(f"unknown transport mode: {value}")
        return value

    @field_validator("last_seen_version")
    @classmethod
    def _version_like(cls, value: str) -> str:
        value = (value or "").strip()
        if value and not re.fullmatch(r"\d+\.\d+\.\d+", value):
            raise ValueError("not a version number")
        return value

    @field_validator("signature_image")
    @classmethod
    def _looks_like_an_image(cls, value: str) -> str:
        value = (value or "").strip()
        if value and not value.startswith("data:image/"):
            raise ValueError("signature must be an image data URL")
        return value

    @field_validator(
        "consignor_name",
        "consignor_address",
        "consignor_contact",
        "carrier_name",
        "loading_point",
        "emergency_contact",
        "default_unit",
    )
    @classmethod
    def _trimmed(cls, value: str) -> str:
        return (value or "").strip()


class InstanceSettings(BaseModel):
    """What the administrator decides for everyone.

    The defaults are read from the environment variables that already governed
    these choices, so an installation that never opens this screen keeps behaving
    exactly as its ``.env`` says. Saving here takes precedence from then on —
    and, unlike an environment variable, without restarting the container.
    """

    #: The language a user who has not chosen one gets, and the language of the
    #: login screen.
    default_language: str = DEFAULT_LANGUAGE
    default_theme: ThemeChoice = "dark"

    #: Address autocomplete is the only outbound request the app makes while
    #: someone is using it. On an air-gapped or privacy-sensitive installation
    #: this switch is the point of this whole screen.
    address_lookup_enabled: bool = True
    address_api_url: str = "https://photon.komoot.io/api"
    address_timeout_seconds: float = Field(default=8.0, ge=1.0, le=60.0)

    #: The other outbound request, made at startup only. Turning it off takes
    #: effect the next time the container starts.
    catalog_auto_sync: bool = True

    #: The third and last outbound request: asking GitHub whether a newer
    #: release exists, when an administrator opens the screen that could act
    #: on the answer. The container cannot update itself either way — this
    #: only decides whether EMCargo may *ask*.
    update_check_enabled: bool = True

    #: The UN card download. Some installations would rather hand out their own
    #: instruction cards than these.
    un_cards_enabled: bool = True

    #: Whether documents may carry a QR code that opens this installation's UN
    #: cards for the substances on them.
    #:
    #: Off by default, and deliberately: turning it on opens **one route that
    #: needs no sign-in**, because the people a QR on a transport document is
    #: for — the driver, the warehouse, the responder at the roadside — do not
    #: have accounts, and a code that asks them to log in is a code that does
    #: nothing. What it serves is the regulation's own reference material for
    #: the UN numbers in the link, which the document already prints in plain
    #: text and larger; it never reaches a consignment, a party or a quantity.
    #: Still, a new door is a new door, so the administrator opens it rather
    #: than finding it open.
    card_links_enabled: bool = False

    #: How long a session stays valid. Eight hours is one working day.
    session_timeout_minutes: int = Field(default=480, ge=15, le=10_080)
    #: How long the administrator's audit log keeps a line, in days. Applied
    #: at start-up and whenever the log is read; a year by default.
    audit_retention_days: int = Field(default=365, ge=1, le=3650)

    #: Whether this installation keeps the shipments it makes — the shipment
    #: history, with the shipments page, the trips, the address book, the
    #: articles library and the safety adviser's report beside it. Off by
    #: default: a shipment drawn up is a shipment forgotten. Switching it
    #: *off* with kept shipments in the table is refused until the
    #: administrator has them deleted first, so a table is never kept while
    #: the interface claims it does not exist.
    history_enabled: bool = True
    dg_review_enabled: bool = True
    super_user_dgsa_enabled: bool = False

    #: Used as the consignor for users who filled in nothing of their own, so a
    #: new colleague starts with the company already on the form.
    organisation_name: str = ""
    organisation_address: str = ""

    #: What the screen calls itself: in the header, on the sign-in page and in
    #: the browser tab. Empty means EMCargo. Separate from the organisation
    #: name above on purpose — that one goes on a document as the consignor,
    #: this one goes on the door, and a shipper's legal name is not always
    #: what it wants over its tools. The logo and the tile images beside it
    #: are files rather than settings; see ``services/branding.py``.
    brand_name: str = Field(default="", max_length=80)

    #: Who must have a second factor. Someone who does not yet have one is
    #: sent to set one up after signing in, rather than being locked out at
    #: the door of an account they can still reach today.
    two_factor_policy: TwoFactorPolicy = "off"

    #: The address people reach this installation on, used to build the links
    #: in outgoing mail. Empty means: read it from the request, which is right
    #: whenever the browser talks to EMCargo directly and wrong behind a
    #: reverse proxy that does not pass its own host on.
    public_url: str = ""

    #: The mail server. Off until an administrator fills it in: an application
    #: that silently knows how to send mail is a surprise nobody asked for.
    mail_enabled: bool = False
    mail_host: str = ""
    mail_port: int = Field(default=587, ge=1, le=65535)
    mail_security: MailSecurity = "starttls"
    mail_username: str = ""
    #: Write-only in practice. The API redacts it on the way out and keeps the
    #: stored one when an empty value is saved, so an administrator can change
    #: the host without retyping the password — and so the password does not
    #: travel to a browser on every visit to the settings screen.
    mail_password: str = ""
    #: Derived on read, never trusted from input: whether a password is stored.
    #: Without it a redacted field is indistinguishable from an empty one.
    mail_password_set: bool = False
    #: The envelope sender. Most relays refuse a sender they do not own, so
    #: this is asked rather than invented from the hostname.
    mail_from: str = ""
    mail_from_name: str = ""
    mail_timeout_seconds: float = Field(default=15.0, ge=1.0, le=120.0)

    @field_validator("public_url")
    @classmethod
    def _public_http_url(cls, value: str) -> str:
        value = (value or "").strip().rstrip("/")
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("the address must start with http:// or https://")
        return value

    @field_validator("mail_host", "mail_username", "mail_from_name")
    @classmethod
    def _trimmed_mail(cls, value: str) -> str:
        return (value or "").strip()

    @field_validator("mail_from")
    @classmethod
    def _address_like(cls, value: str) -> str:
        value = (value or "").strip()
        if value and not EMAIL_ADDRESS.fullmatch(value):
            raise ValueError("sender must be an e-mail address")
        return value

    @model_validator(mode="after")
    def _sending_needs_a_server(self) -> "InstanceSettings":
        """Switching mail on without a server or sender would fail at the
        first message, at a moment nobody is watching. It fails here instead,
        where the administrator can see the field that is empty."""
        if self.mail_enabled:
            if not self.mail_host:
                raise ValueError("a mail server needs a host")
            if not self.mail_from:
                raise ValueError("a mail server needs a sender address")
        return self

    @field_validator("default_language")
    @classmethod
    def _known_language(cls, value: str) -> str:
        value = (value or "").strip().lower()
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"unknown language: {value}")
        return value

    @field_validator("address_api_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        value = (value or "").strip()
        if not value.startswith(("http://", "https://")):
            raise ValueError("address API must be an http(s) URL")
        return value

    @field_validator("organisation_name", "organisation_address", "brand_name")
    @classmethod
    def _trimmed(cls, value: str) -> str:
        return (value or "").strip()


class MailTestRequest(BaseModel):
    """Where the test message goes. Empty means: to the administrator who
    pressed the button, which is the address they can check fastest."""

    to: str = ""

    @field_validator("to")
    @classmethod
    def _address_like(cls, value: str) -> str:
        value = (value or "").strip()
        if value and not EMAIL_ADDRESS.fullmatch(value):
            raise ValueError("recipient must be an e-mail address")
        return value


class MailTestResult(BaseModel):
    ok: bool
    to: str


class PublicSettings(BaseModel):
    """The part of the instance settings every signed-in user may know.

    Deliberately narrow. The wizard needs to know whether to offer the UN card
    download and whether address lookup will answer; it has no business knowing
    the session lifetime or which geocoder is configured.
    """

    default_language: str
    default_theme: ThemeChoice
    address_lookup_enabled: bool
    un_cards_enabled: bool
    card_links_enabled: bool
    organisation_name: str
    organisation_address: str
    #: Whether this installation keeps its shipments. The export step offers
    #: to keep one and the menu shows the shipments page only when it does.
    history_enabled: bool = True
    dg_review_enabled: bool = True
    super_user_dgsa_enabled: bool = False
    #: Whether the export step may offer to mail the documents. Only that a
    #: mail server exists, never which one or under whose name.
    mail_enabled: bool


class OrganisationSettings(BaseModel):
    """Strict allowlist for operational managers; no secrets or access policy."""
    model_config = {"extra": "forbid"}
    organisation_name: str = Field(default="", max_length=255)
    organisation_address: str = Field(default="", max_length=2000)
    default_language: str = DEFAULT_LANGUAGE
    default_theme: ThemeChoice = "dark"

    _known_language = field_validator("default_language")(InstanceSettings._known_language.__func__)
