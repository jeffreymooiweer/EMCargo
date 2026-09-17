from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.settings import EMAIL_ADDRESS
from app.schemas.cargo import CargoManifest


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "user"


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    role: str | None = None
    active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    active: bool

    class Config:
        from_attributes = True


class ParseRequest(BaseModel):
    text: str
    column_map: dict[str, int | None] | None = None
    has_header: bool = False
    input_language: str | None = None


class CalculateRequest(BaseModel):
    text: str | None = None
    lines: list[dict] | None = None
    column_map: dict[str, int | None] | None = None
    has_header: bool = False
    input_language: str | None = None
    output_language: str = "nl"
    mode: str = "continue"
    line_overrides: list[dict] | None = None


class UnCardsRequest(BaseModel):
    """The declared dangerous goods, and which regimes the journey touches.

    Cards exist per UN number *and* regime; the profiles decide which
    regimes' cards belong to this shipment. Empty means every regime the
    installed set holds.
    """

    dangerous_goods: list[dict] | None = None
    profiles: list[str] = []
    output_language: str = "nl"


class DocumentExportRequest(BaseModel):
    cargo: CargoManifest | None = None
    dg_review_id: str | None = Field(default=None, max_length=36)
    document_key: str
    values: dict = Field(default_factory=dict)
    lines: list[dict] = Field(default_factory=list)
    dangerous_goods: list[dict] | None = None
    output_language: str = "nl"
    signature_image: str | None = None
    #: Which regulations the consignment travels under. Only the documents that
    #: genuinely answer differently per regime read it — the package label sheet
    #: is the first, because the IMDG Code marks the proper shipping name on
    #: every package where the land regimes ask for it on Class 1 and Class 7
    #: only. An empty list is not "all of them": it means nothing was said, and
    #: a document that needs the answer says which regime it fell back on rather
    #: than presenting one mode's rule as every mode's.
    profiles: list[str] = Field(default_factory=list)
    #: The transport mode the wizard was in. Recorded by the structured export
    #: so a reader knows which regime's documents the consignment was drawn up
    #: for; no document derives anything from it.
    modality: str | None = None


class DocumentBundleRequest(BaseModel):
    """Everything the export step can hand over, in one archive.

    The documents ride along with their full payloads — the same shape the
    single export takes, so what the bundle produces is what the buttons
    produce. The UN cards and the instructions in writing are included for
    the declared goods on the journey's regimes; both are skipped without
    complaint when the shipment has no dangerous goods.
    """

    cargo: CargoManifest | None = None
    dg_review_id: str | None = Field(default=None, max_length=36)
    documents: list[DocumentExportRequest] = Field(default_factory=list)
    dangerous_goods: list[dict] | None = None
    profiles: list[str] = []
    output_language: str = "nl"
    include_un_cards: bool = True
    include_instructions: bool = True
    signature_image: str | None = None


class DocumentBundleMailRequest(BaseModel):
    """The bundle, and where to send it.

    The archive itself is described by the same model the download uses, so
    mailing cannot drift into producing a different set of papers.
    """

    bundle: DocumentBundleRequest
    #: A consignment's papers go to a carrier, a consignee, a planner —
    #: rarely to only one of them. Ten is a shipment, not a mailing list.
    to: list[str] = Field(min_length=1, max_length=10)
    subject: str = Field(default="", max_length=200)
    message: str = Field(default="", max_length=5000)

    @field_validator("to")
    @classmethod
    def _addresses(cls, value: list[str]) -> list[str]:
        cleaned = [address.strip() for address in value if address.strip()]
        if not cleaned:
            raise ValueError("give at least one recipient")
        for address in cleaned:
            if not EMAIL_ADDRESS.fullmatch(address):
                raise ValueError(f"not an e-mail address: {address}")
        return cleaned


class BundleMailResult(BaseModel):
    ok: bool
    to: list[str]
    filename: str


class ReferenceItemBase(BaseModel):
    canonical_name: str
    category: str = "electrical"
    reference_weight_kg: float
    reference_volume_m3: float | None = None
    aliases: list[str] = Field(default_factory=list)
    language_labels: dict = Field(default_factory=dict)
    notes: str | None = None
    active: bool = True


class ReferenceItemOut(ReferenceItemBase):
    id: int

    class Config:
        from_attributes = True
