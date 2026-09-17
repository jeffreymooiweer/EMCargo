"""What the shipments page and the export step exchange with the server."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas import DocumentBundleRequest
from app.schemas.cargo import CargoManifest


class ShipmentIn(BaseModel):
    """A shipment as the export step hands it over to be kept.

    The server builds the structured export itself from the parts, so the
    kept record is produced by the same code as the downloadable one and the
    two cannot disagree. The snapshot is the wizard's own state and is not
    read here; the bundle is kept for "the documents again".
    """

    cargo: CargoManifest | None = None
    expected_cargo_revision: int | None = Field(default=None, ge=0)
    dg_review_id: str | None = Field(default=None, max_length=36)
    modality: str = Field(default="", max_length=16)
    language: str = Field(default="nl", max_length=8)
    profiles: list[str] = Field(default_factory=list)
    #: The document fields as filled in.
    values: dict[str, Any] = Field(default_factory=dict)
    #: The calculated goods lines.
    lines: list[dict[str, Any]] = Field(default_factory=list)
    dangerous_goods: list[dict[str, Any]] | None = None
    #: The document keys that were selected.
    documents: list[str] = Field(default_factory=list)
    #: The bundle as the export step would send it; ``None`` when nothing was
    #: ready to bundle, in which case "the documents again" is not offered.
    bundle: DocumentBundleRequest | None = None
    #: The wizard's own state, opaque to the server.
    snapshot: dict[str, Any] = Field(default_factory=dict)
    #: Entry still in progress. A draft is kept so a reload does not lose it,
    #: and is not a kept shipment: saving the same row with this false is what
    #: makes it one.
    draft: bool = False


class ShipmentSummary(BaseModel):
    id: int
    reference: str
    modality: str
    language: str
    regulations: list[str]
    consignor_name: str
    consignee_name: str
    goods_count: int
    has_dangerous_goods: bool
    has_documents: bool
    #: Entry still in progress rather than a kept shipment.
    is_draft: bool = False
    cargo_revision: int = 0
    created_by: str
    #: Whose work this is: the keeper's department when it was kept.
    department_id: int | None = None
    department: str = ""
    created_at: datetime
    updated_at: datetime


class ShipmentDetail(ShipmentSummary):
    snapshot: dict[str, Any]
    export: dict[str, Any]


class ShipmentPage(BaseModel):
    items: list[ShipmentSummary]
    total: int
    page: int
    per_page: int
