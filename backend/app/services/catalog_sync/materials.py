import json
import logging
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.user import Material
from app.services.catalog_sync.sources import EUROCODE_MATERIAL_SOURCE

logger = logging.getLogger(__name__)

EXTERNAL_SOURCE_PREFIXES = (
    "github:",
    "eurocodepy:",
    "nist:",
    "seed:",
    "eurocode:",
    "wikidata:",
    "en1991:",
)


@dataclass
class MaterialRecord:
    canonical_name: str
    category: str
    density_kg_m3: float
    density_min_kg_m3: float | None = None
    density_max_kg_m3: float | None = None
    condition: str | None = None
    language_labels: dict[str, str] | None = None
    aliases: list[str] | None = None
    source: str | None = None
    notes: str | None = None


def load_seed_material_records(seed_path: Path) -> list[MaterialRecord]:
    if not seed_path.exists():
        return []
    records = list(_read_seed(str(seed_path), seed_path.stat().st_mtime_ns))
    for measured in sorted(seed_path.parent.glob("materials_measured*.json")):
        records.extend(_read_seed(str(measured), measured.stat().st_mtime_ns))
    # Synchronisation enriches records in place. Never mutate the cached seed.
    return [replace(record, aliases=list(record.aliases or []), language_labels=dict(record.language_labels or {})) for record in records]


@lru_cache(maxsize=8)
def _read_seed(path: str, modified: int) -> tuple[MaterialRecord, ...]:
    return tuple(parse_bundled_materials(Path(path).read_text(encoding="utf-8"), default_source="seed:materials.json"))


def parse_bundled_materials(raw: str, *, default_source: str | None = None) -> list[MaterialRecord]:
    items = json.loads(raw)
    records: list[MaterialRecord] = []
    for item in items:
        records.append(
            MaterialRecord(
                canonical_name=item["canonical_name"],
                category=item["category"],
                density_kg_m3=item["density_kg_m3"],
                density_min_kg_m3=item.get("density_min_kg_m3"),
                density_max_kg_m3=item.get("density_max_kg_m3"),
                condition=item.get("condition"),
                language_labels=item.get("language_labels", {}),
                aliases=item.get("aliases", []),
                source=item.get("source") or default_source,
                notes=item.get("notes"),
            )
        )
    return records


def merge_material_records(*groups: list[MaterialRecord]) -> list[MaterialRecord]:
    """Later groups override density/source for the same canonical_name."""
    merged: dict[str, MaterialRecord] = {}
    for group in groups:
        for record in group:
            existing = merged.get(record.canonical_name)
            if not existing:
                merged[record.canonical_name] = record
                continue
            existing.category = record.category
            existing.density_kg_m3 = record.density_kg_m3
            if record.density_min_kg_m3 is not None:
                existing.density_min_kg_m3 = record.density_min_kg_m3
            if record.density_max_kg_m3 is not None:
                existing.density_max_kg_m3 = record.density_max_kg_m3
            if record.condition:
                existing.condition = record.condition
            if record.language_labels:
                existing.language_labels = {**(existing.language_labels or {}), **record.language_labels}
            if record.aliases:
                existing.aliases = list(dict.fromkeys([*(existing.aliases or []), *record.aliases]))
            if record.source:
                existing.source = record.source
            if record.notes:
                existing.notes = record.notes
    return list(merged.values())


def enrich_from_eurocode(records: list[MaterialRecord], eurocode_json: dict) -> list[MaterialRecord]:
    materials = eurocode_json.get("Eurocodes", {}).get("Materials", {})
    steel_mass = materials.get("Steel", {}).get("Parameters", {}).get("mass")
    if steel_mass:
        _upsert_record(records, "steel", density_kg_m3=float(steel_mass), source=EUROCODE_MATERIAL_SOURCE)
    timber = materials.get("Timber", {}).get("Grade", {})
    c24 = timber.get("C24", {})
    if c24.get("rhom"):
        _upsert_record(
            records,
            "spruce",
            density_kg_m3=float(c24["rhom"]),
            density_min_kg_m3=float(c24.get("rhok", c24["rhom"])),
            source=EUROCODE_MATERIAL_SOURCE,
        )
    gl24 = timber.get("GL24h", {})
    if gl24.get("rhom"):
        _upsert_record(
            records,
            "glulam_gl24h",
            density_kg_m3=float(gl24["rhom"]),
            source=EUROCODE_MATERIAL_SOURCE,
        )
    return records


def _upsert_record(
    records: list[MaterialRecord],
    canonical_name: str,
    *,
    density_kg_m3: float,
    density_min_kg_m3: float | None = None,
    source: str | None = None,
) -> None:
    for record in records:
        if record.canonical_name == canonical_name:
            record.density_kg_m3 = density_kg_m3
            if density_min_kg_m3 is not None:
                record.density_min_kg_m3 = density_min_kg_m3
            if source:
                record.source = source
            return
    records.append(
        MaterialRecord(
            canonical_name=canonical_name,
            category="metal" if canonical_name == "steel" else "wood",
            density_kg_m3=density_kg_m3,
            density_min_kg_m3=density_min_kg_m3,
            source=source,
        )
    )


def _is_external_managed(material: Material) -> bool:
    if not material.source:
        return True
    lower = material.source.lower()
    return lower.startswith(EXTERNAL_SOURCE_PREFIXES) or "eurocode" in lower or "github" in lower


def upsert_materials(db: Session, records: list[MaterialRecord], *, only_missing: bool = False) -> tuple[int, int]:
    added = 0
    updated = 0
    if only_missing:
        existing_names = {name for (name,) in db.query(Material.canonical_name).all()}
        records = [record for record in records if record.canonical_name not in existing_names]
        # Seed upgrades only insert missing rows. Batch them without thousands
        # of transient ORM objects, keeping existing local rows untouched.
        if records:
            db.bulk_insert_mappings(Material, [_material_values(record) for record in records], render_nulls=True)
        return len(records), 0
    by_name = {material.canonical_name: material for material in db.query(Material).all()}
    for record in records:
        existing = by_name.get(record.canonical_name)
        if existing:
            if only_missing or not _is_external_managed(existing):
                continue
            existing.category = record.category
            existing.density_kg_m3 = record.density_kg_m3
            existing.density_min_kg_m3 = record.density_min_kg_m3
            existing.density_max_kg_m3 = record.density_max_kg_m3
            existing.condition = record.condition
            if record.language_labels:
                existing.language_labels_json = json.dumps(record.language_labels, ensure_ascii=False)
            if record.aliases:
                existing.aliases_json = json.dumps(record.aliases, ensure_ascii=False)
            existing.source = record.source
            existing.notes = record.notes
            existing.active = True
            updated += 1
        else:
            db.add(Material(**_material_values(record)))
            added += 1
    return added, updated


def _material_values(record: MaterialRecord) -> dict:
    return {
        "canonical_name": record.canonical_name,
        "category": record.category,
        "density_kg_m3": record.density_kg_m3,
        "density_min_kg_m3": record.density_min_kg_m3,
        "density_max_kg_m3": record.density_max_kg_m3,
        "condition": record.condition,
        "language_labels_json": json.dumps(record.language_labels or {}, ensure_ascii=False),
        "aliases_json": json.dumps(record.aliases or [], ensure_ascii=False),
        "source": record.source,
        "notes": record.notes,
        "active": True,
    }


def merge_seed_material_aliases(db: Session, records: list[MaterialRecord]) -> None:
    """Keep extra aliases from the local seed when canonical_name matches."""
    by_name = {r.canonical_name: r for r in records}
    for material in db.query(Material).all():
        if material.canonical_name not in by_name:
            continue
        seed_aliases = set(json.loads(material.aliases_json or "[]"))
        record = by_name[material.canonical_name]
        merged = list(dict.fromkeys([*(record.aliases or []), *seed_aliases]))
        record.aliases = merged
        labels = json.loads(material.language_labels_json or "{}")
        if labels:
            record.language_labels = {**(record.language_labels or {}), **labels}
