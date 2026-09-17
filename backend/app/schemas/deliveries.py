"""Version one of the operational delivery interface; quantities are decimals."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator

Mode = Literal["road", "rail", "inland", "sea", "air"]
TaskRole = Literal["shipment", "planner", "operator", "recipient", "assessor"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LegIn(StrictModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    mode: Mode = "road"
    origin: str = Field(default="", max_length=500)
    destination: str = Field(default="", max_length=500)
    carrier: str = Field(default="", max_length=255)
    vehicle: str = Field(default="", max_length=120)
    reference: str = Field(default="", max_length=120)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    max_mass_tonnes: Decimal | None = Field(default=None, gt=0, le=1000000, allow_inf_nan=False)
    equipment_ids: list[int] = Field(default_factory=list, max_length=100)
    load_unit_id: str | None = Field(default=None, min_length=1, max_length=64)
    document_values: dict[str, dict[Annotated[str, Field(max_length=120)], Annotated[str, Field(max_length=4000)]]] = Field(default_factory=dict, max_length=2000)

    @model_validator(mode="after")
    def time_order(self):
        if any(value is not None and value.tzinfo is None for value in (self.planned_start, self.planned_end)):
            raise ValueError("A time zone is required")
        if self.planned_start and self.planned_end:
            if not self.planned_start.tzinfo or not self.planned_end.tzinfo or self.planned_end < self.planned_start:
                raise ValueError("Use time zones and an end after the start")
        return self


class AllocationIn(StrictModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    shipment_id: int = Field(gt=0)
    goods_id: str = Field(min_length=1, max_length=120)
    quantity: Decimal = Field(gt=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    leg_ids: list[str] = Field(min_length=1, max_length=100)
    unit_ids: list[Annotated[str, Field(min_length=1, max_length=64)]] | None = Field(default=None, max_length=10000)
    leg_quantities: dict[str, Annotated[Decimal, Field(gt=0, max_digits=20, decimal_places=6, allow_inf_nan=False)]] = Field(default_factory=dict, max_length=100)


class DeliveryIn(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    version: int | None = Field(default=None, ge=1)
    legs: list[LegIn] = Field(default_factory=list, max_length=100)
    allocations: list[AllocationIn] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def references(self):
        legs = {leg.id for leg in self.legs}
        if len(legs) != len(self.legs) or len({a.id for a in self.allocations}) != len(self.allocations):
            raise ValueError("Duplicate identifiers")
        for allocation in self.allocations:
            if len(set(allocation.leg_ids)) != len(allocation.leg_ids) or not set(allocation.leg_ids) <= legs:
                raise ValueError("Unknown or repeated transport part")
            if not set(allocation.leg_quantities) <= set(allocation.leg_ids):
                raise ValueError("Unknown quantity transport part")
            quantities = [allocation.leg_quantities.get(lid, allocation.quantity) for lid in allocation.leg_ids]
            if quantities[0] != allocation.quantity or any(after > before for before, after in zip(quantities, quantities[1:])):
                raise ValueError("Transport quantities cannot increase along an itinerary")
        return self


class ActionIn(StrictModel):
    language: Literal["nl", "en", "de", "fr"] = "en"
    version: int = Field(ge=1)
    action: Literal["plan", "unplan", "release", "start", "cancel", "close", "reopen"]
    reason: str = Field(default="", max_length=2000)


class ReviewIn(StrictModel):
    language: Literal["nl", "en", "de", "fr"] = "en"
    version: int = Field(ge=1)
    reason: str = Field(min_length=10, max_length=4000)
    document_ids: list[str] = Field(default_factory=list, max_length=100)


class ReceiptLine(StrictModel):
    allocation_id: str = Field(min_length=1, max_length=36)
    quantity: Decimal = Field(ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    damaged: Decimal = Field(default=Decimal(0), ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    refused: Decimal = Field(default=Decimal(0), ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)


class EventIn(StrictModel):
    version: int = Field(ge=1)
    request_id: str = Field(min_length=16, max_length=64)
    kind: Literal["load", "receipt", "correction", "resolution", "unpack"]
    recipient: str = Field(min_length=1, max_length=255)
    occurred_at: datetime
    lines: list[ReceiptLine] = Field(min_length=1, max_length=2000)
    reason: str = Field(default="", max_length=2000)
    corrects: str | None = Field(default=None, max_length=64)
    resolution: Literal["redelivery", "return", "accept"] | None = None
    signature_image: str | None = Field(default=None, max_length=500000)
    file_ids: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def valid_event(self):
        if not self.occurred_at.tzinfo:
            raise ValueError("A time zone is required")
        if self.kind in {"correction", "resolution", "unpack"} and not self.reason:
            raise ValueError("A reason is required")
        if self.kind == "correction" and not self.corrects:
            raise ValueError("Select the event to correct")
        if self.kind == "resolution" and not self.resolution:
            raise ValueError("Select how to resolve the difference")
        if len({line.allocation_id for line in self.lines}) != len(self.lines):
            raise ValueError("Duplicate goods")
        return self


class GrantIn(StrictModel):
    user_id: int | None = Field(default=None, gt=0)
    email: str = Field(default="", max_length=254)
    role: Literal["operator", "recipient"]
    leg_id: str = Field(min_length=1, max_length=36)
    shipment_ids: list[int] = Field(default_factory=list, max_length=2000)
    expires_at: datetime


class UnloadingIn(StrictModel):
    version: int = Field(ge=1)
    request_id: str = Field(min_length=16, max_length=64)
    unit_ids: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(min_length=1, max_length=10000)
    recipient: str = Field(min_length=1, max_length=255)
    occurred_at: datetime
    reason: str = Field(min_length=10, max_length=2000)

    @model_validator(mode="after")
    def valid_unloading(self):
        if self.occurred_at.tzinfo is None or len(self.unit_ids) != len(set(self.unit_ids)):
            raise ValueError("Use a time zone and unique unit identifiers")
        return self


class AccountIn(StrictModel):
    roles: list[TaskRole] = Field(max_length=5)
    modes: list[Mode] = Field(default_factory=list, max_length=5)
