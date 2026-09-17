"""Versioned cargo data shared by the editor and independent consumers."""
from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Measure = Annotated[float, Field(ge=0, le=1e12, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, le=1e12, allow_inf_nan=False)]


class CargoModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Dimensions(CargoModel):
    length: Positive | None = None
    width: Positive | None = None
    height: Positive | None = None


class PackagingProperties(CargoModel):
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="box", min_length=1, max_length=32)
    dimensions_mm: Dimensions | None = None
    inner_dimensions_mm: Dimensions | None = None
    tare_kg: Measure | None = None
    max_payload_kg: Positive | None = None
    max_gross_kg: Positive | None = None
    max_stack_load_kg: Measure | None = None
    stackable: bool | None = None
    keep_upright: bool | None = None
    can_rotate: bool | None = None
    reusable: bool = False

    @field_validator("name", "category")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A name is required")
        return value.strip()


class PackagingTemplateIn(PackagingProperties):
    language_labels: dict[str, str] = Field(default_factory=dict)
    active: bool = True
    version: int | None = Field(default=None, ge=1)


class CargoUnit(PackagingProperties):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    kind: Literal["package", "ctu"] = "package"
    source: Literal["own", "external", "unknown"] = "unknown"
    parent_id: str | None = Field(default=None, max_length=64)
    template_id: str | None = Field(default=None, max_length=64)
    group_id: str | None = Field(default=None, max_length=64)
    equipment_id: int | None = Field(default=None, gt=0)
    external_reference: str | None = Field(default=None, max_length=120)
    loaded_dimensions_mm: Dimensions | None = None
    measured_gross_kg: Measure | None = None
    # A migrated container line already contributes its tare to legacy totals.
    legacy_goods_id: int | None = None

    @field_validator("id", "parent_id")
    @classmethod
    def valid_identity(cls, value: str | None) -> str | None:
        if value is not None:
            return str(UUID(value))
        return value


class CargoAllocation(CargoModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=64)
    goods_id: int
    unit_id: str = Field(min_length=1, max_length=64)
    quantity: Positive

    @field_validator("id", "unit_id")
    @classmethod
    def valid_identity(cls, value: str) -> str:
        return str(UUID(value))


class CargoManifest(CargoModel):
    schema_version: Literal[1] = 1
    shipment_id: str = Field(default_factory=lambda: str(uuid4()), max_length=64)
    revision: int = Field(default=0, ge=0)
    units: list[CargoUnit] = Field(default_factory=list, max_length=10000)
    allocations: list[CargoAllocation] = Field(default_factory=list, max_length=50000)

    @field_validator("shipment_id")
    @classmethod
    def valid_shipment(cls, value: str) -> str:
        return str(UUID(value))

    @model_validator(mode="after")
    def unique_ids(self):
        for values in ([unit.id for unit in self.units], [unit.code for unit in self.units],
                       [allocation.id for allocation in self.allocations]):
            if len(values) != len(set(values)):
                raise ValueError("Cargo identifiers must be unique")
        return self


class CargoAssessmentIn(CargoModel):
    cargo: CargoManifest
    lines: list[dict] = Field(default_factory=list, max_length=10000)
