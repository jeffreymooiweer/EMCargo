"""Stable shipment distributions, independent of the transport plan."""
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class RoutingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Party(RoutingModel):
    name: str = Field(default="", max_length=255)
    address: str = Field(default="", max_length=1000)
    country: str = Field(default="", max_length=100)
    contact: str = Field(default="", max_length=255)


class Location(Party):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    kind: Literal["pickup", "delivery"]
    party: Party = Field(default_factory=Party)


class Distribution(RoutingModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    goods_id: str = Field(min_length=1, max_length=120)
    quantity: Decimal = Field(ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    pickup_id: str = Field(default="", max_length=36)
    delivery_id: str = Field(default="", max_length=36)
    unit_ids: list[str] = Field(default_factory=list, max_length=10000)
    # Explicit declarations for a split; originals bind confirmation to the
    # source classification, goods, quantity and address pair.
    dangerous_goods: list[dict[str, Any]] = Field(default_factory=list, max_length=1000)
    dg_confirmation: dict[str, Any] | None = None


class ShipmentRouting(RoutingModel):
    version: Literal[1] = 1
    locations: list[Location] = Field(default_factory=list, max_length=2000)
    distributions: list[Distribution] = Field(default_factory=list, max_length=2000)


class Stop(Party):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=36)
    kind: Literal["pickup", "delivery", "transfer"]
    shipment_id: int | None = Field(default=None, gt=0)
    location_id: str | None = Field(default=None, max_length=36)
    override_reason: str = Field(default="", max_length=2000)
