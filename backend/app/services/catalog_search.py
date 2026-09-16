import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.languages import pick
from app.models.user import Equipment, Material, Profile, ReferenceItem
from app.services.density_references import MEASURED_SOURCES, material_candidates
from app.services.parser.dimension_extractor import extract_dimensions
from app.services.parser.product_detector import detect_product_type

_SYNONYMS_PATH = Path(__file__).resolve().parents[1] / "config" / "search_synonyms.json"

# The suggestion the user clicks becomes the description on their document; it
# therefore belongs in the language they are working in.
PRODUCT_LABELS = {
    "angle_profile": {"nl": "hoekprofiel", "en": "angle profile", "de": "Winkelprofil", "fr": 'cornière'},
    "square_tube": {"nl": "kokerprofiel", "en": "square tube", "de": "Quadratrohr", "fr": 'tube carré'},
    "round_tube": {"nl": "buis", "en": "pipe", "de": "Rohr", "fr": 'tube'},
    "round_bar": {"nl": "ronde staf", "en": "round bar", "de": "Rundstab", "fr": 'barre ronde'},
    "plate": {"nl": "plaat", "en": "plate", "de": "Blech", "fr": 'tôle'},
    "beam": {"nl": "balk", "en": "beam", "de": "Träger", "fr": 'poutre'},
    "standard_profile": {"nl": "staalprofiel", "en": "steel profile", "de": "Stahlprofil", "fr": 'profilé en acier'},
    "concrete_slab": {"nl": "betonplaat", "en": "concrete slab", "de": "Betonplatte", "fr": 'dalle de béton'},
    "plywood": {"nl": "multiplex", "en": "plywood", "de": "Sperrholz", "fr": 'contreplaqué'},
    "pvc_pipe": {"nl": "pvc buis", "en": "pvc pipe", "de": "PVC-Rohr", "fr": 'tube en pvc'},
    "plastic_sheet": {"nl": "kunststof plaat", "en": "plastic sheet", "de": "Kunststoffplatte", "fr": 'plaque plastique'},
}

# Fallback for materials the database does not know as a label.
MATERIAL_LABELS = {
    "steel": {"nl": "staal", "en": "steel", "de": "Stahl", "fr": 'acier'},
    "stainless_steel": {"nl": "rvs", "en": "stainless steel", "de": "Edelstahl", "fr": 'acier inoxydable'},
    "aluminium": {"nl": "aluminium", "en": "aluminium", "de": "Aluminium", "fr": 'aluminium'},
    "copper": {"nl": "koper", "en": "copper", "de": "Kupfer", "fr": 'cuivre'},
    "brass": {"nl": "messing", "en": "brass", "de": "Messing", "fr": 'laiton'},
    "concrete": {"nl": "beton", "en": "concrete", "de": "Beton", "fr": 'béton'},
    "reinforced_concrete": {"nl": "gewapend beton", "en": "reinforced concrete",
                            "de": "Stahlbeton", "fr": 'béton armé'},
    "spruce": {"nl": "hout", "en": "wood", "de": "Holz", "fr": 'bois'},
    "hardwood": {"nl": "hardhout", "en": "hardwood", "de": "Laubholz", "fr": 'bois feuillu'},
    "plywood": {"nl": "multiplex", "en": "plywood", "de": "Sperrholz", "fr": 'contreplaqué'},
    "pvc": {"nl": "pvc", "en": "pvc", "de": "PVC", "fr": 'pvc'},
    "pe": {"nl": "pe", "en": "pe", "de": "PE", "fr": 'pe'},
    "pp": {"nl": "pp", "en": "pp", "de": "PP", "fr": 'pp'},
    "pom": {"nl": "pom", "en": "pom", "de": "POM", "fr": 'pom'},
    "nylon": {"nl": "nylon", "en": "nylon", "de": "Nylon", "fr": 'nylon'},
    "acrylic": {"nl": "plexiglas", "en": "acrylic", "de": "Acrylglas", "fr": 'acrylique'},
    "sand": {"nl": "zand", "en": "sand", "de": "Sand", "fr": 'sable'},
    "gravel": {"nl": "grind", "en": "gravel", "de": "Kies", "fr": 'gravier'},
}


def material_label(material: Material, language: str) -> str:
    """The name of a material in the requested language."""
    labels = json.loads(material.language_labels_json or "{}")
    return (
        pick(labels, language)
        or pick(MATERIAL_LABELS.get(material.canonical_name), language)
        or material.canonical_name
    )


def product_label(product_type: str, language: str) -> str:
    return pick(PRODUCT_LABELS.get(product_type), language) or product_type.replace("_", " ")


@dataclass
class SearchHit:
    id: str
    source: str
    label: str
    sublabel: str | None
    value: str
    score: float
    equipment: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "label": self.label,
            "sublabel": self.sublabel,
            "value": self.value,
            "score": round(self.score, 2),
            **({"equipment": self.equipment} if self.equipment else {}),
        }


def _load_aliases(raw: str) -> list[str]:
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []


def _flatten_synonym_sections(data: dict[str, Any]) -> dict[str, str]:
    """Build one map from nested sections (products, materials, …) or flat legacy json."""
    if not data:
        return {}
    if any(isinstance(v, dict) for v in data.values()):
        flat: dict[str, str] = {}
        for section in data.values():
            if isinstance(section, dict):
                for src, dst in section.items():
                    flat[src.lower()] = dst
        return flat
    return {str(k).lower(): str(v) for k, v in data.items()}


def _load_static_synonyms() -> dict[str, str]:
    if not _SYNONYMS_PATH.exists():
        return {}
    data = json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    return _flatten_synonym_sections(data)


def _db_synonyms(db: Session) -> dict[str, str]:
    """Add aliases from materials, references and equipment as search synonyms.

    In two passes, and that order is the point. A key is set with `setdefault`,
    so whoever gets there first keeps it. Had it all gone in one pass, the
    commodity that happened to come first in the database would win — and a mere
    *alias* of that commodity could thereby intercept the *own name* of another.
    Concretely: cauliflower once carried "broccoli" as an alias, so anyone typing
    "broccoli" ended up at cauliflower while broccoli is simply in the database.

    So first all the names — canonical name and the labels in the three
    languages — and only then the aliases. A name can no longer be overwritten by
    somebody else's alias, whatever order the rows were entered in.
    """
    synonyms: dict[str, str] = {}
    # Names a commodity has of its own. A name equal to its own target text does
    # not need replacing, but does need to be claimed: otherwise it is not in the
    # table and somebody else's alias takes it after all.
    reserved: set[str] = set()

    # Qualified source labels already carry the selected identity and state.
    # They have no aliases to expand and must not dominate the synonym map.
    materials = db.query(Material).filter(Material.active.is_(True), or_(Material.source.is_(None), Material.source.notin_(MEASURED_SOURCES))).all()
    references = db.query(ReferenceItem).filter(ReferenceItem.active.is_(True)).all()

    def register(keys: list[str], target: str, *, is_name: bool) -> None:
        for alias in keys:
            key = str(alias).strip().lower()
            if len(key) <= 2:
                continue
            if is_name:
                reserved.add(key)
            elif key in reserved:
                continue
            if key != target:
                synonyms.setdefault(key, target)

    for material in materials:
        labels = json.loads(material.language_labels_json or "{}")
        register(
            [material.canonical_name, *labels.values()],
            material_label(material, "nl").lower(),
            is_name=True,
        )

    for item in references:
        labels = json.loads(item.language_labels_json or "{}")
        register(
            [item.canonical_name, *labels.values()],
            (labels.get("nl") or item.canonical_name).lower(),
            is_name=True,
        )

    for material in materials:
        register(
            _load_aliases(material.aliases_json),
            material_label(material, "nl").lower(),
            is_name=False,
        )

    for item in references:
        labels = json.loads(item.language_labels_json or "{}")
        register(
            _load_aliases(item.aliases_json),
            (labels.get("nl") or item.canonical_name).lower(),
            is_name=False,
        )

    for equip in db.query(Equipment).filter(Equipment.active.is_(True)).all():
        target = (equip.specifications or "").strip().lower()
        if not target:
            continue
        for alias in _load_aliases(equip.aliases_json):
            key = str(alias).strip().lower()
            if len(key) > 3 and key != target:
                synonyms.setdefault(key, target)

    return synonyms


def _merged_synonyms(db: Session | None) -> dict[str, str]:
    merged = dict(_load_static_synonyms())
    if db is not None:
        for src, dst in _db_synonyms(db).items():
            merged.setdefault(src, dst)
    return merged


#: Letters that still belong to a word. The re module's `\b` does not count é and
#: ü as word characters, which would let "kupfer" in the middle of
#: "Kupferkathoden" be replaced after all.
_WORD_CHAR = r"[0-9A-Za-zÀ-ÖØ-öø-ÿ]"


@lru_cache(maxsize=4096)
def _synonym_pattern(src: str) -> re.Pattern[str]:
    """The synonym as a whole word, not as a run of letters inside a word."""
    left = rf"(?<!{_WORD_CHAR})" if re.match(_WORD_CHAR, src[:1] or " ") else ""
    right = rf"(?!{_WORD_CHAR})" if re.match(_WORD_CHAR, src[-1:] or " ") else ""
    return re.compile(left + re.escape(src) + right, re.IGNORECASE)


def normalize_synonyms(text: str, db: Session | None = None) -> tuple[str, list[tuple[str, str]]]:
    """Replace known synonyms; return normalised text plus applied replacements.

    On whole words. That it once worked on runs of letters went unnoticed while
    the goods database was small — but *every* alias of *every* commodity is a
    synonym here, so the more commodities, the greater the chance that a key
    happens to sit inside another word. "cashew" contains "as" (ash),
    "Kupferkathoden" contains "kupfer" *and* "per" (perchloroethylene). The query
    was then rewritten into nonsense and the commodity the user typed did not
    come out on top.
    """
    synonyms = _merged_synonyms(db)
    if not synonyms:
        return text, []
    lower = text.lower()
    applied: list[tuple[str, str]] = []
    for src, dst in sorted(synonyms.items(), key=lambda x: len(x[0]), reverse=True):
        # The cheap test first. There are well over four thousand synonyms and
        # for nearly all of them a substring test settles the answer; a regex
        # over all four thousand cost 1.4 seconds per search.
        if src not in lower:
            continue
        pattern = _synonym_pattern(src)
        if pattern.search(text):
            # A lambda as the replacement: a target text with \1 or \g in it is a
            # name, not a group reference.
            text = pattern.sub(lambda _match: dst, text, count=1)
            lower = text.lower()
            applied.append((src, dst))
    return text, applied


def _dimension_suffix(text: str) -> str:
    """Keep the dimension/length part of the query for suggestion values."""
    dim_match = re.search(
        r"(\d+(?:[.,]\d+)?\s*[x×]\s*\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?){0,2}(?:\s*[x×]\s*\d+(?:[.,]\d+)?)?\s*(?:mm|cm|m)?)",
        text,
        re.IGNORECASE,
    )
    if dim_match:
        return dim_match.group(1).strip()
    profile_dim = re.search(
        r"\b((?:UNP|UPN|UPE|IPE|HEA|HEB|HEM|IPN|INP|SHS|RHS|CHS)\s*\d+.*?)$",
        text,
        re.IGNORECASE,
    )
    if profile_dim:
        return profile_dim.group(1).strip()
    length = re.search(r"(?:l\s*[=:]?\s*)?(\d+(?:[.,]\d+)?\s*(?:mm|cm|m)\b)", text, re.IGNORECASE)
    if length:
        return length.group(0).strip()
    return ""


def _merge_label(base: str, original_query: str) -> str:
    suffix = _dimension_suffix(original_query)
    if not suffix:
        return base.strip()
    if suffix.lower() in base.lower():
        return base.strip()
    return f"{base.strip()} {suffix}".strip()


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


def _score_tokens(query_tokens: set[str], haystack: str) -> float:
    if not query_tokens:
        return 0.0
    hay_tokens = _tokens(haystack)
    if not hay_tokens:
        return 0.0
    overlap = len(query_tokens & hay_tokens)
    score = overlap / max(len(query_tokens), 1)
    hay_lower = haystack.lower()
    joined = " ".join(query_tokens)
    if joined in hay_lower or hay_lower in joined:
        score += 2
    return score


def _substring_alias_score(query_lower: str, aliases: list[str]) -> float:
    best = 0.0
    for alias in aliases:
        alias_lower = str(alias).strip().lower()
        if not alias_lower or len(alias_lower) < 2:
            continue
        if alias_lower in query_lower:
            best = max(best, 2.5 + len(alias_lower) / max(len(query_lower), 1))
    return best


def _collect_terms(*parts: str | None) -> str:
    return " ".join(p for p in parts if p)


def _material_terms(material: Material) -> list[str]:
    labels = json.loads(material.language_labels_json or "{}")
    return [
        material.canonical_name,
        *_load_aliases(material.aliases_json),
        *labels.values(),
    ]


def _search_equipment(db: Session, query: str, normalized: str, query_tokens: set[str]) -> list[SearchHit]:
    from app.services.equipment import details, snapshot
    hits: list[SearchHit] = []
    for item in db.query(Equipment).filter(Equipment.active.is_(True)).all():
        data = details(item)
        labels = json.loads(item.language_labels_json or "{}")
        alias_list = [
            item.specifications,
            *_load_aliases(item.aliases_json),
            *labels.values(),
            item.asset_code or "", item.container_number or "", data["registration"], data["serial_number"],
            data["brand"], data["model_name"],
        ]
        terms = _collect_terms(*alias_list)
        score = max(
            _score_tokens(query_tokens, terms),
            _substring_alias_score(query.lower(), alias_list),
            _substring_alias_score(normalized.lower(), alias_list),
        )
        norm_lower = normalized.lower()
        if "forklift" in norm_lower:
            if "forklift" in terms.lower():
                score += 5
            elif score < 2:
                continue
        if score <= 0:
            continue
        label = item.specifications
        hits.append(
            SearchHit(
                id=f"equipment:{item.id}",
                source="equipment",
                label=label,
                sublabel=" · ".join(filter(None, [item.asset_code or item.container_number, f"{item.weight_kg:g} kg"])),
                value=_merge_label(label, query),
                score=score,
                equipment=snapshot(item),
            )
        )
    return hits


def _search_profiles(db: Session, query: str, normalized: str, query_tokens: set[str], dims) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for profile in db.query(Profile).filter(Profile.active.is_(True)).all():
        label = f"{profile.profile_type} {profile.size_label}"
        alias_list = [label, profile.size_label, *_load_aliases(profile.aliases_json), profile.material or ""]
        terms = _collect_terms(*alias_list)
        score = max(
            _score_tokens(query_tokens, terms),
            _substring_alias_score(query.lower(), alias_list),
            _substring_alias_score(normalized.lower(), alias_list),
        )
        if dims.profile_size and dims.profile_size.lower() in terms.lower():
            score += 4
        if score <= 0:
            continue
        hits.append(
            SearchHit(
                id=f"profile:{profile.id}",
                source="profile",
                label=label,
                sublabel=f"{profile.kg_per_meter} kg/m · {profile.material}",
                value=_merge_label(label, query),
                score=score,
            )
        )
    return hits


def _material_names(material: Material) -> set[str]:
    """The names the commodity has of its own, without the aliases."""
    labels = json.loads(material.language_labels_json or "{}")
    return {material.canonical_name.lower(), *(str(v).strip().lower() for v in labels.values())}


def _search_materials(db: Session, query: str, query_tokens: set[str]) -> list[tuple[Material, float]]:
    lower = query.lower()
    matched: list[tuple[Material, float]] = []
    for material in material_candidates(db, query):
        terms = _material_terms(material)
        score = max(_score_tokens(query_tokens, _collect_terms(*terms)), _substring_alias_score(lower, terms))
        # Whoever types exactly the name of a commodity means that commodity.
        # Without this precedence, *another* commodity carrying that name as an
        # alias scores equally high and the order in the database decides —
        # cauliflower carried "broccoli" and came before broccoli in the table, so
        # cauliflower won.
        if lower.strip() in _material_names(material):
            score += 1
        if score > 0:
            matched.append((material, score))
    matched.sort(key=lambda x: x[1], reverse=True)
    return matched[:4]


def _material_hits(
    query: str, materials_scored: list[tuple[Material, float]], language: str
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for material, score in materials_scored:
        display = material_label(material, language)
        density = material.density_kg_m3
        hits.append(
            SearchHit(
                id=f"material:{material.canonical_name}",
                source="material",
                label=display,
                sublabel=f"{density:g} kg/m³" if density else None,
                value=_merge_label(display, query),
                score=score + 0.5,
            )
        )
    return hits


def _search_reference(
    db: Session, query: str, normalized: str, query_tokens: set[str], language: str
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for item in db.query(ReferenceItem).filter(ReferenceItem.active.is_(True)).all():
        labels = json.loads(item.language_labels_json or "{}")
        alias_list = [item.canonical_name, *_load_aliases(item.aliases_json), *labels.values()]
        terms = _collect_terms(*alias_list)
        score = max(
            _score_tokens(query_tokens, terms),
            _substring_alias_score(query.lower(), alias_list),
            _substring_alias_score(normalized.lower(), alias_list),
        )
        if score <= 0:
            continue
        display = pick(labels, language) or item.canonical_name
        hits.append(
            SearchHit(
                id=f"reference:{item.id}",
                source="reference",
                label=display,
                sublabel=f"{item.reference_weight_kg} kg",
                value=_merge_label(display, query),
                score=score + 1,
            )
        )
    return hits


def _template_suggestions(
    query: str, normalized: str, materials: list[Material], db: Session, language: str
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    product_type = detect_product_type(normalized)
    if not product_type:
        return hits

    product_name = product_label(product_type, language)
    suffix = _dimension_suffix(query)

    if materials:
        for material in materials:
            mat_name = material_label(material, language)
            mat_lower = mat_name.lower()
            prod_lower = product_name.lower()
            if mat_lower == prod_lower or prod_lower in mat_lower:
                base = mat_name
            else:
                base = f"{mat_name} {product_name}".strip()
            value = f"{base} {suffix}".strip() if suffix else base
            hits.append(
                SearchHit(
                    id=f"template:{material.canonical_name}:{product_type}",
                    source="template",
                    label=base.title() if mat_name.islower() else base,
                    sublabel=f"{material.density_kg_m3:g} kg/m³" if material.density_kg_m3 else None,
                    value=value,
                    score=8.0,
                )
            )
    else:
        base = product_name
        value = f"{base} {suffix}".strip() if suffix else base
        hits.append(
            SearchHit(
                id=f"template::{product_type}",
                source="template",
                label=base.title(),
                sublabel=None,
                value=value,
                score=6.0,
            )
        )

    _, applied = normalize_synonyms(query, db)
    if applied and hits:
        hits[0].score = max(hits[0].score, 9.0)
    return hits


def search_catalog(
    db: Session, query: str, limit: int = 25, language: str = "nl"
) -> list[dict[str, Any]]:
    query = (query or "").strip()
    if len(query) < 2:
        return []

    normalized, _ = normalize_synonyms(query, db)
    query_tokens = _tokens(normalized) | _tokens(query)
    dims = extract_dimensions(normalized)

    materials_scored = _search_materials(db, normalized, query_tokens)
    hits: list[SearchHit] = []
    hits.extend(
        _template_suggestions(query, normalized, [m for m, _ in materials_scored], db, language)
    )
    hits.extend(_material_hits(query, materials_scored, language))
    hits.extend(_search_equipment(db, query, normalized, query_tokens))
    hits.extend(_search_profiles(db, query, normalized, query_tokens, dims))
    hits.extend(_search_reference(db, query, normalized, query_tokens, language))

    seen: set[str] = set()
    unique: list[SearchHit] = []
    for hit in sorted(hits, key=lambda h: h.score, reverse=True):
        key = hit.value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
        if len(unique) >= limit:
            break

    return [h.to_dict() for h in unique]
