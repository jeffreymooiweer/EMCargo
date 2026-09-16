"""Bulk import of equipment from a spreadsheet."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.core.messages import detail as message_detail
from app.models.user import Equipment, User
from app.services import equipment as library
from app.core.messages import ApiError
from app.services.spreadsheet_io import normalize_header

#: The columns of the template, in order. The SAP material number left in
#: v1.116.0 — it belonged to one organisation's old system — and the wall
#: thickness took its place, without which the weight of a hollow section
#: cannot be worked out.
EQUIPMENT_HEADERS = [
    "specifications",
    "length_cm",
    "width_cm",
    "height_cm",
    "wall_thickness_mm",
    "weight_kg",
    "aliases",
    "active",
]

LEGACY_HEADERS = list(EQUIPMENT_HEADERS)
EXTRA_HEADERS = ["kind", "asset_code", "brand", "model_name", "registration", "serial_number", "propulsion",
                 "container_number", "container_type", "inner_length_cm", "inner_width_cm", "inner_height_cm",
                 "max_payload_kg", "max_gross_kg", "inspection_due", "current_location", "availability", "condition",
                 "planned_reference", "planned_date", "transport_instructions", "accessories", "source", "notes",
                 "configurations", "language_labels"]
EQUIPMENT_HEADERS += EXTRA_HEADERS

EQUIPMENT_EXAMPLE = [
    "DEMO LIGHT VEHICLE",
    "400",
    "180",
    "170",
    "",
    "1200",
    "demo vehicle, demo light vehicle",
    "yes",
]

EQUIPMENT_EXAMPLE += ["vehicle", "DEMO-01"] + [""] * (len(EXTRA_HEADERS) - 2)

COLUMN_ALIASES: dict[str, set[str]] = {
    "specifications": {"specifications", "specification", "specs", "omschrijving", "description", "naam"},
    "length_cm": {"length_cm", "length", "lengte", "l"},
    "width_cm": {"width_cm", "width", "breedte", "b"},
    "height_cm": {"height_cm", "height", "hoogte", "h"},
    "wall_thickness_mm": {
        "wall_thickness_mm", "wall_thickness", "wall", "wanddikte", "dikte",
        "wandstarke", "wandstärke", "epaisseur", "épaisseur",
    },
    "weight_kg": {"weight_kg", "weight", "gewicht", "kg"},
    "aliases": {"aliases", "alias", "synoniemen", "synonyms"},
    "active": {"active", "actief", "enabled"},
}

COLUMN_ALIASES.update({key: {key} for key in EXTRA_HEADERS})
COLUMN_ALIASES["asset_code"] |= {"materieelnummer", "asset_number", "fleet_number", "inventarisnummer"}
COLUMN_ALIASES["container_number"] |= {"containernummer", "container_no"}
COLUMN_ALIASES["registration"] |= {"kenteken"}
COLUMN_ALIASES["serial_number"] |= {"serienummer"}
COLUMN_ALIASES["brand"] |= {"merk"}
COLUMN_ALIASES["model_name"] |= {"model"}


@dataclass
class EquipmentImportResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    #: One entry per unusable row: ``{"code", "message", "params"}``. A bare
    #: sentence would have to be written in one language, and this list is shown
    #: to the user verbatim.
    errors: list[dict] = field(default_factory=list)


def _detect_column_map(header: list[str]) -> dict[str, int | None]:
    mapping = {key: None for key in EQUIPMENT_HEADERS}
    for idx, col in enumerate(header):
        norm = normalize_header(col)
        for field_name, aliases in COLUMN_ALIASES.items():
            if norm in aliases:
                mapping[field_name] = idx
    return mapping


def _infer_column_map(row: list[str]) -> dict[str, int | None]:
    if len(row) >= len(LEGACY_HEADERS):
        return {key: (idx if idx < len(row) else None) for idx, key in enumerate(EQUIPMENT_HEADERS)}
    mapping: dict[str, int | None] = {key: None for key in EQUIPMENT_HEADERS}
    mapping["specifications"] = 0
    if len(row) >= 2:
        mapping["weight_kg"] = 1
    if len(row) >= 3:
        mapping["length_cm"] = 2
    if len(row) >= 4:
        mapping["width_cm"] = 3
    if len(row) >= 5:
        mapping["height_cm"] = 4
    return mapping


def _has_header_row(rows: list[list[str]]) -> bool:
    if not rows:
        return False
    header_map = _detect_column_map(rows[0])
    return header_map["specifications"] is not None or header_map["weight_kg"] is not None


def _parse_float(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bool(value: str) -> bool:
    norm = value.strip().lower()
    if norm in {"", "yes", "y", "ja", "j", "true", "1", "actief", "active"}:
        return True
    if norm in {"no", "n", "nee", "false", "0", "inactief", "inactive"}:
        return False
    return True


def _parse_aliases(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def _row_to_record(row: list[str], mapping: dict[str, int | None]) -> dict:
    def cell(field: str) -> str:
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    return {
        "specifications": cell("specifications"),
        "length_cm": _parse_float(cell("length_cm")),
        "width_cm": _parse_float(cell("width_cm")),
        "height_cm": _parse_float(cell("height_cm")),
        "wall_thickness_mm": _parse_float(cell("wall_thickness_mm")),
        "weight_kg": _parse_float(cell("weight_kg")),
        "aliases": _parse_aliases(cell("aliases")),
        "active": _parse_bool(cell("active")) if cell("active") else True,
    }


def _number_cell(value: float | None) -> str:
    """A number the import reads back to the same value, or the empty cell.

    Not ``:g`` formatting — that turns a large value into scientific notation,
    which ``_parse_float`` would still read but no person checking the file
    against reality could.
    """
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def equipment_to_rows(items: list[Equipment]) -> list[list[str]]:
    """Export typed metadata as well as the original eight import columns.

    Supporting binary files and confirmed movement history stay on the
    installation; the spreadsheet describes the library's current records.
    """
    rows = []
    for item in items:
        data = library.to_dict(item)
        row = [item.specifications, _number_cell(item.length_cm), _number_cell(item.width_cm),
               _number_cell(item.height_cm), _number_cell(item.wall_thickness_mm), _number_cell(item.weight_kg),
               ", ".join(data["aliases"]), "yes" if item.active else "no"]
        for key in EXTRA_HEADERS:
            value = data.get(key)
            row.append(json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value) if value is not None else "")
        rows.append(row)
    return rows


def import_equipment_rows(db: Session, rows: list[list[str]], user: User | None = None) -> EquipmentImportResult:
    result = EquipmentImportResult()
    if not rows:
        result.errors.append(message_detail("import.no_usable_lines"))
        return result
    has_header = _has_header_row(rows)
    mapping = _detect_column_map(rows[0]) if has_header else _infer_column_map(rows[0])
    if has_header and mapping["specifications"] is None:
        mapping["specifications"] = 0
    start = 1 if has_header else 0
    for line_no, row in enumerate(rows[start:], start=start + 1):
        try:
            record = _row_to_record(row, mapping)
            if not record["specifications"]:
                result.skipped += 1
                continue
            if record["weight_kg"] is None or record["weight_kg"] <= 0:
                result.errors.append(message_detail("equipment.row_weight_missing", row=line_no))
                result.skipped += 1
                continue
            for key in EXTRA_HEADERS:
                index = mapping.get(key)
                if index is None or index >= len(row):
                    continue
                value = row[index].strip()
                if key in {"configurations", "language_labels"}:
                    record[key] = json.loads(value) if value else ([] if key == "configurations" else {})
                elif key.endswith(("_kg", "_cm")) or key in {"inspection_due", "planned_date"}:
                    record[key] = value.replace(",", ".") if value else None
                elif key in {"kind", "availability", "condition"}:
                    if value:
                        record[key] = value
                else:
                    record[key] = value
            asset = str(record.get("asset_code", "")).strip().upper()
            container = str(record.get("container_number", "")).strip().upper()
            if asset:
                existing = db.query(Equipment).filter_by(asset_code=asset).first()
            elif container:
                existing = db.query(Equipment).filter_by(container_number=container).first()
            else:
                matches = db.query(Equipment).filter(Equipment.specifications.ilike(record["specifications"])).all()
                if len(matches) > 1 or (matches and (matches[0].asset_code or matches[0].container_number)):
                    raise ValueError("Use the asset or container number to identify this equipment.")
                existing = matches[0] if matches else None
            if existing and not record["aliases"]:
                record.pop("aliases")
            if not existing:
                record.setdefault("source", "import")
            # Each rejected row rolls back its own work; other valid rows survive.
            with db.begin_nested():
                library.save(db, record, user, existing=existing)
            if existing:
                result.updated += 1
            else:
                result.created += 1
        except (ApiError, ValueError) as exc:
            reason = exc.detail["message"] if isinstance(exc, ApiError) else str(exc)
            result.errors.append(message_detail("equipment.row_invalid", row=line_no, reason=reason))
            result.skipped += 1
    library.commit(db)
    return result
