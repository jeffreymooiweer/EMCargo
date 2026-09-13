"""Trace the density actually stored in an installation to its bundled source."""
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.languages import pick
from app.models.user import Material

MEASURED_SOURCES = ("seed:gwdd:2.2:original", "seed:hapman:2026-09-13",
    "seed:nist:thermoml:2020-09-30", "seed:campus:2026-09-13", "seed:ensinger:2026-09-13",
    "seed:cda:2026-09-13", "seed:fao:2.0:measured", "seed:fao:2.0:compiled", "seed:rockwool:2026-09-13")
_CONDITION_WORDS = frozenset({"wood", "hout", "holz", "bois", "heartwood", "kernhout", "kernholz", "duramen",
    "ovendroog", "oven", "dry", "darrtrockenes", "anhydre", "moisture", "vocht", "feuchte", "humidité",
    "bulk", "solid", "bulkstof", "schüttgut", "vrac"})


def material_candidates(db: Session, text: str) -> list[Material]:
    """Keep legacy substring recognition, preselect the larger qualified set.

    Loading the entire reference catalogue for every pasted line made a small
    import slow. New references have no unqualified aliases: a meaningful
    name token must occur before the existing scorer/matcher needs them.
    """
    words = {word for word in re.findall(r"\w+", text.casefold()) if len(word) >= 3 and not word.isdigit() and word not in _CONDITION_WORDS}
    patterns = []
    for word in sorted(words) or [text.casefold()]:
        escaped = word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        patterns.extend((
            Material.language_labels_json.ilike(f"%{escaped}%", escape="\\"),
            Material.canonical_name.ilike(f"%{escaped}%", escape="\\"),
            Material.aliases_json.ilike(f"%{escaped}%", escape="\\"),
        ))
    return db.query(Material).filter(Material.active.is_(True), or_(Material.source.is_(None), Material.source.notin_(MEASURED_SOURCES), *patterns)).all()


@lru_cache(maxsize=2)
def _references(path: str) -> dict[str, dict]:
    file = Path(path)
    if not file.exists():
        return {}
    return {row["canonical_name"]: row
            for part in sorted(file.parent.glob("materials_measured*.json"))
            for row in json.loads(part.read_text(encoding="utf-8"))}


def density_reference(material: Material, language: str = "en") -> dict:
    row = _references(str(get_settings().seed_dir / "materials_measured.json")).get(material.canonical_name)
    provenance = {}
    if (row and material.source == row["source"]
            and math.isclose(material.density_kg_m3, row["density_kg_m3"], abs_tol=0.0001)
            and material.condition == row["condition"]
            and material.category == row["category"]
            and material.density_min_kg_m3 == row.get("density_min_kg_m3")
            and material.density_max_kg_m3 == row.get("density_max_kg_m3")):
        provenance = row["provenance"]
    return {
        "canonical_name": material.canonical_name,
        "label": pick(json.loads(material.language_labels_json or "{}"), language, default=material.canonical_name),
        "density_kg_m3": material.density_kg_m3,
        "density_min_kg_m3": material.density_min_kg_m3,
        "density_max_kg_m3": material.density_max_kg_m3,
        "kind": provenance.get("kind", "unverified"),
        "basis": provenance.get("basis"),
        "source_name": provenance.get("source_name"),
        "source_url": provenance.get("source_url"),
        "record_count": provenance.get("record_count"),
        "condition_key": provenance.get("condition_key"),
        **{key: provenance.get(key) for key in ("temperature_c", "pressure_kpa", "phase", "method",
            "expanded_uncertainty_kg_m3", "original_value", "original_unit", "manufacturer")},
    }


def list_density_references(db: Session, query: str, *, offset: int = 0, limit: int = 30, language: str = "nl", category: str = "") -> dict:
    materials = db.query(Material).filter(Material.active.is_(True))
    if category:
        materials = materials.filter(Material.category == category)
    # Literal search, including percent signs in moisture conditions.
    for term in query.strip().split():
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        materials = materials.filter(or_(
            Material.canonical_name.ilike(pattern, escape="\\"),
            Material.language_labels_json.ilike(pattern, escape="\\"),
            Material.aliases_json.ilike(pattern, escape="\\"),
        ))
    total = materials.count()
    rows = materials.order_by(Material.canonical_name, Material.id).offset(offset).limit(limit).all()
    return {"total": total, "offset": offset, "results": [density_reference(row, language) for row in rows]}
