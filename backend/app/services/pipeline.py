import json
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from sqlalchemy.orm import Session

from app.models.user import Equipment, Material, Profile, ReferenceItem
from app.services.density_references import density_reference, material_candidates
from app.services.calculator.engine import (
    STEEL_DENSITY,
    calc_angle_profile,
    calc_catalog_profile,
    calc_hollow_rect,
    calc_round_bar,
    calc_round_tube,
    calc_solid_block,
    transport_volume_outer,
)
from app.services.dg.detector import (
    detect_dangerous_goods,
    detect_package_content,
    detect_un_numbers,
)
from app.services.dg.name_detection import detect_name_candidates
from app.services.parser.dimension_extractor import Dimensions, extract_dimensions, meters_to_cm
from app.core.languages import pick
from app.services.parser.language_detector import detect_language
from app.services.parser.paste_parser import ParsedRow, parse_paste
from app.services.units import Dimension, convert as convert_units, get_unit as units_get_unit
from app.services.parser.product_detector import detect_product_type

PRODUCT_LABELS = {
    "angle_profile": {"nl": "Hoekprofiel", "en": "Angle profile", "de": "Winkelprofil", "fr": 'Cornière'},
    "square_tube": {"nl": "Kokerprofiel", "en": "Square tube", "de": "Quadratrohr", "fr": 'Tube carré'},
    "round_tube": {"nl": "Buis", "en": "Pipe", "de": "Rohr", "fr": 'Tube'},
    "round_bar": {"nl": "Ronde staf", "en": "Round bar", "de": "Rundstab", "fr": 'Barre ronde'},
    "plate": {"nl": "Plaat", "en": "Plate", "de": "Blech", "fr": 'Tôle'},
    "beam": {"nl": "Balk", "en": "Beam", "de": "Träger", "fr": 'Poutre'},
    "standard_profile": {"nl": "Staalprofiel", "en": "Steel profile", "de": "Stahlprofil", "fr": 'Profilé en acier'},
    "concrete_slab": {"nl": "Betonplaat", "en": "Concrete slab", "de": "Betonplatte", "fr": 'Dalle de béton'},
    "plywood": {"nl": "Plaatmateriaal", "en": "Sheet material", "de": "Plattenwerkstoff", "fr": 'Panneau'},
    "reference_item": {"nl": "Artikel", "en": "Item", "de": "Artikel", "fr": 'Article'},
    "equipment": {"nl": "Materieel", "en": "Equipment", "de": "Material", "fr": 'Matériel'},
    "unknown": {"nl": "Onbekend", "en": "Unknown", "de": "Unbekannt", "fr": 'Inconnu'},
}

STEEL_PRODUCT_TYPES = {
    "angle_profile",
    "square_tube",
    "round_tube",
    "round_bar",
    "plate",
    "beam",
    "standard_profile",
    "concrete_slab",
    "plywood",
}


@dataclass
class LineResult:
    line_id: int
    raw: str
    description: str
    output_description: str
    quantity: float | None
    unit: str | None
    material: str | None = None
    material_density: float | None = None
    density_reference: dict[str, Any] | None = None
    # The category of the recognised commodity. The interface uses it to suggest
    # the units belonging to this kind of cargo: litres for liquids, tonnes for
    # bulk, pieces for general cargo.
    material_category: str | None = None
    # The form this commodity travels in. A user wondering where 9360 kg comes
    # from should be able to see that a stacked cubic metre was used and not
    # solid timber.
    cargo_form: str | None = None
    product_type: str | None = None
    dimensions: dict[str, Any] = field(default_factory=dict)
    length_cm: float | None = None
    width_cm: float | None = None
    height_cm: float | None = None
    weight_each_kg: float | None = None
    weight_total_kg: float | None = None
    material_volume_m3: float | None = None
    transport_volume_m3: float | None = None
    kg_per_meter: float | None = None
    status: str = "ok"
    messages: list[str] = field(default_factory=list)
    confidence: float = 1.0
    include: bool = True
    input_language: str = "nl"
    calculation_method: str | None = None
    dangerous_goods: bool = False
    detected_un_numbers: list[str] = field(default_factory=list)
    # Substances recognised by name in the description. Suggestions only: the
    # interface proposes them and the user confirms — a DG classification is
    # never set silently on the strength of a word in free text.
    dg_name_candidates: list[dict[str, Any]] = field(default_factory=list)
    # "1000 jerrycans van 25l": what one package holds, read from the
    # description of a line counted in packages. Feeds the DG derivation so
    # the net-per-package question never has to be asked.
    package_content: str | None = None
    equipment: dict[str, Any] | None = None
    equipment_role: str = "cargo"
    container_line_id: int | None = None
    cargo_goods_id: int | None = None


def _load_aliases_json(raw: str) -> list[str]:
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []


def match_material(text: str, db: Session) -> tuple[Material | None, float]:
    lower = text.lower()
    best: Material | None = None
    best_len = 0
    for material in material_candidates(db, text):
        aliases = [material.canonical_name.lower(), *_load_aliases_json(material.aliases_json)]
        labels = json.loads(material.language_labels_json or "{}")
        aliases.extend(v.lower() for v in labels.values())
        for alias in aliases:
            if alias and alias in lower and len(alias) > best_len:
                best = material
                best_len = len(alias)
    return best, best.density_kg_m3 if best else STEEL_DENSITY


def match_profile(text: str, dims: Dimensions, db: Session) -> Profile | None:
    candidates = []
    if dims.profile_size:
        candidates.append(dims.profile_size.lower())
    for profile in db.query(Profile).filter(Profile.active.is_(True)).all():
        aliases = [f"{profile.profile_type} {profile.size_label}".lower(), profile.size_label.lower()]
        aliases.extend(a.lower() for a in _load_aliases_json(profile.aliases_json))
        hay = text.lower()
        for alias in aliases:
            if alias and alias in hay:
                return profile
    return None


def match_reference(text: str, db: Session) -> ReferenceItem | None:
    lower = text.lower()
    best: ReferenceItem | None = None
    best_len = 0
    for item in db.query(ReferenceItem).filter(ReferenceItem.active.is_(True)).all():
        aliases = [item.canonical_name.lower(), *_load_aliases_json(item.aliases_json)]
        labels = json.loads(item.language_labels_json or "{}")
        aliases.extend(v.lower() for v in labels.values())
        for alias in aliases:
            if alias and alias in lower and len(alias) > best_len:
                best = item
                best_len = len(alias)
    return best


def match_equipment(text: str, db: Session) -> Equipment | None:
    lower = text.lower()
    best: Equipment | None = None
    best_len = 0
    ambiguous = False
    for item in db.query(Equipment).filter(Equipment.active.is_(True)).all():
        aliases = [item.specifications.lower()]
        aliases.extend(a.lower() for a in _load_aliases_json(item.aliases_json))
        labels = json.loads(item.language_labels_json or "{}")
        aliases.extend(v.lower() for v in labels.values())
        for alias in aliases:
            if alias and alias in lower and len(alias) > best_len:
                best = item
                best_len = len(alias)
                ambiguous = False
            elif alias and alias in lower and len(alias) == best_len and best is not item:
                ambiguous = True
    return None if ambiguous else best


def build_output_description(description: str, product_type: str | None, dims: Dimensions, lang: str) -> str:
    # Without a recognised shape the consignor's own words are the
    # description. "Onbekend 2000x1000x5 mm" on the goods box of a waybill
    # tells the carrier strictly less than what was typed — the normalised
    # form is only an improvement when there is a name to normalise to.
    labels = PRODUCT_LABELS.get(product_type or "")
    if labels is None:
        return description
    label = pick(labels, lang)
    if dims.profile_size:
        size = dims.profile_size
        length_mm = int(round((dims.length_m or 0) * 1000))
        return f"{label} {size} {length_mm} mm"
    if dims.values_m:
        mm = "x".join(str(int(round(v * 1000))) for v in dims.values_m)
        return f"{label} {mm} mm"
    return description


# Cross-sections with a wall. For these shapes length-width-height says nothing
# about the weight: an 80x80 angle is two legs 8 mm thick and not a solid bar of
# 80x80. The difference is a factor of five, and that is exactly the kind of
# figure that looks reliable on a waybill.
#
# For a plate, a beam, a plank or a block this does not come into play: there
# three measurements describe the material completely. The field should
# therefore only appear where it means something.
WALL_PROFILE_TYPES = {"angle_profile", "square_tube", "round_tube"}


def _positive(value: Any) -> float | None:
    """A measurement is only a measurement when it is greater than zero."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _split_package_content(content: str | None) -> tuple[float, Any]:
    """"25 L" as the number and the unit the catalogue knows it by."""
    amount, _, symbol = str(content or "").partition(" ")
    try:
        number = float(amount)
    except ValueError:
        return 0.0, None
    unit = units_get_unit(symbol) if number > 0 else None
    return number, unit


def process_line(
    line_id: int,
    row: ParsedRow,
    db: Session,
    input_language: str | None = None,
    output_language: str = "nl",
    overrides: dict[str, Any] | None = None,
) -> LineResult:
    overrides = overrides or {}
    lang = input_language or detect_language(row.description)
    dims = extract_dimensions(row.description)
    product_type = overrides.get("product_type") or detect_product_type(row.description)
    material_obj, density = match_material(row.description, db)
    if overrides.get("material_density"):
        density = float(overrides["material_density"])
    material_name = overrides.get("material") or (material_obj.canonical_name if material_obj else None)
    qty = overrides.get("quantity", row.quantity)
    messages: list[str] = []
    status = "ok"
    cargo_form: str | None = None
    weight_each = None
    weight_total = None
    material_vol = None
    transport_vol = None
    kg_per_m = overrides.get("kg_per_meter")
    method = None
    length_cm = meters_to_cm(overrides.get("length_m") or dims.length_m)
    width_cm = meters_to_cm(overrides.get("width_m") or dims.width_m)
    height_cm = meters_to_cm(overrides.get("height_m") or dims.height_m)

    # A per-package content only exists on a line counted in packages: on a
    # line measured in litres the litre figure is the quantity itself. Read
    # before the calculation, because a known content is what turns a count of
    # packages into a mass.
    row_unit = units_get_unit(row.unit)
    package_content = (
        detect_package_content(row.description)
        if row_unit is not None and row_unit.dimension == Dimension.COUNT
        else None
    )

    # Dimensions the user fills in themselves in the table count towards the
    # calculation and not only towards the display. Until v1.35.0 they were taken
    # over here for the screen, but the calculation paths below kept looking at
    # what had been read out of the *description*. Anyone typing "oak beam" and
    # then putting the measurements in the columns saw their input ignored.
    # A fourth measurement: the wall thickness. Without it the weight of an angle
    # or a hollow section cannot be determined, and with the three outside
    # measurements alone the answer is five times too heavy.
    wall_m = _positive(overrides.get("wall_thickness_m"))
    # For a round cross-section the width is the diameter and there is no
    # height; we set those equal so the rest of the code does not trip over a
    # missing third measurement.
    if product_type in {"round_tube", "round_bar"} and overrides.get("width_m"):
        overrides = {**overrides, "height_m": overrides["width_m"]}

    entered = [overrides.get("width_m"), overrides.get("height_m"), overrides.get("length_m")]
    if all(value for value in entered):
        # The same order the calculation paths expect: width, height, length.
        dims = replace(
            dims,
            values_m=[float(value) for value in entered],
            width_m=float(overrides["width_m"]),
            height_m=float(overrides["height_m"]),
            length_m=float(overrides["length_m"]),
        )
    elif overrides.get("length_m"):
        # A length alone is enough for a profile from the catalogue.
        dims = replace(dims, length_m=float(overrides["length_m"]))

    ref = match_reference(row.description, db)
    if ref and not product_type:
        product_type = "reference_item"
        weight_each = ref.reference_weight_kg
        if qty:
            weight_total = weight_each * qty
        method = "reference_weight"

    frozen = overrides.get("equipment")
    equipment = None
    if frozen:
        from pydantic import ValidationError
        from types import SimpleNamespace
        from app.schemas.equipment import EquipmentSnapshot
        from app.core.messages import error as api_error
        try:
            frozen = EquipmentSnapshot.model_validate(frozen).model_dump(mode="json")
        except ValidationError as exc:
            raise api_error(422, "equipment.snapshot_invalid") from exc
        equipment = SimpleNamespace(**frozen)
    else:
        equipment = match_equipment(row.description, db)
    if equipment and (frozen or product_type not in STEEL_PRODUCT_TYPES):
        product_type = "equipment"
        weight_each = equipment.weight_kg
        if qty:
            weight_total = weight_each * qty
        length_cm = meters_to_cm(overrides.get("length_m")) or equipment.length_cm
        width_cm = meters_to_cm(overrides.get("width_m")) or equipment.width_cm
        height_cm = meters_to_cm(overrides.get("height_m")) or equipment.height_cm
        if length_cm and width_cm and height_cm and qty:
            transport_vol = length_cm * width_cm * height_cm / 1_000_000 * qty
        method = "equipment_catalog"
        ref = None

    profile = match_profile(row.description, dims, db)
    if profile and not kg_per_m and product_type != "equipment":
        kg_per_m = profile.kg_per_meter

    if product_type not in {"equipment", "reference_item"} and (
        product_type == "standard_profile" or dims.profile_size
    ):
        product_type = "standard_profile"
        if not dims.length_m:
            messages.append("length_missing")
            status = "error"
        elif not kg_per_m:
            messages.append("kg_per_meter_missing")
            status = "needs_review"
        else:
            _, weight_total = calc_catalog_profile(kg_per_m, dims.length_m, qty or 1)
            weight_each = kg_per_m * dims.length_m
            method = "catalog_profile"
            outer_w = 0.22
            outer_h = 0.08
            transport_vol = transport_volume_outer(outer_w, outer_h, dims.length_m, qty or 1)
            length_cm = meters_to_cm(dims.length_m)
            width_cm = meters_to_cm(outer_w)
            height_cm = meters_to_cm(outer_h)

    elif product_type == "angle_profile" and (len(dims.values_m) >= 4 or wall_m):
        if wall_m and dims.width_m and dims.height_m and dims.length_m:
            leg_a, leg_b, thick, length_m = dims.width_m, dims.height_m, wall_m, dims.length_m
        else:
            leg_a, leg_b, thick, length_m = dims.values_m[:4]
        try:
            material_vol, weight_each = calc_angle_profile(leg_a, leg_b, thick, length_m, density)
            if qty:
                weight_total = weight_each * qty
            transport_vol = transport_volume_outer(leg_a, leg_b, length_m, qty or 1)
            length_cm = meters_to_cm(length_m)
            width_cm = meters_to_cm(leg_a)
            height_cm = meters_to_cm(leg_b)
            method = "angle_profile"
        except ValueError as exc:
            messages.append(str(exc))
            status = "error"

    elif product_type == "square_tube" and (len(dims.values_m) >= 4 or wall_m):
        if wall_m and dims.width_m and dims.height_m and dims.length_m:
            outer_w, outer_h, wall, length_m = dims.width_m, dims.height_m, wall_m, dims.length_m
        else:
            outer_w, outer_h, wall, length_m = dims.values_m[:4]
        try:
            material_vol, weight_each = calc_hollow_rect(outer_w, outer_h, wall, length_m, density)
            if qty:
                weight_total = weight_each * qty
            transport_vol = transport_volume_outer(outer_w, outer_h, length_m, qty or 1)
            length_cm = meters_to_cm(length_m)
            width_cm = meters_to_cm(outer_w)
            height_cm = meters_to_cm(outer_h)
            method = "hollow_rect"
        except ValueError:
            messages.append("wall_thickness_invalid")
            status = "error"

    elif product_type == "round_tube" and (diameter_m := dims.width_m or None) and wall_m and dims.length_m:
        # A round tube needs no height: the width *is* the diameter, and the
        # inside diameter follows from the wall thickness. Two measurements and a
        # thickness are enough, and asking for a third that adds nothing is only
        # an opportunity to fill in something wrong.
        outer_r = diameter_m / 2
        inner_r = outer_r - wall_m
        if inner_r <= 0:
            messages.append("wall_thickness_invalid")
            status = "error"
        else:
            material_vol, weight_each = calc_round_tube(outer_r, inner_r, dims.length_m, density)
            if qty:
                weight_total = weight_each * qty
            # For stowage the enclosing box counts, not the circle.
            transport_vol = transport_volume_outer(
                diameter_m, diameter_m, dims.length_m, qty or 1
            )
            length_cm = meters_to_cm(dims.length_m)
            width_cm = height_cm = meters_to_cm(diameter_m)
            method = "round_tube"

    elif product_type == "round_bar" and (diameter_m := dims.width_m or None) and dims.length_m:
        # Solid round. Until v1.37.1 this fell through to the block below and a
        # bar was weighed as a beam of d by d — 4/pi, that is 27% too heavy.
        radius = diameter_m / 2
        material_vol, weight_each = calc_round_bar(radius, dims.length_m, density)
        if qty:
            weight_total = weight_each * qty
        transport_vol = transport_volume_outer(diameter_m, diameter_m, dims.length_m, qty or 1)
        length_cm = meters_to_cm(dims.length_m)
        width_cm = height_cm = meters_to_cm(diameter_m)
        method = "round_bar"

    elif product_type in {"plate", "beam"} and len(dims.values_m) >= 3:
        w, h, length_m = dims.values_m[:3]
        material_vol, weight_each = calc_solid_block(length_m, w, h, density)
        if qty:
            weight_total = weight_each * qty
        transport_vol = transport_volume_outer(w, h, length_m, qty or 1)
        length_cm = meters_to_cm(length_m)
        width_cm = meters_to_cm(w)
        height_cm = meters_to_cm(h)
        method = "solid_block"

    elif product_type in {"equipment", "reference_item"}:
        if not qty:
            messages.append("quantity_missing")
            status = "error"

    elif product_type in WALL_PROFILE_TYPES:
        # The shape has a wall, but the thickness is missing. Falling through to
        # the solid block below is exactly what happened until v1.36.1: an L80x80x8
        # angle of 6 m weighed 301 kg instead of 57 — well over five times too
        # heavy, and nothing on screen betraying that a measurement was missing.
        # Better no figure than that figure.
        messages.append("wall_thickness_missing")
        status = "needs_review" if status == "ok" else status
        if dims.width_m and dims.height_m and dims.length_m:
            # The transport volume can be done: that is about the outside
            # measurements and not about how much steel is in it.
            transport_vol = transport_volume_outer(
                dims.width_m, dims.height_m, dims.length_m, qty or 1
            )

    elif material_obj and len(dims.values_m) >= 3:
        # Recognised material with three dimensions: compute as a solid block on
        # density.
        w, h, length_m = dims.values_m[:3]
        material_vol, weight_each = calc_solid_block(length_m, w, h, density)
        if qty:
            weight_total = weight_each * qty
        transport_vol = transport_volume_outer(w, h, length_m, qty or 1)
        length_cm = meters_to_cm(length_m)
        width_cm = meters_to_cm(w)
        height_cm = meters_to_cm(h)
        method = "solid_block"

    else:
        if not material_obj:
            messages.append("material_not_recognized")
            status = "needs_review" if status == "ok" else status
        if not qty:
            messages.append("quantity_missing")
            status = "error"

        # Not every consignment needs dimensions. "1500 litres of petrol" is
        # fully determined: the unit gives the volume, the density of the
        # recognised commodity gives the mass. Until v1.34.1 "dimensions_missing"
        # was reported here and weight and volume stayed empty, while everything
        # needed to work it out was on the screen. The units module existed, but
        # was used only by the dropdown and not by the calculation.
        #
        # Only with a recognised commodity: match_material falls back to the
        # density of steel, and 1500 litres times 7850 would look just as
        # confident as the answer that is right.
        if material_obj and qty:
            # A count of packages converts to nothing by itself — until the
            # description said what one package holds. "1000 jerricans of 25 l
            # of petrol" is 25000 litres, and with the catalogue's density that
            # is 18625 kg: everything needed was already on the screen. The
            # packaging around the contents is not, so the material volume
            # follows from the contents while the transport volume stays open
            # for the dimensions to answer.
            convert_qty, convert_unit, packed = qty, row.unit, False
            content_amount, content_unit = _split_package_content(package_content)
            if content_unit is not None and row_unit is not None \
                    and row_unit.dimension == Dimension.COUNT:
                convert_qty, convert_unit, packed = qty * content_amount, content_unit.code, True
            source_reference = density_reference(material_obj) if not overrides.get("material_density") else None
            converted = convert_units(
                convert_qty, convert_unit, density, material_obj.category,
                canonical_name=material_obj.canonical_name,
                form=overrides.get("cargo_form"),
                source_basis=source_reference.get("basis") if source_reference else None,
            )
            if converted.mass_kg is not None or converted.volume_m3 is not None:
                weight_total = converted.mass_kg
                material_vol = converted.volume_m3
                # For a liquid or bulk the entered volume is also the volume
                # carried; there is no packaging around it that the app knows of.
                transport_vol = None if packed else converted.volume_m3
                method = f"unit_{converted.basis.value}"
                density = converted.density_used_kg_m3 or density
                cargo_form = converted.form
                if packed and weight_total is not None:
                    weight_each = weight_total / qty

        if not dims.length_m and not weight_each and weight_total is None:
            messages.append("dimensions_missing")
            status = "needs_review" if status == "ok" else status

    if not material_name and ("staal" in row.description.lower() or "steel" in row.description.lower()):
        material_name = "steel"
        density = STEEL_DENSITY

    output_desc = overrides.get("output_description") or (
        " · ".join(filter(None, (equipment.specifications, frozen.get("asset_code") or frozen.get("container_number") or frozen.get("registration"), frozen.get("configuration")))) if frozen else equipment.specifications
        if equipment and product_type == "equipment"
        else build_output_description(row.description, product_type, dims, output_language)
    )

    dangerous_goods, dg_messages = detect_dangerous_goods(row.description)
    if overrides.get("dangerous_goods"):
        dangerous_goods = True
    messages.extend(dg_messages)
    detected_un_numbers = detect_un_numbers(row.description)
    # With an explicit UN number in the text there is nothing left to suggest.
    dg_name_candidates = (
        [] if detected_un_numbers
        else detect_name_candidates(row.description, output_language)
    )
    if overrides.get("weight_each_kg") is not None:
        weight_each = float(overrides["weight_each_kg"])
        if qty:
            weight_total = weight_each * qty
    elif overrides.get("weight_total_kg") is not None:
        weight_total = float(overrides["weight_total_kg"])
        if qty:
            weight_each = weight_total / qty

    if weight_total is not None and weight_total > 0 and "dimensions_missing" in messages:
        messages = ["transport_dimensions_missing" if message == "dimensions_missing" else message for message in messages]

    # Package outer dimensions define loading volume even without a material.
    if transport_vol is None and qty and row_unit and row_unit.dimension == Dimension.COUNT and all((length_cm, width_cm, height_cm)):
        transport_vol = length_cm * width_cm * height_cm * qty / 1_000_000

    reference = density_reference(material_obj, output_language) if material_obj and not overrides.get("material_density") else None
    if (reference and reference["kind"] == "published_reference" and weight_total is not None
            and row_unit and row_unit.dimension != Dimension.MASS
            and overrides.get("weight_total_kg") is None and overrides.get("weight_each_kg") is None):
        messages.append("density_reference_estimate")
        if status == "ok":
            status = "needs_review"

    return LineResult(
        line_id=line_id,
        raw=row.raw,
        description=row.description,
        output_description=output_desc,
        quantity=qty,
        unit=row.unit,
        material=material_name,
        material_category=material_obj.category if material_obj else None,
        cargo_form=cargo_form,
        material_density=density,
        density_reference=reference,
        product_type=product_type,
        dimensions={
            "values_m": dims.values_m,
            "profile_size": dims.profile_size,
            "length_m": dims.length_m,
        },
        length_cm=length_cm,
        width_cm=width_cm,
        height_cm=height_cm,
        weight_each_kg=round(weight_each, 2) if weight_each is not None else None,
        weight_total_kg=round(weight_total, 2) if weight_total is not None else None,
        material_volume_m3=round(material_vol, 6) if material_vol is not None else None,
        transport_volume_m3=round(transport_vol, 6) if transport_vol is not None else None,
        kg_per_meter=kg_per_m,
        status=status,
        messages=messages,
        confidence=0.7 if status == "needs_review" else (0.4 if status == "error" else 1.0),
        include=overrides.get("include", True),
        input_language=lang,
        calculation_method=method,
        dangerous_goods=dangerous_goods,
        detected_un_numbers=detected_un_numbers,
        dg_name_candidates=dg_name_candidates,
        package_content=package_content,
        equipment=frozen,
        equipment_role=overrides.get("equipment_role") or "cargo",
        container_line_id=overrides.get("container_line_id"),
        cargo_goods_id=overrides.get("cargo_goods_id"),
    )


def parse_and_calculate(
    text: str,
    db: Session,
    column_map: dict[str, int | None] | None = None,
    has_header: bool = False,
    input_language: str | None = None,
    output_language: str = "nl",
    mode: str = "continue",
    line_overrides: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    rows, mapping = parse_paste(text, column_map, has_header)
    overrides_by_id = {o.get("line_id"): o for o in (line_overrides or [])}
    lines: list[LineResult] = []
    for idx, row in enumerate(rows, start=1):
        line = process_line(
            idx, row, db, input_language, output_language, overrides_by_id.get(idx)
        )
        lines.append(line)
    from app.services.container_loading import assess
    prepared, _ = assess([asdict(line) for line in lines])
    if mode == "strict" and any(line["status"] in {"error", "needs_review"} for line in prepared):
        return {"success": False, "column_map": mapping, "lines": prepared, "totals": {},
                "errors": [line["messages"] for line in prepared if line["messages"]]}
    included = [l for l in lines if l.include]
    totals = {
        "line_count": len(lines),
        "included_count": len(included),
        "total_quantity": sum(l.quantity or 0 for l in included),
        "total_weight_kg": round(sum(l.weight_total_kg or 0 for l in included), 2),
        "total_material_volume_m3": round(sum(l.material_volume_m3 or 0 for l in included), 6),
        "total_transport_volume_m3": round(sum(l.get("transport_volume_m3") or 0 for l in prepared if l["include"]), 6),
        "warning_count": sum(1 for l in prepared if l["status"] in {"warning", "needs_review"}),
        "error_count": sum(1 for l in prepared if l["status"] == "error"),
    }
    return {
        "success": True,
        "column_map": mapping,
        "lines": prepared,
        "totals": totals,
        "errors": [],
    }
