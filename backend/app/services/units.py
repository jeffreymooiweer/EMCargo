"""Units, and converting between them with the help of density.

Until now the unit of a line was a free text field with "stuks" as the default.
Anyone entering 1200 litres of diesel got 1200 *pieces* of diesel, and had to
add the weight themselves. That is not so much a missing feature as a missing
concept: a quantity without a unit means nothing, and with a unit it means
exactly one thing.

The model is small on purpose. Every unit has a **dimension** — mass, volume,
length or count — and a factor to the base unit of that dimension (kilogram or
cubic metre). Between mass and volume lies exactly one bridge: the density of
the commodity. That makes every conversion this application needs a
multiplication, and means no table of substance-specific exceptions is required
anywhere.

Where this can go wrong, and why there is a ``DensityBasis`` here: 20 m³ of
gravel times the density of gravel is right, 20 m³ of steel times the density of
steel is right, and 20 m³ of *stacked* timber is neither — there is air in
between. The goods database carries no field saying what kind of density a
figure is; ``docs/data-sources.md`` claimed for years that it did. So that basis
is *derived* here from the category and reported as derived, not as established.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Dimension(str, Enum):
    """What a unit is about."""

    MASS = "mass"
    VOLUME = "volume"
    LENGTH = "length"
    COUNT = "count"


class DensityBasis(str, Enum):
    """What the figure in ``density_kg_m3`` of a commodity means.

    Derived from the category, not from the data itself. See the module note.
    """

    SOLID = "solid"          # the material itself, without voids
    BULK = "bulk"            # bulk: grains with air between them
    LIQUID = "liquid"
    STACKED = "stacked"      # stacked or bundled: air between the pieces
    EFFECTIVE = "effective"  # praktijkgemiddelde per pallet of collo
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Unit:
    """One unit: what it is about and how much of it goes into the base unit."""

    code: str
    dimension: Dimension
    # To kg for mass, to m³ for volume, to metres for length.
    factor: float
    # Short display after a figure, the way the article does it: "150 (sqm)".
    symbol: str


UNITS: dict[str, Unit] = {
    # Massa
    "kg": Unit("kg", Dimension.MASS, 1.0, "kg"),
    "ton": Unit("ton", Dimension.MASS, 1000.0, "t"),
    "g": Unit("g", Dimension.MASS, 0.001, "g"),
    "lb": Unit("lb", Dimension.MASS, 0.45359237, "lb"),
    # Volume
    "m3": Unit("m3", Dimension.VOLUME, 1.0, "m³"),
    "l": Unit("l", Dimension.VOLUME, 0.001, "L"),
    "hl": Unit("hl", Dimension.VOLUME, 0.1, "hL"),
    "ml": Unit("ml", Dimension.VOLUME, 0.000001, "mL"),
    # Length — for profiles and beams, where the weight per metre is known.
    "m": Unit("m", Dimension.LENGTH, 1.0, "m"),
    "cm": Unit("cm", Dimension.LENGTH, 0.01, "cm"),
    "mm": Unit("mm", Dimension.LENGTH, 0.001, "mm"),
    # Count. A package is not a physical unit; its weight can only come from the
    # input, never from a density.
    "pcs": Unit("pcs", Dimension.COUNT, 1.0, "st"),
    "pallet": Unit("pallet", Dimension.COUNT, 1.0, "pal"),
    "box": Unit("box", Dimension.COUNT, 1.0, "ds"),
    "drum": Unit("drum", Dimension.COUNT, 1.0, "vat"),
    # The jerrycan is a packaging ADR defines by name (1.2.1) and P001 admits
    # to 60 litres as a single packaging; a fuel consignment is counted in
    # them, so the lines step has to be able to say so.
    "jerrycan": Unit("jerrycan", Dimension.COUNT, 1.0, "jerrycan"),
    "ibc": Unit("ibc", Dimension.COUNT, 1.0, "IBC"),
    "bag": Unit("bag", Dimension.COUNT, 1.0, "zak"),
    "roll": Unit("roll", Dimension.COUNT, 1.0, "rol"),
    "bundle": Unit("bundle", Dimension.COUNT, 1.0, "bundel"),
}

# Which units a category normally uses, with the default first. The user can
# always pick something else — this is a suggestion, not a fence. A goods
# database of 400 substances in 16 categories always has exceptions, and getting
# stuck on an exception is worse than an odd unit.
SUGGESTED_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "liquid": ("l", "m3", "kg", "ton", "ibc", "drum", "jerrycan"),
    "chemical": ("kg", "l", "ton", "m3", "drum", "ibc", "jerrycan"),
    "agri": ("ton", "kg", "m3", "bag", "pallet"),
    "bulk_material": ("ton", "m3", "kg"),
    "ore_mineral": ("ton", "m3", "kg"),
    "waste": ("ton", "m3", "kg"),
    "construction": ("ton", "m3", "kg", "pcs", "pallet"),
    "concrete": ("ton", "m3", "kg"),
    "metal": ("kg", "ton", "pcs", "m", "bundle"),
    "wood": ("m3", "pcs", "m", "kg", "bundle"),
    "plastic": ("kg", "ton", "pcs", "pallet", "roll"),
    "paper": ("kg", "ton", "roll", "pallet", "pcs"),
    "textile": ("kg", "roll", "pcs", "pallet"),
    "insulation": ("m3", "pcs", "pallet", "kg"),
    "food": ("kg", "ton", "pallet", "box", "pcs"),
    "general_cargo": ("pcs", "pallet", "box", "kg"),
}

DEFAULT_SUGGESTED: tuple[str, ...] = ("pcs", "kg", "ton", "m3", "l", "pallet")

# What kind of density a category's figure is. Derived, and reported as derived
# — the data itself does not say.
BASIS_BY_CATEGORY: dict[str, DensityBasis] = {
    "liquid": DensityBasis.LIQUID,
    "chemical": DensityBasis.LIQUID,
    "agri": DensityBasis.BULK,
    "bulk_material": DensityBasis.BULK,
    "ore_mineral": DensityBasis.BULK,
    "waste": DensityBasis.BULK,
    "concrete": DensityBasis.SOLID,
    "metal": DensityBasis.SOLID,
    "plastic": DensityBasis.SOLID,
    "construction": DensityBasis.SOLID,
    "insulation": DensityBasis.SOLID,
    "wood": DensityBasis.STACKED,
    "paper": DensityBasis.SOLID,
    "textile": DensityBasis.EFFECTIVE,
    "food": DensityBasis.EFFECTIVE,
    "general_cargo": DensityBasis.EFFECTIVE,
}


# --- The form it travels in ------------------------------------------------
#
# The density of oak is 720 kg/m³ and that of steel 7850. Those are the
# densities of the material itself. A cubic metre of stacked planks, a cubic
# metre of loose firewood and a cubic metre of solid beam are three different
# weights of the same timber, and the difference is air.
#
# v1.35.0 solved that with a single hidden factor of 0.65 for all timber. That
# was an average describing nobody's load. Instead the user now picks the form,
# and the form carries the factor. The same goes for steel (plate versus scrap),
# plastic (granulate versus regrind) and paper (bales versus loose).
#
# **Where this choice does not apply.** For gravel, grain and ore the stored
# figure is already a bulk density: that substance is never carried other than
# in bulk and the database describes it in that state. Laying another bulk
# factor over it counts the air twice. The same holds for liquids and for the
# practical averages per pallet. The form is therefore only offered where the
# stored figure describes the substance itself — see ``form_applies``.
#
# The factors are practical values and not standards. They are here because
# ``seed_catalogs`` only fills the goods table when it is empty: new seed data
# never reaches an existing installation.


class CargoForm(str, Enum):
    """How the commodity sits on the vehicle."""

    SOLID = "solid"        # one piece, or made to measure with given dimensions
    SHEETS = "sheets"      # platen vlak op elkaar
    BUNDLED = "bundled"    # strak gebundeld of in pakket
    STACKED = "stacked"    # neatly stacked, with air between
    LOOSE = "loose"        # los gestort


# Which part of a cubic metre is actually material.
FILL_FACTOR: dict[CargoForm, float] = {
    CargoForm.SOLID: 1.0,
    CargoForm.SHEETS: 1.0,
    CargoForm.BUNDLED: 0.75,
    CargoForm.STACKED: 0.65,
    CargoForm.LOOSE: 0.45,
}

# Which forms belong to a category, with the default first. Everything stays
# selectable; this is a suggestion, just as with the units.
FORMS_BY_CATEGORY: dict[str, tuple[CargoForm, ...]] = {
    "wood": (CargoForm.STACKED, CargoForm.SOLID, CargoForm.SHEETS,
             CargoForm.BUNDLED, CargoForm.LOOSE),
    "metal": (CargoForm.SOLID, CargoForm.BUNDLED, CargoForm.STACKED, CargoForm.LOOSE),
    "plastic": (CargoForm.SOLID, CargoForm.LOOSE, CargoForm.BUNDLED, CargoForm.STACKED),
    "paper": (CargoForm.BUNDLED, CargoForm.SHEETS, CargoForm.STACKED, CargoForm.LOOSE),
    "construction": (CargoForm.SOLID, CargoForm.STACKED, CargoForm.LOOSE, CargoForm.BUNDLED),
    "concrete": (CargoForm.SOLID, CargoForm.LOOSE),
    "insulation": (CargoForm.SHEETS, CargoForm.STACKED, CargoForm.BUNDLED, CargoForm.SOLID),
    "textile": (CargoForm.BUNDLED, CargoForm.LOOSE, CargoForm.STACKED),
}

# Sheet material lies flat; there a cubic metre of stack is nearly a cubic metre
# of material. This only sets the default form — the user may always pick another.
SHEET_LIKE_WOOD = frozenset({
    "plywood", "chipboard", "osb", "mdf", "hdf", "hardboard", "softboard",
    "cork", "clt", "glulam",
})


def form_applies(category: str | None) -> bool:
    """Does the stored figure describe the substance itself, or the bulk state?

    Only in the first case is there still a form to lay over it. Gravel and
    grain already carry a bulk density; there a second factor would count the
    air twice.
    """
    return density_basis(category) in {DensityBasis.SOLID, DensityBasis.STACKED}


def available_forms(category: str | None) -> list[CargoForm]:
    """The forms belonging to this category, the default first."""
    if not form_applies(category):
        return []
    key = str(category or "").strip().lower()
    return list(FORMS_BY_CATEGORY.get(key, (CargoForm.SOLID, CargoForm.STACKED,
                                            CargoForm.BUNDLED, CargoForm.LOOSE)))


def default_form(category: str | None, canonical_name: str | None = None) -> CargoForm | None:
    """The form assumed when none is chosen."""
    forms = available_forms(category)
    if not forms:
        return None
    if str(category or "").lower() == "wood" and str(canonical_name or "").lower() in SHEET_LIKE_WOOD:
        return CargoForm.SHEETS
    return forms[0]


def get_form(value: str | None) -> CargoForm | None:
    try:
        return CargoForm(str(value or "").strip().lower())
    except ValueError:
        return None


def fill_factor(
    category: str | None, canonical_name: str | None = None, form: str | None = None
) -> float:
    """Which part of a cubic metre is material, given the chosen form."""
    if not form_applies(category):
        return 1.0
    chosen = get_form(form) or default_form(category, canonical_name)
    return FILL_FACTOR.get(chosen, 1.0) if chosen else 1.0


def effective_density(
    density_kg_m3: float | None,
    category: str | None,
    canonical_name: str | None = None,
    form: str | None = None,
) -> float | None:
    """The density of a cubic metre as it stands on the vehicle."""
    if density_kg_m3 is None:
        return None
    return density_kg_m3 * fill_factor(category, canonical_name, form)


def get_unit(code: str | None) -> Unit | None:
    """Look a unit up, including when it says 'M3', ' ton ' or 'liter'."""
    if not code:
        return None
    key = str(code).strip().lower().replace("³", "3").replace("²", "2")
    if key in UNITS:
        return UNITS[key]
    return _ALIASES.get(key)


# What people type, and what they mean. Set up generously because the old free
# text input has produced all sorts of things over the years that are still in
# stored consignments and simply have to keep working.
_ALIASES: dict[str, Unit] = {}
for _code, _names in {
    "kg": ("kilo", "kilos", "kilogram", "kilograms", "kgs", "kilogramm"),
    "ton": ("t", "tonne", "tonnes", "tons", "mt", "metric ton", "tonnen"),
    "g": ("gram", "grams", "gr", "gramm"),
    "lb": ("lbs", "pound", "pounds"),
    "m3": ("m^3", "cbm", "kubieke meter", "kubiek", "cubic meter", "cubic metre", "cbms"),
    "l": ("ltr", "liter", "liters", "litre", "litres", "lt"),
    "hl": ("hectoliter", "hectolitre"),
    "ml": ("milliliter", "millilitre"),
    "m": ("meter", "meters", "metre", "metres", "mtr"),
    "cm": ("centimeter", "centimetre"),
    "mm": ("millimeter", "millimetre"),
    "pcs": ("stuk", "stuks", "st", "pc", "piece", "pieces", "ea", "each", "stück", "stücke", "stk", "pièce", "pièces"),
    "pallet": ("pallets", "pal", "europallet", "europallets", "palette", "paletten", "palettes"),
    "box": ("boxes", "doos", "dozen", "ds", "karton", "kartons", "carton", "cartons", "kiste", "kisten", "boîte", "boîtes"),
    "drum": ("drums", "vat", "vaten", "fass"),
    "jerrycan": ("jerrycans", "jerrican", "jerricans", "kanister", "jerrycan 25l"),
    "ibc": ("ibcs", "ibc-tank", "container ibc"),
    "bag": ("bags", "zak", "zakken", "sack", "sacks", "big bag", "bigbag", "sack"),
    "roll": ("rolls", "rol", "rollen", "rolle"),
    "bundle": ("bundles", "bundel", "bundels", "bos", "bossen", "bund"),
}.items():
    for _name in _names:
        _ALIASES[_name] = UNITS[_code]


def suggested_units(category: str | None) -> list[str]:
    """The units that are the obvious ones for this category, the default first."""
    return list(SUGGESTED_BY_CATEGORY.get(str(category or "").strip().lower(), DEFAULT_SUGGESTED))


def default_unit(category: str | None) -> str:
    return suggested_units(category)[0]


def density_basis(category: str | None) -> DensityBasis:
    return BASIS_BY_CATEGORY.get(str(category or "").strip().lower(), DensityBasis.UNKNOWN)


@dataclass
class Converted:
    """What a quantity is in mass and volume, and what could not be worked out.

    ``mass_kg`` or ``volume_m3`` is None when the conversion cannot be made
    without guessing. That is an outcome, not an error: with 40 pallets and no
    weight per pallet the weight is unknown, and putting a 0 there would produce
    a total that looks fine and means nothing.
    """

    mass_kg: float | None = None
    volume_m3: float | None = None
    basis: DensityBasis = DensityBasis.UNKNOWN
    # Why one of the two stayed empty, as a machine-readable reason.
    missing: str | None = None
    # The density actually computed with, and the part of a cubic metre that is
    # material. With a stacked or bulk form that differs from the density of the
    # commodity itself, and the user should be able to see that.
    density_used_kg_m3: float | None = None
    fill_factor: float = 1.0
    form: str | None = None


def convert(
    quantity: float | None,
    unit_code: str | None,
    density_kg_m3: float | None = None,
    category: str | None = None,
    mass_per_item_kg: float | None = None,
    volume_per_item_m3: float | None = None,
    canonical_name: str | None = None,
    form: str | None = None,
    source_basis: str | None = None,
) -> Converted:
    """Convert an entered quantity to mass and volume.

    Density bridges mass and volume. When it is missing, only the side that
    follows directly from the unit is filled in.

    The form determines how much of a cubic metre is actually material: a cubic
    metre of stacked planks is not a cubic metre of timber. See ``fill_factor``.
    """
    basis = density_basis(category)
    chosen = get_form(form) or default_form(category, canonical_name)
    chosen_name = chosen.value if chosen else None
    factor = fill_factor(category, canonical_name, form)
    if source_basis is not None:
        # A traceable specimen or grade has an explicit density basis. Do not
        # infer liquid from "chemical", or stacked wood from its category.
        basis = DensityBasis(source_basis)
        chosen = (get_form(form) or CargoForm.SOLID) if basis == DensityBasis.SOLID else None
        chosen_name = chosen.value if chosen else None
        factor = FILL_FACTOR[chosen] if chosen else 1.0
    if density_kg_m3 is not None and factor != 1.0:
        density_kg_m3 = density_kg_m3 * factor
    unit = get_unit(unit_code)
    if quantity is None or unit is None:
        return Converted(basis=basis, missing="unit" if quantity is not None else "quantity")

    amount = float(quantity)
    if amount < 0:
        return Converted(basis=basis, missing="negative")

    if unit.dimension is Dimension.MASS:
        mass = amount * unit.factor
        volume = mass / density_kg_m3 if density_kg_m3 else None
        return Converted(mass, volume, basis, None if volume is not None else "density",
                         density_kg_m3, factor, chosen_name)

    if unit.dimension is Dimension.VOLUME:
        volume = amount * unit.factor
        mass = volume * density_kg_m3 if density_kg_m3 else None
        return Converted(mass, volume, basis, None if mass is not None else "density",
                         density_kg_m3, factor, chosen_name)

    if unit.dimension is Dimension.COUNT:
        # A count carries no physics in itself. Without a weight or volume per
        # item there is nothing to compute, and that is reported.
        mass = amount * mass_per_item_kg if mass_per_item_kg else None
        volume = amount * volume_per_item_m3 if volume_per_item_m3 else None
        if mass is None and volume is not None and density_kg_m3:
            mass = volume * density_kg_m3
        if volume is None and mass is not None and density_kg_m3:
            volume = mass / density_kg_m3
        missing = None if (mass is not None or volume is not None) else "per_item"
        return Converted(mass, volume, basis, missing, density_kg_m3, factor, chosen_name)

    # Length: only usable with a weight per metre, which the profiles table
    # supplies. That path runs via pipeline.py and not through here.
    return Converted(basis=basis, missing="length_needs_profile")


def format_quantity(quantity: float | None, unit_code: str | None) -> str:
    """"1200 L" — the figure with the symbol of its unit behind it.

    The article puts the unit small behind the value instead of reserving a
    column for it; this produces the text the interface does that with.
    """
    if quantity is None:
        return ""
    unit = get_unit(unit_code)
    number = f"{quantity:,.2f}".rstrip("0").rstrip(".").replace(",", " ")
    return f"{number} {unit.symbol}" if unit else number
