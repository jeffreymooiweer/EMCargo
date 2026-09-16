"""Equipment master data and the frozen transport data selected by a shipment."""
from datetime import date
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Kind = Literal["vehicle", "machine", "container", "other"]
Availability = Literal["unknown", "available", "planned", "in_transit", "maintenance"]


class EquipmentInspection(BaseModel):
    """A separately maintained inspection, with no inferred statutory interval."""
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=64)
    kind: Literal["general", "csc", "nen3140", "fgas", "apk", "lifting", "water", "fire", "other"] = "general"
    name: str = Field(default="", max_length=120)
    scope: str = Field(default="", max_length=160)
    performed_on: date | None = None
    due_on: date | None = None
    result: Literal["unknown", "passed", "failed", "conditional", "not_applicable"] = "unknown"
    inspector: str = Field(default="", max_length=160)
    reference: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=2000)
    archived: bool = False

    @model_validator(mode="after")
    def valid_record(self):
        if self.kind == "other" and not self.name.strip():
            raise PydanticCustomError("equipment.inspection_name", "Enter a name for this inspection.")
        if self.performed_on and self.due_on and self.due_on < self.performed_on:
            raise PydanticCustomError("equipment.inspection_dates", "The due date cannot precede the inspection date.")
        if self.result in {"passed", "failed", "conditional"} and not self.performed_on:
            raise PydanticCustomError("equipment.inspection_date_required", "Enter the date of the recorded inspection result.")
        return self


class TransportConfiguration(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    length_cm: Positive | None = None
    width_cm: Positive | None = None
    height_cm: Positive | None = None
    weight_kg: Positive
    instructions: str = Field(default="", max_length=2000)


class EquipmentDetails(BaseModel):
    brand: str = Field(default="", max_length=100)
    model_name: str = Field(default="", max_length=100)
    registration: str = Field(default="", max_length=64)
    serial_number: str = Field(default="", max_length=100)
    propulsion: Literal["", "diesel", "petrol", "electric", "lpg", "hybrid", "other"] = ""
    transport_instructions: str = Field(default="", max_length=4000)
    accessories: str = Field(default="", max_length=1000)
    container_type: str = Field(default="", max_length=80)
    container_template_id: str = Field(default="", max_length=100)
    container_use: Literal["freight", "storage", "workshop", "office", "sanitary", "accommodation", "other"] = "freight"
    facilities: list[Literal["electricity", "water", "air_conditioning", "heating", "sanitary"]] = Field(default_factory=list, max_length=5)
    inner_length_cm: Positive | None = None
    inner_width_cm: Positive | None = None
    inner_height_cm: Positive | None = None
    max_payload_kg: Positive | None = None
    max_gross_kg: Positive | None = None
    inspection_due: date | None = None
    inspections: list[EquipmentInspection] = Field(default_factory=list, max_length=100)
    current_location: str = Field(default="", max_length=200)
    availability: Availability = "unknown"
    condition: Literal["unknown", "good", "damaged", "unserviceable"] = "unknown"
    planned_reference: str = Field(default="", max_length=120)
    planned_date: date | None = None
    configurations: list[TransportConfiguration] = Field(default_factory=list, max_length=20)

    @model_validator(mode="before")
    @classmethod
    def legacy_inspection(cls, values):
        if isinstance(values, dict) and "inspections" not in values and values.get("inspection_due"):
            return {**values, "inspections": [{"id": "legacy-inspection", "kind": "general", "due_on": values["inspection_due"]}]}
        return values

    @model_validator(mode="after")
    def distinct_configurations(self):
        names = [config.name.strip().casefold() for config in self.configurations]
        if any(not name for name in names) or len(set(names)) != len(names):
            raise PydanticCustomError("equipment.configuration_names", "Give each transport configuration a distinct name.")
        identifiers = [inspection.id for inspection in self.inspections]
        if len(set(identifiers)) != len(identifiers):
            raise PydanticCustomError("equipment.inspection_ids", "Each inspection must have its own identifier.")
        self.facilities = list(dict.fromkeys(self.facilities))
        self.inspection_due = min((inspection.due_on for inspection in self.inspections
                                   if inspection.due_on and not inspection.archived and inspection.result != "not_applicable"), default=None)
        return self


class EquipmentBase(EquipmentDetails):
    specifications: str = Field(min_length=1, max_length=255)
    kind: Kind = "other"
    asset_code: str = Field(default="", max_length=64)
    container_number: str = Field(default="", max_length=32)
    length_cm: Positive | None = None
    width_cm: Positive | None = None
    height_cm: Positive | None = None
    wall_thickness_mm: Positive | None = None
    weight_kg: Positive
    aliases: list[Annotated[str, Field(max_length=120)]] = Field(default_factory=list, max_length=50)
    language_labels: dict[str, str] = Field(default_factory=dict)
    source: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)
    active: bool = True

    @field_validator("asset_code", "container_number", mode="before")
    @classmethod
    def identifiers(cls, value):
        return str(value or "").strip().upper()

    @field_validator("specifications")
    @classmethod
    def named(cls, value):
        if not value.strip():
            raise PydanticCustomError("equipment.name_required", "Enter an equipment name.")
        return value.strip()

    @model_validator(mode="after")
    def container_limits(self):
        if self.kind == "container":
            if self.max_gross_kg is not None and self.max_gross_kg <= self.weight_kg:
                raise PydanticCustomError("equipment.gross_limit", "Maximum gross weight must exceed the empty container weight.")
            for inside, outside in ((self.inner_length_cm, self.length_cm), (self.inner_width_cm, self.width_cm), (self.inner_height_cm, self.height_cm)):
                if inside is not None and outside is not None and inside > outside:
                    raise PydanticCustomError("equipment.inner_dimensions", "Internal dimensions cannot exceed external dimensions.")
        return self


class EquipmentUpdate(BaseModel):
    """Partial updates are merged with the saved record, then fully validated.

    This deliberately retains unset versus explicit null. Nullable dimensions
    can be cleared while required identity and weight fields cannot disappear.
    """
    model_config = {"extra": "allow"}
    version: int | None = Field(default=None, ge=1)


class EquipmentOut(EquipmentBase):
    id: int
    version: int = 1
    photo_url: str | None = None
    file_count: int = 0


class EquipmentSnapshot(BaseModel):
    equipment_id: int = Field(gt=0)
    version: int = Field(default=1, ge=1)
    specifications: str = Field(min_length=1, max_length=255)
    kind: Kind = "other"
    asset_code: str = Field(default="", max_length=64)
    container_number: str = Field(default="", max_length=32)
    registration: str = Field(default="", max_length=64)
    serial_number: str = Field(default="", max_length=100)
    length_cm: Positive | None = None
    width_cm: Positive | None = None
    height_cm: Positive | None = None
    weight_kg: Positive
    max_payload_kg: Positive | None = None
    max_gross_kg: Positive | None = None
    inner_length_cm: Positive | None = None
    inner_width_cm: Positive | None = None
    inner_height_cm: Positive | None = None
    transport_instructions: str = Field(default="", max_length=4000)
    accessories: str = Field(default="", max_length=1000)
    configuration: str = Field(default="", max_length=100)
    configurations: list[TransportConfiguration] = Field(default_factory=list, max_length=20)


class EquipmentMovement(BaseModel):
    version: int = Field(ge=1)
    to_location: str = Field(min_length=1, max_length=200)
    availability: Availability = "available"
    reference: str = Field(default="", max_length=120)
    notes: str = Field(default="", max_length=2000)

    @field_validator("to_location")
    @classmethod
    def destination(cls, value):
        if not value.strip():
            raise PydanticCustomError("equipment.location_required", "Enter the confirmed destination.")
        return value.strip()
