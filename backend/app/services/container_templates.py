"""Sourced product examples; selecting one never creates a physical asset."""
import json
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.core.config import get_settings
from app.schemas.equipment import Positive


class ContainerTemplate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str
    language_labels: dict[str, str]
    family: Literal["dry", "high_cube", "side_door", "double_door", "double_side_door", "open_top", "hard_top", "flatrack", "reefer", "pallet_wide", "tank", "site", "storage"]
    size_ft: Positive
    supplier: str
    source_url: HttpUrl
    checked_on: str
    # Measurements describe the cited supplier model, not every unit of a size.
    basis: Literal["supplier_example", "cut_down_nominal", "base_shell", "mass_conflict"] = "supplier_example"
    length_cm: Positive
    width_cm: Positive
    height_cm: Positive
    inner_length_cm: Positive | None = None
    inner_width_cm: Positive | None = None
    inner_height_cm: Positive | None = None
    weight_kg: Positive | None = None
    max_payload_kg: Positive | None = None
    max_gross_kg: Positive | None = None
    container_use: Literal["freight", "storage", "workshop", "office", "sanitary", "accommodation", "other"] = "freight"


@lru_cache(maxsize=1)
def container_templates() -> list[dict]:
    path = get_settings().seed_dir / "container_templates.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    records = [ContainerTemplate.model_validate(item).model_dump(mode="json") for item in data["templates"]]
    if len({item["id"] for item in records}) != len(records):
        raise ValueError("Duplicate container template identifier")
    return records
