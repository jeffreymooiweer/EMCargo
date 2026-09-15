"""Compliance checks for dangerous goods: ADR 1.1.3.6 points, ADR 7.5.2 mixed
loading, the LQ/EQ limits of chapters 3.4 and 3.5, and IATA Table 9.3.A
segregation plus the Q value (5.0.2.11).

The results are guidance and warnings — not a legal determination. The
qualified person remains responsible (see TERMS.nl.md).
"""

import json
import re
from decimal import ROUND_CEILING, Decimal
from functools import lru_cache
from typing import Any

from app.core.config import get_settings
from app.core.languages import normalise, pick
from app.services.dg import amendment_42_24, dangerous_goods_list, database
from app.services.dg.autofill import rid_marking_prescribed
from app.services.dg.package_marking import check_package_marking
from app.services.dg.database import adn_loading_measures
from app.services.quantities import parse_number
from app.services.regulatory_manifest import stale_rule_sets, summary
from app.services.dg.enrichment import (
    EXCEPTED_QUANTITY_LIMITS,
    imdg_code_text,
    imdg_segregation_codes_for,
    parse_hazards,
    segregation_group_label,
    segregation_groups_for,
    segregation_provisions,
)


@lru_cache
def get_compliance_rules() -> dict[str, Any]:
    path = get_settings().config_dir / "dg_compliance.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lang(language: str) -> str:
    return normalise(language)


def _num(value: Any) -> float | None:
    """Parse one scalar quantity ('333', '5 kg', '12,5 L', '1.250,5 L').

    The sign counts: '-5 L' is -5, not 5. A negative quantity has to surface as
    an error rather than being silently made positive. Thousands separators
    are read as such (see ``services.quantities``): '1.250,5' is 1250.5, not
    1.25 — the reading that, until v1.190.0, put a consignment a thousandfold
    under its exemption limit.
    """
    return parse_number(value)


def _primary_class(product: dict[str, Any]) -> str:
    return str(product.get("class") or "").strip().upper()


def _hazard_tokens(product: dict[str, Any]) -> list[str]:
    """Every hazard class of a product: primary hazard plus subsidiary risks."""
    tokens: list[str] = []
    for raw in [product.get("class"), product.get("subsidiary_risks")]:
        for token in re.split(r"[,;/\s()+]+", str(raw or "")):
            token = token.strip().upper()
            if token:
                tokens.append(token)
    return tokens


def _is_class1(token: str) -> bool:
    return bool(re.match(r"^1(\.\d)?[A-S]?$", token)) and not token.startswith(("1.4S",))


def _compat_group(product: dict[str, Any]) -> str | None:
    """Compatibility group of a class 1 product (1.4G → 'G', for instance).

    The group lives in Table A in the classification code, not in the class
    column: for explosives that column only says "1". Hence the classification
    code is read first. Until v1.40.1 the ADR side looked only at the class
    field with a tight anchor, so 7.5.2.2 did not fire the moment the division
    did not happen to be in there.
    """
    for raw in (product.get("classification_code"), product.get("class"), product.get("subsidiary_risks")):
        match = re.search(r"\b1\.\d\s*([A-HJ-NPS])\b", str(raw or "").upper())
        if match:
            return match.group(1)
    return None


def _matches_iata_key(token: str, key: str) -> bool:
    """Match a hazard token against a 9.3.A key ('1', '2.1', '4.3', …)."""
    if key == "1":
        return _is_class1(token)
    return token == key or token.startswith(f"{key}")


def _product_label(entry: dict[str, Any], product: dict[str, Any], index: int) -> str:
    un = str(product.get("un_number") or "").strip()
    name = str(product.get("proper_shipping_name") or "").strip()
    base = " ".join(x for x in [f"UN {un}" if un else "", name] if x)
    label = base or f"{entry.get('vehicle') or entry.get('line_id') or '?'} #{index + 1}"
    # Only a trip sets this, and only a trip needs it: on one vehicle two
    # customers may both ship UN 1263, and "these two may not travel together"
    # is unusable if the reader cannot tell which pallet to take off. A single
    # consignment carries no such key and reads exactly as it always did.
    consignment = str(entry.get("consignment") or "").strip()
    return f"{consignment} — {label}" if consignment else label


def _iter_products(entries: list[dict[str, Any]]):
    for entry in entries:
        for index, product in enumerate(entry.get("products") or []):
            yield entry, index, product


#: The road, rail and inland waterway regimes each have a 1.1.3.6 and a mixed
#: loading chapter, but they are not the same texts. EMCargo carries the ADR
#: tables; those of RID and ADN are not in it. Presenting that silently as a
#: "RID result" gives the user a certainty that does not exist, so the basis is
#: named the moment it differs from the chosen profile.
LAND_PROFILES = ("ADR", "RID", "ADN")

BASIS_NOTE = {
    "nl": "Berekend met de tabellen van het ADR. {other} kent een eigen "
          "{section}; die staat niet in EMCargo. Gebruik deze uitkomst als "
          "indicatie en toets hem aan de tekst die voor jouw traject geldt.",
    "en": "Computed with the ADR tables. {other} has its own {section}, which "
          "EMCargo does not hold. Treat this as indicative and check it "
          "against the text that applies to your leg.",
    "de": "Mit den Tabellen des ADR berechnet. {other} hat einen eigenen "
          "{section}, den EMCargo nicht enthält. Nehmen Sie das Ergebnis als "
          "Anhaltspunkt und prüfen Sie es an dem für Ihre Strecke geltenden Text.", "fr": "Calculé avec les tableaux de l'ADR. Le {other} possède son propre {section}, dont EMCargo ne dispose pas. Prenez ce résultat à titre indicatif et vérifiez-le dans le texte applicable à votre trajet."}

# 7.5.2 no longer needs the blanket hedge above. RID's 7.5.2.1 was read in
# v1.38.0 and is word-identical to the ADR's, footnotes included; a rail-only
# selection is evaluated against RID's own 7.5.2.2 table (v1.41.0) under its
# own name. What is left to say when road and rail are combined is the one
# difference: 7.5.2.2 is then shown from the road table, which additionally
# carries compatibility group A — the rail table does not.
RID_MIXED_NOTE = {
    "nl": "Voor het spoortraject: 7.5.2.1 is in ADR en RID woordelijk gelijk "
          "(gelezen, v1.38.0). De 7.5.2.2-tabel hierboven is die van het ADR, "
          "die ook compatibiliteitsgroep A kent; het RID-eigen 7.5.2.2 kent "
          "groep A niet — een lading met groep A valt op het spoor buiten de "
          "tabel.",
    "en": "For the rail leg: 7.5.2.1 is word-identical in ADR and RID (read, "
          "v1.38.0). The 7.5.2.2 table above is the ADR's, which additionally "
          "carries compatibility group A; RID's own 7.5.2.2 does not — a load "
          "with group A falls outside the table on rail.",
    "de": "Für die Schienenstrecke: 7.5.2.1 ist in ADR und RID wortgleich "
          "(gelesen, v1.38.0). Die obige 7.5.2.2-Tabelle ist die des ADR, die "
          "auch die Verträglichkeitsgruppe A kennt; das RID-eigene 7.5.2.2 "
          "kennt Gruppe A nicht — eine Ladung mit Gruppe A fällt auf der "
          "Schiene aus der Tabelle.",
    "fr": "Pour le trajet ferroviaire : le 7.5.2.1 est mot pour mot identique "
          "dans l'ADR et le RID (lu, v1.38.0). Le tableau 7.5.2.2 ci-dessus "
          "est celui de l'ADR, qui connaît aussi le groupe de compatibilité A ; "
          "le 7.5.2.2 propre au RID ne le connaît pas — un chargement du "
          "groupe A sort du tableau sur le rail."}

# And ADN is not hedged either: its mixed loading prohibitions are its own
# chapter — 7.1.4.2 (bulk), 7.1.4.3 (packages in holds, applied since v1.59.0),
# 7.1.4.4/7.1.4.5 (containers) and 7.1.4.10 (foodstuffs, special provision
# 802) — read in the English and Dutch editions, which agree, and reported as
# their own findings. The note only has to say the 7.5.2 outcome is not the
# water's answer.
ADN_MIXED_NOTE = {
    "nl": "De 7.5.2-uitkomst geldt niet voor het watertraject: het ADN kent "
          "eigen samenladingsverboden — 7.1.4.2 (losgestort), 7.1.4.3 (colli "
          "in laadruimen), 7.1.4.4/7.1.4.5 (containers) en 7.1.4.10 "
          "(levensmiddelen, BV 802) — en die staan als eigen bevindingen, "
          "onder ADN-nummer, in dit paneel.",
    "en": "The 7.5.2 outcome does not apply to the water leg: ADN has its own "
          "mixed loading prohibitions — 7.1.4.2 (bulk), 7.1.4.3 (packages in "
          "holds), 7.1.4.4/7.1.4.5 (containers) and 7.1.4.10 (foodstuffs, "
          "special provision 802) — reported as their own findings, under "
          "their ADN numbers, in this panel.",
    "de": "Das 7.5.2-Ergebnis gilt nicht für die Wasserstrecke: das ADN hat "
          "eigene Zusammenladeverbote — 7.1.4.2 (lose Schüttung), 7.1.4.3 "
          "(Versandstücke in Laderäumen), 7.1.4.4/7.1.4.5 (Container) und "
          "7.1.4.10 (Lebensmittel, Sondervorschrift 802) — die als eigene "
          "Befunde unter ihren ADN-Nummern in diesem Panel stehen.",
    "fr": "Le résultat du 7.5.2 ne vaut pas pour le trajet fluvial : l'ADN a "
          "ses propres interdictions de chargement en commun — 7.1.4.2 (vrac), "
          "7.1.4.3 (colis dans les cales), 7.1.4.4/7.1.4.5 (conteneurs) et "
          "7.1.4.10 (denrées alimentaires, disposition spéciale 802) — "
          "présentées comme constatations propres, sous leurs numéros ADN, "
          "dans ce panneau."}

# For 1.1.3.6 the hedge above is no longer the truth, and saying less than we
# know is its own kind of wrong. RID 1.1.3.6.3 sets out the same five transport
# categories with the same figures (0, 20, 333, 1000, unlimited) and RID
# 1.1.3.6.4 the same multipliers — 50, 3 and 1 — against the same calculated
# value of 1000. What differs is the unit of account: RID counts per wagon or
# large container, ADR per transport unit. Read from RID 2025 p. 29 — and read
# further in v1.124.0: what the number *governs* differs too. RID 1.1.3.6.3
# opens "Where, in accordance with 1.1.3.1 (c), dangerous goods ... are
# carried", and 1.1.3.1 (c) (p. 27, confirmed in the German edition) is the
# exemption for carriage ancillary to an enterprise's main activity, at most
# 450 litres per packaging and never class 7. RID has no general small-load
# relief the way ADR 1.1.3.6 grants one; staying under 1000 relieves a rail
# consignment of nothing unless the carriage itself is that ancillary case.
RID_POINTS_NOTE = {
    "nl": "RID 1.1.3.6.3 en 1.1.3.6.4 schrijven dezelfde vervoerscategorieën, "
          "dezelfde factoren (50, 3 en 1) en dezelfde waarde van 1000 voor als "
          "het ADR; het RID rekent per wagen of grote container, het ADR per "
          "vervoerseenheid. Wat de uitkomst betekent verschilt wél: RID "
          "1.1.3.6 begrenst uitsluitend de vrijstelling van 1.1.3.1 (c) — "
          "vervoer door ondernemingen als nevenactiviteit van hun "
          "hoofdbedrijvigheid, ten hoogste 450 liter per verpakking, nooit "
          "klasse 7. Een algemene kleine-hoeveelhedenvrijstelling zoals ADR "
          "1.1.3.6 kent het RID niet: onder de 1000 blijven ontheft een "
          "spoorzending nergens van, tenzij het vervoer zelf dat nevengeval is.",
    "en": "RID 1.1.3.6.3 and 1.1.3.6.4 prescribe the same transport categories, "
          "the same factors (50, 3 and 1) and the same calculated value of 1000 "
          "as ADR; RID counts per wagon or large container, ADR per transport "
          "unit. What the outcome means differs: RID 1.1.3.6 only bounds the "
          "exemption of 1.1.3.1 (c) — carriage by enterprises ancillary to "
          "their main activity, at most 450 litres per packaging, never "
          "class 7. RID has no general small-load relief the way ADR 1.1.3.6 "
          "grants one: staying under 1000 relieves a rail consignment of "
          "nothing unless the carriage itself is that ancillary case.",
    "de": "RID 1.1.3.6.3 und 1.1.3.6.4 schreiben dieselben "
          "Beförderungskategorien, dieselben Faktoren (50, 3 und 1) und "
          "denselben berechneten Wert von 1000 vor wie das ADR; das RID "
          "rechnet je Wagen oder Großcontainer, das ADR je "
          "Beförderungseinheit. Was das Ergebnis bedeutet, unterscheidet "
          "sich: RID 1.1.3.6 begrenzt ausschließlich die Freistellung nach "
          "1.1.3.1 (c) — Beförderungen von Unternehmen in Verbindung mit "
          "ihrer Haupttätigkeit, höchstens 450 Liter je Verpackung, nie "
          "Klasse 7. Eine allgemeine Kleinmengen-Freistellung wie ADR 1.1.3.6 "
          "kennt das RID nicht: unter 1000 zu bleiben stellt eine "
          "Eisenbahnsendung von nichts frei, es sei denn, die Beförderung "
          "selbst ist dieser Nebenfall.",
    "fr": "Les 1.1.3.6.3 et 1.1.3.6.4 du RID prescrivent les mêmes catégories "
          "de transport, les mêmes facteurs (50, 3 et 1) et la même valeur "
          "calculée de 1000 que l'ADR ; le RID compte par wagon ou grand "
          "conteneur, l'ADR par unité de transport. Ce que le résultat "
          "signifie diffère : le 1.1.3.6 du RID borne uniquement l'exemption "
          "du 1.1.3.1 (c) — transports effectués par des entreprises en "
          "marge de leur activité principale, au plus 450 litres par "
          "emballage, jamais la classe 7. Le RID ne connaît pas d'exemption "
          "générale de petites quantités comme l'ADR 1.1.3.6 : rester sous "
          "1000 n'exempte un envoi ferroviaire de rien, sauf si le transport "
          "est lui-même ce cas accessoire."}

# ADN does not have a points system at all. Its 1.1.3.6.1 exempts a consignment
# in packages when the gross mass of everything stays under 3000 kg and no class
# exceeds its own figure. An ADR points total is therefore not an approximation
# of the ADN answer — it answers a different question — so the two are reported
# separately rather than one standing in for the other.
ADN_POINTS_NOTE = {
    "nl": "Let op: het ADN kent geen puntentelling. ADN 1.1.3.6.1 stelt vrij op "
          "grond van de totale brutomassa (ten hoogste 3000 kg) en een eigen "
          "grens per klasse. Deze punten gelden voor het wegtraject; de "
          "ADN-uitkomst staat er los van in het paneel.",
    "en": "Note: ADN has no points calculation. ADN 1.1.3.6.1 exempts on total "
          "gross mass (at most 3,000 kg) and its own limit per class. These "
          "points apply to the road leg; the ADN outcome is reported separately "
          "in the panel.",
    "de": "Hinweis: das ADN kennt keine Punkteberechnung. ADN 1.1.3.6.1 stellt "
          "anhand der Gesamtbruttomasse (höchstens 3000 kg) und einer eigenen "
          "Grenze je Klasse frei. Diese Punkte gelten für die Straßenstrecke; "
          "das ADN-Ergebnis wird im Panel gesondert ausgewiesen.", "fr": "Attention : l'ADN ne connaît pas de calcul de points. Le 1.1.3.6.1 de l'ADN exempte sur la masse brute totale (3 000 kg au plus) et sur une limite propre à chaque classe. Ces points valent pour le trajet routier ; le résultat ADN est présenté séparément dans le panneau."}


def basis_note(profiles: list[str] | None, section: str, language: str) -> str | None:
    """A note for when an ADR table is used for RID or ADN.

    For 1.1.3.6 the basis has since been read in the official texts and no
    longer needs hedging: RID computes the same way, ADN computes something
    entirely different. For the remaining chapters the old, cautious note still
    stands — those have not been read yet.
    """
    selected = {p.upper() for p in (profiles or [])}
    other = sorted(selected & {"RID", "ADN"})
    if not other:
        return None
    if section == "1.1.3.6":
        parts = []
        if "RID" in other:
            parts.append(pick(RID_POINTS_NOTE, language))
        if "ADN" in other:
            parts.append(pick(ADN_POINTS_NOTE, language))
        return " ".join(parts)
    if section == "7.5.2":
        # A rail-only selection is evaluated against RID's own tables and an
        # inland-only selection against ADN's own chapter — neither needs a
        # caveat about a table that was not used. The note is for combined
        # selections, where the outcome above belongs to one leg only.
        parts = []
        if "RID" in other and "ADR" in selected:
            parts.append(pick(RID_MIXED_NOTE, language))
        if "ADN" in other and (selected & {"ADR", "RID"}):
            parts.append(pick(ADN_MIXED_NOTE, language))
        return " ".join(parts) or None
    return pick(BASIS_NOTE, language).format(other=" en ".join(other), section=section)


def check_adr_points(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> dict[str, Any]:
    """ADR 1.1.3.6: points per product, total and exemption status."""
    rules = get_compliance_rules()["adr_points"]
    lang = _lang(language)
    categories = rules["categories"]
    threshold = rules["threshold"]

    rows: list[dict[str, Any]] = []
    total = 0.0
    incomplete: list[str] = []
    category0: list[str] = []
    forbidden: list[str] = []

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        # A substance that is forbidden for transport does not belong in the
        # points total: there is nothing to exempt, and "fill in the category"
        # next to the red prohibition is confusing. The line is named separately.
        if product.get("transport_forbidden"):
            forbidden.append(label)
            continue
        category = str(product.get("transport_category") or "").strip()
        # 1.1.3.6.1 reassigns an empty uncleaned packaging: it keeps category 0
        # if that is what it contained, and otherwise becomes category 4
        # whatever it contained. Category 4 has factor 0, so a returned drum
        # counts nothing at all — where reading the substance's own category
        # put one empty drum of a packing group II liquid at 900 of the 1000
        # and denied an exemption the regulation grants.
        reassigned = False
        if product.get("empty_uncleaned"):
            rule = rules.get("empty_uncleaned") or {}
            un = re.sub(r"\D", "", str(product.get("un_number") or ""))
            if category == rule.get("category_0_stays", "0") \
                    and un not in set(rule.get("except_un") or ()):
                pass
            else:
                category = rule.get("otherwise_becomes", "4")
            reassigned = True
        quantity = _num(product.get("adr_total_quantity"))
        # A reassigned line needs no quantity. 5.4.1.1.1 (f) composes none for
        # residues nobody has weighed, and factor 0 makes the arithmetic the
        # same whatever it would have been — asking for a number that changes
        # nothing is how a form teaches people to invent numbers.
        # Only where the reassignment lands on a factor of zero. Category 0's
        # factor is null, not zero, and the two mean opposite things: zero is
        # "counts nothing", null is "no exemption exists". Treating them alike
        # let an empty drum of a category 0 substance report a possible
        # exemption, which is the one direction that must never be wrong.
        if reassigned and category in categories \
                and categories[category].get("factor") == 0:
            quantity = quantity if quantity and quantity > 0 else 0.0
            rows.append({
                "product": label,
                "transport_category": category,
                "quantity": quantity or None,
                "points": 0.0,
                "empty_uncleaned": True,
                "basis": "1.1.3.6.1",
            })
            continue
        if category not in categories or quantity is None or quantity <= 0:
            # Zero or negative is unusable too: -5 L would lower the points
            # total and suggest an exemption that does not exist.
            incomplete.append(label)
            rows.append({
                "product": label,
                "transport_category": category or None,
                "quantity": quantity,
                "points": None,
            })
            continue
        spec = categories[category]
        factor = spec["factor"]
        note_a = False
        # ADR/RID 1.1.3.6.3 note (a): nine UN numbers of transport category 1
        # may be carried up to 50 kg instead of 20 kg, and RID 1.1.3.6.4 spells
        # out the multiplier that goes with it — times 20, not times 50. Read
        # from ADR 2025 Vol. I and RID 2025; see scripts/read_land_regulations.py.
        #
        # Counting them at 50 is not a harmless over-estimate. 50 kg of chlorine
        # scored 2500 and lost an exemption the text grants at exactly 1000, so
        # the application demanded orange plates, a driver certificate and an
        # ADR vehicle for a load that does not need them.
        if category == "1" and _num(rules.get("category_1_note_a", {}).get("factor")):
            exception = rules["category_1_note_a"]
            if str(product.get("un_number") or "").strip().lstrip("UN ").strip() in set(
                exception["un_numbers"]
            ):
                factor = exception["factor"]
                note_a = True
        if category == "0":
            category0.append(label)
            points = None
        else:
            points = round(quantity * (factor or 0), 2)
            total += points
        rows.append({
            "product": label,
            "transport_category": category,
            "quantity": quantity,
            "factor": factor,
            "points": points,
            **({"note_a": True} if note_a else {}),
        })

    # 1.1.3.6.2 grants the exemption for goods carried *in packages* in one
    # transport unit. A tank or a bulk load is not carriage in packages, so the
    # exemption is not available to it however small the quantity — and the
    # points arithmetic, which exists only to test that exemption, is answering
    # a question that does not arise. Withholding an exemption is the safe
    # direction to be wrong in; granting one is not.
    not_in_packages = sorted({
        _product_label(entry, product, index)
        for entry, index, product in _iter_products(entries)
        if str(product.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank", "bulk")})

    if not_in_packages:
        status = "not_available_for_mode"
    elif category0:
        status = "not_exempt"
    elif incomplete:
        status = "incomplete"
    elif total <= threshold:
        status = "exempt_possible"
    else:
        status = "above_threshold"

    result_extra: dict[str, Any] = {}
    if not_in_packages:
        text = rules["not_available_for_mode"]
        result_extra["mode_note"] = (text.get(lang) or text["en"]).format(
            products=", ".join(not_in_packages))
        result_extra["not_in_packages"] = not_in_packages

    return {
        **result_extra,
        "rows": rows,
        "total_points": round(total, 2),
        "threshold": threshold,
        "status": status,
        "category0_products": category0,
        "incomplete_products": incomplete,
        "forbidden_products": forbidden,
        "quantity_units_note": pick(rules["quantity_units"], lang),
        "exempt_provisions": pick(rules["exempt_provisions"], lang),
        "still_required": pick(rules["still_required"], lang),
        "basis": "ADR 1.1.3.6",
        "basis_note": basis_note(profiles, "1.1.3.6", language),
    }


def _adn_row_matches(rule: dict[str, Any], product: dict[str, Any]) -> bool:
    """Does this ADN table row describe this product?"""
    selector = rule["selector"]
    if selector in {"all", "other"}:
        return True
    packing_group = str(product.get("packing_group") or "").strip().upper()
    if selector == "pg_i":
        return packing_group == "I"
    if selector == "toxic_groups" or selector == "group_f":
        # ADN reads the class 2 group out of the classification code: the letters
        # after the digit in 2.2.2.1.3, e.g. 2TF, 4F, 1O.
        code = str(product.get("classification_code") or "").strip().upper()
        letters = "".join(character for character in code if character.isalpha())
        if not letters:
            return False
        return letters in {group.upper() for group in rule.get("groups", [])}
    if selector == "label_1":
        # "for which a danger label of model No. 1 is required in column (5)".
        labels = {token.strip() for token in _hazard_tokens(product)}
        return "1" in labels
    if selector == "category_a":
        # Class 6.2 category A is carried in the UN number, not in a column.
        return str(product.get("un_number") or "").strip() in {"2814", "2900", "3549"}
    if selector == "excepted_packages":
        return str(product.get("un_number") or "").strip() in set(rule.get("un_numbers", []))
    return False


def _adn_limit_for(product: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The first row of the ADN table that fits, which is the applicable one.

    Order matters and the table is written to be read in order: the specific
    rows of a class come before its "any other substances" row, so a class 3
    packing group I substance is caught by the 300 kg row and never reaches the
    3000 kg one.
    """
    primary = _primary_class(product)
    for rule in rules:
        if rule["class"] != primary:
            continue
        if _adn_row_matches(rule, product):
            return rule
    return None


def check_adn_exemption(
    entries: list[dict[str, Any]], language: str = "nl"
) -> dict[str, Any]:
    """ADN 1.1.3.6.1: exemption for carriage in packages on board a vessel.

    ADN has no points count. It exempts when the gross mass of all dangerous
    goods together stays below 3000 kg *and* no single class exceeds its own
    limit — 0, 300 or 3000 kg, depending on packing group, group or label. For
    carriage in tanks the exemption does not apply at all.

    Until v1.32.0 an ADN consignment was shown the ADR points count. That is not
    an approximation of this answer but an answer to a different question: 1200
    kg of a liquid in packing group III costs 1200 ADR points and loses the
    exemption there, while ADN exempts the same consignment as long as the total
    stays under 3000 kg.
    """
    config = get_compliance_rules()["adn_exemption"]
    lang = _lang(language)
    rules = config["rules"]
    cap = float(config["total_gross_mass_kg"])

    rows: list[dict[str, Any]] = []
    total = 0.0
    incomplete: list[str] = []
    over_class: list[dict[str, Any]] = []
    per_limit: dict[tuple[str, str], float] = {}

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        if product.get("transport_forbidden"):
            continue
        rule = _adn_limit_for(product, rules)
        mass = _num(product.get("adr_total_quantity"))
        if rule is None or mass is None or mass <= 0:
            incomplete.append(label)
            rows.append({"product": label, "limit": rule["limit"] if rule else None,
                         "quantity": mass, "class": _primary_class(product)})
            continue
        total += mass
        key = (rule["class"], rule["selector"])
        per_limit[key] = per_limit.get(key, 0.0) + mass
        rows.append({
            "product": label,
            "class": rule["class"],
            "selector": rule["selector"],
            "limit": rule["limit"],
            "quantity": mass,
        })

    for (class_name, selector), carried in sorted(per_limit.items()):
        limit = next(
            rule["limit"] for rule in rules
            if rule["class"] == class_name and rule["selector"] == selector
        )
        if carried > limit:
            over_class.append({"class": class_name, "selector": selector,
                               "limit": limit, "carried": round(carried, 2)})

    # 1.1.3.6.1 grants this for the carriage of dangerous goods *in packages*,
    # and its own table opens by giving carriage in tanks a limit of nought for
    # every class. The note under this result has said so since v1.32.0 while the
    # arithmetic granted the exemption anyway — a sentence to the reader is not a
    # rule. Bulk is not carriage in packages either, and a tank container is a
    # tank; withholding an exemption is the safe direction to be wrong in.
    not_in_packages = sorted({
        _product_label(entry, product, index)
        for entry, index, product in _iter_products(entries)
        if not product.get("transport_forbidden")
        and str(product.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank", "bulk")})

    if not_in_packages:
        status = "not_available_for_mode"
    elif incomplete:
        status = "incomplete"
    elif over_class:
        status = "not_exempt"
    elif total > cap:
        status = "above_threshold"
    else:
        status = "exempt_possible"

    mode_note: dict[str, Any] = {}
    if not_in_packages:
        text = get_compliance_rules()["adn_carriage_admission"]["not_in_packages"]
        mode_note["mode_note"] = (text.get(lang) or text["en"]).format(
            products=", ".join(not_in_packages))

    return {
        "rows": rows,
        "total_gross_mass_kg": round(total, 2),
        "threshold": cap,
        "status": status,
        **mode_note,
        "over_class_limit": over_class,
        "incomplete_products": incomplete,
        "basis": "ADN 1.1.3.6.1",
        "conditions": pick(config["conditions"], lang),
        "note": pick(
            {
                "nl": "Het ADN stelt vrij op brutomassa, niet met punten: het "
                      "totaal blijft onder 3000 kg en geen klasse komt boven haar "
                      "eigen grens. Vervoer in tanks is nooit vrijgesteld. De "
                      "voorwaarden van 1.1.3.6.2 blijven gelden.",
                "en": "ADN exempts on gross mass, not on points: the total stays "
                      "under 3,000 kg and no class exceeds its own limit. Carriage "
                      "in tanks is never exempt. The conditions of 1.1.3.6.2 "
                      "continue to apply.",
                "de": "Das ADN stellt anhand der Bruttomasse frei, nicht mit "
                      "Punkten: die Summe bleibt unter 3000 kg und keine Klasse "
                      "überschreitet ihre eigene Grenze. Beförderung in Tanks ist "
                      "nie freigestellt. Die Bedingungen nach 1.1.3.6.2 gelten "
                      "weiter.", "fr": "L'ADN exempte sur la masse brute et non sur des points : le total reste inférieur à 3 000 kg et aucune classe ne dépasse sa propre limite. Le transport en citerne n'est jamais exempté. Les conditions du 1.1.3.6.2 restent applicables."},
            lang,
        ),
    }


def _mixed_loading_footnote(
    class1_un: str, other_un: str, other_class: str, footnotes: dict[str, Any]
) -> str | None:
    """Which footnote to table 7.5.2.1 permits this pair, if any.

    The cell for class 1 against another class is empty in the table —
    forbidden — except where a letter appears. Three of those matter here, and
    all three hang on the UN number rather than the class:

    (b) class 1 with life-saving appliances of class 9;
    (c) UN 0503 with UN 3268;
    (d) explosive with ammonium nitrate and related nitrates.

    Footnote (a) is there too, but it concerns 1.4S and that is already caught
    above: 1.4S does not count as class 1 for this table.
    """
    note_d = footnotes["d"]
    if (
        class1_un in note_d["blasting_explosive_un_numbers"]
        and class1_un not in note_d["excluded_un_numbers"]
        and other_un in note_d["nitrate_un_numbers"]
    ):
        return "d"
    if class1_un == footnotes["c"]["class1_un"] and other_un == footnotes["c"]["class9_un"]:
        return "c"
    if other_class.startswith("9") and other_un in footnotes["b"]["life_saving_un_numbers"]:
        return "b"
    return None


def _compatibility_table(profiles: list[str] | None) -> tuple[dict[str, Any], str]:
    """Which 7.5.2.2 table applies, and under which name it is cited.

    RID has its own 7.5.2.2 and it is not the same as the ADR one: it is missing
    compatibility group A. That is a difference in what the table answers, not
    in the answer — hence a rail leg gets the rail table and not the road one.
    ADN has no table of its own; that keeps borrowing, with the basis note that
    is already there.
    """
    compatibility = get_compliance_rules()["adr_mixed_loading"]["compatibility"]
    active = {p.upper() for p in (profiles or [])}
    if active == {"RID"}:
        return compatibility["rail"], "RID"
    return compatibility["road"], "ADR"


def _class1_compatibility(
    compat_groups: dict[str, list[str]],
    unknown: list[str],
    language: str,
    profiles: list[str] | None,
) -> list[dict[str, str]]:
    """ADR/RID 7.5.2.2: may this compatibility group travel next to that one?

    The table sets group against group. An empty cell is a prohibition, an X is
    "mixed loading permitted", and four cells carry a letter: then it is allowed,
    but not without conditions. Until v1.41.0 EMCargo only counted the groups
    and handed the question back to the user; now the table is read.
    """
    rules = get_compliance_rules()["adr_mixed_loading"]["rules"]
    table, regime = _compatibility_table(profiles)
    order: list[str] = table["group_order"]
    matrix: dict[str, list[str]] = table["matrix"]
    lang = _lang(language)
    findings: list[dict[str, str]] = []

    known = sorted(g for g in compat_groups if g in order)
    outside = sorted(g for g in compat_groups if g not in order)

    for i, group_a in enumerate(known):
        for group_b in known[i:]:
            # On the diagonal this is about two packages of the same group; with
            # a single package there is nothing to load together.
            if group_a == group_b and len(compat_groups[group_a]) < 2:
                continue
            cell = matrix[group_a][order.index(group_b)]
            if cell == "X":
                continue
            products = ", ".join(
                dict.fromkeys(compat_groups[group_a] + compat_groups[group_b])
            )
            pair = f"{group_a} × {group_b}"
            if not cell:
                key = "class1_compat_forbidden_rail" if regime == "RID" else "class1_compat_forbidden"
                findings.append({
                    "rule": f"{regime} 7.5.2.2 ({pair})",
                    "severity": "error",
                    "message": pick(rules[key], lang).replace("{groups}", pair),
                    "products": products,
                })
                continue
            # A cell can refer to two footnotes ("b c"); then both apply and the
            # user should see both.
            for letter in cell:
                findings.append({
                    "rule": f"{regime} 7.5.2.2 ({pair}) ({letter})",
                    "severity": "warning",
                    "message": pick(rules[f"class1_compat_note_{letter}"], lang),
                    "products": products,
                })

    for group in outside:
        # What the table does not know, the table does not answer. Saying so is
        # the only honest option: group A *is* in ADR and is not in RID.
        findings.append({
            "rule": f"{regime} 7.5.2.2",
            "severity": "warning",
            "message": pick(rules["class1_compat_not_in_table"], lang)
            .replace("{group}", group)
            .replace("{regime}", regime)
            .replace("{products}", ", ".join(compat_groups[group])),
            "products": ", ".join(compat_groups[group]),
        })

    if unknown and len(unknown) + sum(len(v) for v in compat_groups.values()) > 1:
        findings.append({
            "rule": f"{regime} 7.5.2.2",
            "severity": "warning",
            "message": pick(rules["class1_compat_unknown_group"], lang).replace(
                "{products}", ", ".join(unknown)
            ),
            "products": ", ".join(unknown),
        })
    return findings


def check_adr_mixed_loading(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> list[dict[str, str]]:
    """ADR 7.5.2 / 7.5.4 (CV28): mixed loading warnings at class level."""
    rules = get_compliance_rules()["adr_mixed_loading"]
    footnotes = rules["footnotes"]
    lang = _lang(language)
    warnings: list[dict[str, str]] = []

    class1_products: list[tuple[str, str]] = []
    other_class_products: list[tuple[str, str, str]] = []
    # Per compatibility group the packages that fall in it, so the message can
    # say *which* packages it concerns and not merely how many groups there are.
    compat_groups: dict[str, list[str]] = {}
    compat_unknown: list[str] = []
    food_separation: list[str] = []

    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        tokens = _hazard_tokens(product)
        primary = _primary_class(product)
        un = str(product.get("un_number") or "").strip()

        if primary.startswith("1"):
            # 7.5.2.2 is about explosives among themselves, and 1.4S does belong
            # there: the table has an S row and it is not X everywhere — S next
            # to group L is empty, hence forbidden. Footnote (a) to 7.5.2.1 only
            # removes 1.4S from the comparison with *other* classes.
            group = _compat_group(product)
            if group:
                if label not in compat_groups.setdefault(group, []):
                    compat_groups[group].append(label)
            elif label not in compat_unknown:
                compat_unknown.append(label)

        if primary.startswith("1") and not primary.endswith("S"):
            class1_products.append((label, un))
        elif primary and not primary.endswith("S"):
            other_class_products.append((label, un, primary))

        if any(t.startswith("6.1") or t.startswith("6.2") for t in tokens):
            food_separation.append(label)
        elif primary.startswith("9") and un in rules["cv28_class9_un_numbers"]:
            food_separation.append(label)

    if class1_products and other_class_products:
        # Per pair, not per consignment: one forbidden combination does not make
        # the others forbidden, and one permitted combination does not make the
        # rest all right.
        forbidden: list[str] = []
        permitted: dict[str, list[str]] = {}
        for class1_label, class1_un in class1_products:
            for other_label, other_un, other_class in other_class_products:
                note = _mixed_loading_footnote(class1_un, other_un, other_class, footnotes)
                bucket = permitted.setdefault(note, []) if note else forbidden
                for label in (class1_label, other_label):
                    if label not in bucket:
                        bucket.append(label)

        # The table is the same in both regimes — v1.38.0 read RID's 7.5.2.1
        # and found it identical to the ADR's, footnotes included — but the
        # citation is not. "ADR 7.5.2.1" printed on a CIM is the same category
        # of inaccuracy as the CV28 that used to appear there in place of CW 28:
        # a code name the regulation governing that document does not have.
        _table, regime = _compatibility_table(profiles)
        if forbidden:
            warnings.append({
                "rule": f"{regime} 7.5.2.1",
                "severity": "error",
                "message": pick(rules["rules"]["class1_with_others"], lang),
                "products": ", ".join(forbidden),
            })
        for note in sorted(permitted):
            # Permitted, but not without conditions: footnote (d) moves the
            # placarding and the maximum permitted quantity to class 1.
            warnings.append({
                "rule": f"{regime} 7.5.2.1 ({note})",
                "severity": "warning",
                "message": pick(rules["rules"][f"class1_footnote_{note}"], lang),
                "products": ", ".join(permitted[note]),
            })
    warnings.extend(_class1_compatibility(compat_groups, compat_unknown, language, profiles))
    if food_separation:
        # The same provision under a different name: RID puts it in column (18)
        # as CW 28, ADR as CV28. The content of 7.5.4 is word for word the same,
        # so only the citation differs — but an invented code name on a rail
        # document is exactly the kind of inaccuracy the app adds itself.
        _, regime = _compatibility_table(profiles)
        code = "CW28" if regime == "RID" else "CV28"
        warnings.append({
            "rule": f"{regime} {code} / 7.5.4",
            "severity": "warning",
            "message": pick(rules["rules"]["cv28_foodstuffs"], lang),
            "products": ", ".join(food_separation),
        })
    return warnings


def _position_label(entry: dict[str, Any], index: int) -> str:
    return str(entry.get("vehicle") or entry.get("line_id") or f"#{index + 1}")


def check_rid_protective_distance(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, str]]:
    """RID 7.5.3: protective distance in the train.

    This is the provision the railway has no road equivalent for, and that is no
    accident: 7.5.3 is about how a train is assembled, and a road vehicle
    travels alone. Precisely for that reason the ADR chapter could never stand
    in here — it would not give the wrong answer but no answer at all.

    The trigger is the placard, not the division. RID names models 1, 1.5 and
    1.6 and does not name model 1.4, so a wagon carrying only 1.4 goods falls
    outside it.
    """
    rules = get_compliance_rules().get("rid_protective_distance")
    if not rules:
        return []
    lang = _lang(language)
    class1_placards = set(rules["class1_placards"])
    counterpart = set(rules["counterpart_placards"])

    class1_positions: list[str] = []
    counterpart_positions: list[str] = []
    for index, entry in enumerate(entries):
        label = _position_label(entry, index)
        bears_class1 = False
        bears_counterpart = False
        for product in entry.get("products") or []:
            for token in _hazard_tokens(product) + [_primary_class(product)]:
                token = token.strip().upper()
                if token in class1_placards:
                    bears_class1 = True
                elif token in counterpart:
                    bears_counterpart = True
            # Class 1 without a division in the class field: the division is
            # then in the classification code, and without a division there is no
            # telling whether the placard is 1.4 — so the position counts, because
            # not knowing whether a distance is needed must not look like knowing
            # that it is not.
            code = str(product.get("classification_code") or "").strip().upper()
            division = code[:3] if re.match(r"^1\.\d", code) else ""
            if division in class1_placards:
                bears_class1 = True
            elif _primary_class(product) == "1" and not division:
                bears_class1 = True
        if bears_class1 and label not in class1_positions:
            class1_positions.append(label)
        if bears_counterpart and label not in counterpart_positions:
            counterpart_positions.append(label)

    if not class1_positions:
        return []

    pairs = [
        (one, other)
        for one in class1_positions
        for other in counterpart_positions
        if one != other
    ]
    if pairs:
        return [{
            "rule": "RID 7.5.3",
            "severity": "warning",
            "message": pick(rules["rules"]["between_positions"], lang),
            "products": "; ".join(f"{one} ↔ {other}" for one, other in pairs),
        }]
    # No counterpart in this consignment does not mean no distance is needed:
    # the rest of the train is not in EMCargo.
    return [{
        "rule": "RID 7.5.3",
        "severity": "warning",
        "message": pick(rules["rules"]["train_formation"], lang),
        "products": ", ".join(class1_positions),
    }]


def check_rid_transport_document(
    entries: list[dict[str, Any]], language: str = "nl",
) -> list[dict[str, str]]:
    """RID 5.4.1.1.1 (j): the hazard identification number on the CIM.

    Rail is the only one of the three land regimes that puts that number on the
    document. ADR's own (k) is the tunnel restriction code and ADN has neither,
    so this is not a shared provision under three names.

    Where a marking under 5.3.2.1 is prescribed the number goes *before* the
    letters "UN", and the composed line does that itself. What is left here is
    the two cases the line cannot settle on its own:

    - the marking is prescribed and table A has **no** hazard identification
      number for the substance, so there is nothing to put in front. Composing
      the line silently without it would hide a description the RID says is
      incomplete;
    - the goods travel in packages as a **full load of one and the same
      substance**, where 5.3.2.1.1 says the plate *may* be affixed. If it is,
      (j) applies and the number belongs on the document — and whether a wagon
      was plated is not something this application can see. So it is asked.
    """
    rules = get_compliance_rules()["rid_transport_document"]
    lang = _lang(language)
    findings: list[dict[str, str]] = []

    marked: list[str] = []
    without_number: list[str] = []
    substances: set[str] = set()
    packaged: list[str] = []
    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        un = str(product.get("un_number") or "").strip()
        if not un:
            continue
        substances.add(un)
        label = _product_label(entry, product, index)
        number = str(product.get("hazard_number") or "").strip()
        if rid_marking_prescribed(product):
            (marked if number else without_number).append(
                f"{label} ({number})" if number else label)
        else:
            packaged.append(label)

    if marked:
        findings.append({
            "rule": "RID 5.4.1.1.1 (j)",
            "severity": "info",
            "message": pick(rules["rules"]["prescribed"], lang),
            "products": ", ".join(marked),
        })
    if without_number:
        findings.append({
            "rule": "RID 5.4.1.1.1 (j)",
            "severity": "warning",
            "message": pick(rules["rules"]["no_hazard_number"], lang),
            "products": ", ".join(without_number),
        })
    # One substance and nothing else: the wagon may be plated, and then the
    # number belongs in front. More than one substance and the permission of
    # 5.3.2.1.1 does not arise, so neither does the question.
    if packaged and not marked and not without_number and len(substances) == 1:
        findings.append({
            "rule": "RID 5.4.1.1.1 (j) / 5.3.2.1.1",
            "severity": "warning",
            "message": pick(rules["rules"]["full_load_of_packages"], lang),
            "products": ", ".join(packaged),
        })
    return findings


def check_rid_limited_quantities_with_explosives(
    entries: list[dict[str, Any]], language: str = "nl",
    lq_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    """RID 7.5.2.4: limited quantities may not be loaded with explosives.

    Read in the English edition on printed page 1103 and in the German on 1187,
    which agree: *mixed loading of dangerous goods packed in limited quantities
    with any type of explosive substances and articles, except those of Division
    1.4 and UN Nos. 0161 and 0499, is prohibited.* There is no ADR equivalent,
    and nothing here is new data — the LQ assessment of 3.4 and the class of
    each package are both already computed.

    Which lines count as "packed in limited quantities" is taken from the 3.4
    assessment rather than recomputed, so the two cannot disagree about the same
    package. Without that assessment nothing is claimed.
    """
    rules = get_compliance_rules()["rid_limited_quantities_with_explosives"]
    lang = _lang(language)
    excepted = set(rules["excepted_un_numbers"])

    within_lq = {row["product"] for row in (lq_rows or [])
                 if (row.get("lq") or {}).get("status") == "within_limits"}
    if not within_lq:
        return []

    explosives: list[str] = []
    limited: list[str] = []
    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        if label in within_lq:
            limited.append(label)
            continue
        if not _primary_class(product).startswith("1"):
            continue
        un = str(product.get("un_number") or "").strip()
        division = _primary_class(product)
        if un in excepted:
            continue
        # Division 1.4 is out, and a class 1 entry whose division is not known
        # is not: not knowing whether the exception applies must not read as
        # knowing that it does.
        code = str(product.get("classification_code") or "").strip().upper()
        if division.startswith("1.4") or code.startswith("1.4"):
            continue
        explosives.append(label)

    if not (limited and explosives):
        return []
    return [{
        "rule": "RID 7.5.2.4",
        "severity": "error",
        "message": pick(rules["rules"]["forbidden"], lang),
        "products": ", ".join(limited + explosives),
    }]


def check_technical_name_required(
    entries: list[dict[str, Any]], language: str = "nl",
) -> list[dict[str, str]]:
    """Special provision 274: an N.O.S. entry needs its technical name.

    Column (6) of table A carries 274 on 816 rows, and 3.1.2.8.1 is what it
    points at: the proper shipping name of such an entry is supplemented with
    the technical name in brackets. The description-line builder has appended
    that name since the field existed — for the consignor who filled it in.
    Nothing ever spoke for the one who did not, and "UN 1993 FLAMMABLE LIQUID,
    N.O.S." with nothing in the brackets is a description the provision calls
    incomplete, printed with full confidence.
    """
    rules = get_compliance_rules()["sp274_technical_name"]
    lang = _lang(language)
    missing: list[str] = []
    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        un = str(product.get("un_number") or "").strip()
        if not un or str(product.get("technical_name") or "").strip():
            continue
        rows = database.get_un_entries(un)
        provisions = str((rows[0] if rows else {}).get("special_provisions") or "")
        if "274" in provisions.replace(",", " ").split():
            missing.append(_product_label(entry, product, index))
    if not missing:
        return []
    return [{
        "rule": "ADR/RID/ADN 3.3, special provision 274",
        "severity": "warning",
        "message": pick(rules["rules"]["missing"], lang).format(
            products=", ".join(missing)),
        "products": ", ".join(missing),
    }]


def check_adn_stabilisation(
    entries: list[dict[str, Any]], language: str = "nl",
) -> list[dict[str, str]]:
    """ADN 5.4.1.1.1 (j): the confirmation of stabilisation on the document.

    Column (11) of the ADN's own table A carries the additional requirements of
    7.1.6.11, and one of them reaches the paper. ST01 — read in the English
    edition on printed page 388 — requires the substance to have been stabilized
    as the IMSBC Code requires for ammonium nitrate fertilizers, and says in as
    many words that *stabilizing shall be certified by the consignor in the
    transport document*.

    7.1.6.11 is headed "Carriage in bulk" and applies where column (11) says so,
    so this speaks for a bulk load and not for the same substance in packages.
    Two UN numbers carry ST01 in the table this application holds: 1942 and
    2067. ST02, which UN 2071 carries, is a condition on the carriage and not on
    the document, and is deliberately not raised here.
    """
    rules = get_compliance_rules()["adn_stabilisation"]
    lang = _lang(language)
    affected: list[str] = []
    for entry, index, product in _iter_products(entries):
        if str(product.get("carriage_mode") or "").strip() != "bulk":
            continue
        un = str(product.get("un_number") or "").strip()
        if "ST01" in adn_loading_measures(un):
            affected.append(_product_label(entry, product, index))
    if not affected:
        return []
    return [{
        "rule": "ADN 5.4.1.1.1 (j) / 7.1.6.11 ST01",
        "severity": "warning",
        "message": pick(rules["rules"]["st01"], lang),
        "products": ", ".join(affected),
    }]


#: The wording of the tunnel result, per outcome. Kept here rather than in the
#: configuration because these are sentences about what the app did, not values
#: read out of the ADR; the figures and the table itself are in the config.
_TUNNEL_MESSAGES: dict[str, dict[str, str]] = {
    "derived": {
        "nl": "De meest restrictieve code van de hele lading is {code} (8.6.3.2). "
              "Doorgang verboden door tunnels van categorie {categories}.",
        "en": "The most restrictive code for the whole load is {code} (8.6.3.2). "
              "Passage forbidden through tunnels of category {categories}.",
        "de": "Der restriktivste Code der gesamten Ladung ist {code} (8.6.3.2). "
              "Durchfahrt durch Tunnel der Kategorie {categories} verboten.",
        "fr": "Le code le plus restrictif de l'ensemble du chargement est {code} "
              "(8.6.3.2). Passage interdit dans les tunnels de catégorie {categories}.",
    },
    "unrestricted": {
        "nl": "De meest restrictieve code van de hele lading is {code} (8.6.3.2): "
              "doorgang toegestaan door alle tunnels.",
        "en": "The most restrictive code for the whole load is {code} (8.6.3.2): "
              "passage permitted through all tunnels.",
        "de": "Der restriktivste Code der gesamten Ladung ist {code} (8.6.3.2): "
              "Durchfahrt durch alle Tunnel erlaubt.",
        "fr": "Le code le plus restrictif de l'ensemble du chargement est {code} "
              "(8.6.3.2) : passage autorisé dans tous les tunnels.",
    },
    "exempt": {
        "nl": "Alle goederen worden overeenkomstig 1.1.3 vervoerd. Die tellen niet "
              "mee bij het vaststellen van de code voor de hele lading en zijn niet "
              "aan tunnelbeperkingen onderworpen (8.6.3.3).",
        "en": "Every item is carried under 1.1.3. Those do not count towards the "
              "code for the whole load and are not subject to tunnel restrictions "
              "(8.6.3.3).",
        "de": "Alle Güter werden nach 1.1.3 befördert. Sie zählen bei der "
              "Bestimmung des Codes für die gesamte Ladung nicht mit und "
              "unterliegen keinen Tunnelbeschränkungen (8.6.3.3).",
        "fr": "Toutes les marchandises sont transportées selon le 1.1.3. Elles ne "
              "comptent pas pour la détermination du code de l'ensemble du "
              "chargement et ne sont pas soumises aux restrictions en tunnel "
              "(8.6.3.3).",
    },
    "lq_marking_only": {
        "nl": "De goederen zelf worden overeenkomstig 1.1.3 vervoerd, maar de "
              "transporteenheid moet de LQ-kenmerking van 3.4.13 dragen. Daarmee "
              "geldt het verbod op doorgang door tunnels van categorie {categories} "
              "(8.6.3.3 en 8.6.4).",
        "en": "The goods themselves are carried under 1.1.3, but the transport unit "
              "has to carry the LQ marking of 3.4.13. That brings the ban on passage "
              "through tunnels of category {categories} with it (8.6.3.3 and 8.6.4).",
        "de": "Die Güter selbst werden nach 1.1.3 befördert, die Beförderungseinheit "
              "muss jedoch die LQ-Kennzeichnung nach 3.4.13 tragen. Damit gilt das "
              "Verbot der Durchfahrt durch Tunnel der Kategorie {categories} "
              "(8.6.3.3 und 8.6.4).",
        "fr": "Les marchandises elles-mêmes relèvent du 1.1.3, mais l'unité de "
              "transport doit porter la marque QL du 3.4.13. L'interdiction de "
              "passage dans les tunnels de catégorie {categories} s'applique donc "
              "(8.6.3.3 et 8.6.4).",
    },
    "incomplete": {
        "nl": "Voor {products} staat geen code voor beperkingen in tunnels in de "
              "regel. Zolang die ontbreekt kan de code voor de hele lading niet "
              "worden vastgesteld (8.6.3.2).",
        "en": "No tunnel restriction code is on the line for {products}. Until it is "
              "there the code for the whole load cannot be determined (8.6.3.2).",
        "de": "Für {products} steht kein Code für Tunnelbeschränkungen in der Zeile. "
              "Solange er fehlt, kann der Code für die gesamte Ladung nicht bestimmt "
              "werden (8.6.3.2).",
        "fr": "Aucun code de restriction en tunnel ne figure sur la ligne pour "
              "{products}. Tant qu'il manque, le code de l'ensemble du chargement ne "
              "peut être déterminé (8.6.3.2).",
    },
    "unknown_code": {
        "nl": "De code {code} bij {products} staat niet in de tabel van 8.6.4. De "
              "code voor de hele lading is daarom niet vastgesteld.",
        "en": "The code {code} on {products} is not in the table of 8.6.4. The code "
              "for the whole load has therefore not been determined.",
        "de": "Der Code {code} bei {products} steht nicht in der Tabelle von 8.6.4. "
              "Der Code für die gesamte Ladung wurde daher nicht bestimmt.",
        "fr": "Le code {code} de {products} ne figure pas au tableau du 8.6.4. Le "
              "code de l'ensemble du chargement n'a donc pas été déterminé.",
    },
}

#: What the answer does *not* cover. The app knows packages, not tanks, and it
#: does not know the route — both of which change the answer, so both are said.
_TUNNEL_NOTE = {
    "nl": "Berekend voor vervoer in colli. Los gestort vervoer of vervoer in tanks "
          "geeft bij de codes B/D, B/E, C/D, C/E en D/E een strengere uitkomst. "
          "Welke tunnels op de route liggen en in welke categorie zij vallen, weet "
          "EMCargo niet — dat blijft aan de vervoerder (1.9.5).",
    "en": "Computed for carriage in packages. Carriage in bulk or in tanks gives a "
          "stricter answer for the codes B/D, B/E, C/D, C/E and D/E. Which tunnels "
          "lie on the route, and which category they are in, EMCargo does not "
          "know — that stays with the carrier (1.9.5).",
    "de": "Berechnet für die Beförderung in Versandstücken. Beförderung in loser "
          "Schüttung oder in Tanks ergibt bei den Codes B/D, B/E, C/D, C/E und D/E "
          "ein strengeres Ergebnis. Welche Tunnel auf der Strecke liegen und in "
          "welche Kategorie sie fallen, weiß EMCargo nicht — das bleibt beim "
          "Beförderer (1.9.5).",
    "fr": "Calculé pour le transport en colis. Le transport en vrac ou en citernes "
          "donne un résultat plus strict pour les codes B/D, B/E, C/D, C/E et D/E. "
          "Quels tunnels se trouvent sur l'itinéraire, et dans quelle catégorie ils "
          "sont classés, EMCargo l'ignore — cela reste au transporteur (1.9.5).",
}


def _tunnel_code_of(product: dict[str, Any]) -> str:
    """The code from column (15), however it was written into the field.

    It reaches the line as "D/E", as "(D/E)" or — where the ADR says there is no
    restriction — as "-" or "(-)". All three mean the same thing.
    """
    raw = str(product.get("tunnel_code") or "").strip()
    raw = raw.strip("()").strip()
    if raw in {"–", "—"}:
        return "-"
    return raw.upper() if raw else ""


def check_adr_tunnel(
    entries: list[dict[str, Any]],
    language: str = "nl",
    points_status: str | None = None,
    lq_marking_required: bool = False,
) -> dict[str, Any]:
    """ADR 8.6.3: the tunnel restriction code for the whole load.

    Until now the code was printed on the transport document — correctly, per
    5.4.1.1.1 (k) — and evaluated nowhere. That is the more dangerous half of the
    two: a consignor who reads "(D/E)" on a CMR may reasonably assume that
    something has been considered, and nothing had been.

    Two provisions make this more than picking the strictest of a list.

    **8.6.3.2** assigns the most restrictive of the codes present to the *whole
    load*, so a load is not a set of separately restricted substances but one
    unit with one code. The order of restrictiveness is not stated in words; it
    is the order of the table in 8.6.4, and that is where it is read from.

    **8.6.3.3** takes goods carried under 1.1.3 out of the determination
    altogether. They are not subject to tunnel restrictions and must not be
    counted — so for a consignment that stays within the 1.1.3.6 exemption there
    is no code to assign at all, and printing one is not merely unevaluated but
    arguably not applicable. The single exception the article names is the
    transport unit that has to carry the marking of 3.4.13 subject to 3.4.14;
    that unit is restricted for category E tunnels under 8.6.4, whatever its
    goods' own codes say.

    ``points_status`` comes from :func:`check_adr_points` and ``lq_marking_required``
    from :func:`check_lq_eq`, so the two things 8.6.3.3 turns on are read from the
    checks that already establish them rather than derived a second time here.
    """
    rules = get_compliance_rules()["adr_tunnel"]
    lang = _lang(language)
    order: list[str] = rules["order"]
    table: dict[str, Any] = rules["codes"]

    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    unknown: list[tuple[str, str]] = []
    present: list[str] = []
    explosive_mass = 0.0

    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        label = _product_label(entry, product, index)
        code = _tunnel_code_of(product)
        rows.append({"product": label, "code": code or None})
        if not code:
            missing.append(label)
            continue
        if code not in table:
            unknown.append((label, code))
            continue
        present.append(code)
        if table[code].get("explosive_mass_kg"):
            # The two split codes count the *total* net explosive mass per
            # transport unit, not the mass of the one line that carries them.
            mass = _num(product.get("net_explosive_mass"))
            if mass:
                explosive_mass += mass

    result: dict[str, Any] = {
        "rows": rows,
        "code": None,
        "restricted_categories": [],
        "explosive_mass_kg": round(explosive_mass, 3) if explosive_mass else None,
        "basis": "ADR 8.6.3 / 8.6.4",
        "note": pick(_TUNNEL_NOTE, lang),
    }

    if not rows:
        result["status"] = "not_checked"
        result["message"] = ""
        return result

    # 8.6.3.3 first: what is carried under 1.1.3 does not take part in the
    # determination, and if that is everything there is nothing to determine.
    if points_status == "exempt_possible":
        if lq_marking_required:
            categories = list(rules["lq_marking_categories"])
            result.update({
                "status": "lq_marking_only",
                "restricted_categories": categories,
                "message": pick(_TUNNEL_MESSAGES["lq_marking_only"], lang).format(
                    categories=", ".join(categories)),
            })
        else:
            result["status"] = "exempt"
            result["message"] = pick(_TUNNEL_MESSAGES["exempt"], lang)
        return result

    if unknown:
        label, code = unknown[0]
        result["status"] = "unknown_code"
        result["message"] = pick(_TUNNEL_MESSAGES["unknown_code"], lang).format(
            code=code, products=label)
        return result
    if missing:
        result["status"] = "incomplete"
        result["message"] = pick(_TUNNEL_MESSAGES["incomplete"], lang).format(
            products=", ".join(missing))
        return result

    code = min(present, key=order.index)
    spec = table[code]
    # 8.6.4 gives five codes two answers: B/D, B/E, C/D, C/E and D/E bar more
    # tunnel categories for carriage in tanks and in bulk than for packages.
    # Both lists have been in this configuration since v1.50.0 and only the
    # packages one was ever read, because nothing knew how the goods travelled.
    # The note said so — and a note is not a check. Now that the consignment
    # says, the stricter side is applied where it applies.
    in_tanks = any(
        str(product.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank", "bulk")
        for _entry, _index, product in _iter_products(entries))
    categories = list(spec["tanks" if in_tanks else "packages"])
    threshold = spec.get("explosive_mass_kg")
    if threshold and explosive_mass > threshold:
        categories = list(spec["above"])
    result.update({
        "code": code,
        "restricted_categories": categories,
        "carriage": "tanks_or_bulk" if in_tanks else "packages",
        "status": "unrestricted" if not categories else "derived",
    })
    result["message"] = pick(
        _TUNNEL_MESSAGES["unrestricted" if not categories else "derived"], lang
    ).format(code=code, categories=", ".join(categories))
    return result


#: The equipment of 8.1.5, in the words a driver checks it by. Kept out of the
#: configuration because these are labels for the user; the *conditions* — which
#: label numbers call for what — are in the configuration, read from the ADR.
_EQUIPMENT_LABELS: dict[str, dict[str, str]] = {
    "wheel_chock": {
        "nl": "Per voertuig een stopblok (wielkeg), passend bij de massa van het "
              "voertuig en de wieldiameter",
        "en": "A wheel chock per vehicle, sized to the vehicle's mass and the wheel "
              "diameter",
        "de": "Je Fahrzeug ein Unterlegkeil, passend zur Fahrzeugmasse und zum "
              "Raddurchmesser",
        "fr": "Une cale de roue par véhicule, adaptée à la masse du véhicule et au "
              "diamètre de la roue",
    },
    "warning_signs": {
        "nl": "Twee zelfstandig staande waarschuwingssignalen",
        "en": "Two self-standing warning signs",
        "de": "Zwei selbststehende Warnzeichen",
        "fr": "Deux signaux d'avertissement autoportants",
    },
    "eye_rinsing_liquid": {
        "nl": "Vloeistof om de ogen te spoelen",
        "en": "Eye-rinsing liquid",
        "de": "Augenspülflüssigkeit",
        "fr": "Liquide de rinçage pour les yeux",
    },
    "warning_vest": {
        "nl": "Per bemanningslid een waarschuwingsvest",
        "en": "A warning vest per crew member",
        "de": "Je Mitglied der Fahrzeugbesatzung eine Warnweste",
        "fr": "Un gilet d'avertissement par membre d'équipage",
    },
    "portable_lighting": {
        "nl": "Per bemanningslid een draagbaar verlichtingsapparaat (8.3.4)",
        "en": "A portable lighting apparatus per crew member (8.3.4)",
        "de": "Je Mitglied der Fahrzeugbesatzung ein tragbares Beleuchtungsgerät (8.3.4)",
        "fr": "Un appareil d'éclairage portatif par membre d'équipage (8.3.4)",
    },
    "gloves": {
        "nl": "Per bemanningslid een paar beschermende handschoenen",
        "en": "A pair of protective gloves per crew member",
        "de": "Je Mitglied der Fahrzeugbesatzung ein Paar Schutzhandschuhe",
        "fr": "Une paire de gants de protection par membre d'équipage",
    },
    "eye_protection": {
        "nl": "Per bemanningslid bescherming voor de ogen (bijv. een veiligheidsbril)",
        "en": "Eye protection per crew member (safety goggles, for instance)",
        "de": "Je Mitglied der Fahrzeugbesatzung Augenschutz (z. B. eine Schutzbrille)",
        "fr": "Une protection des yeux par membre d'équipage (lunettes de sécurité)",
    },
    "escape_mask": {
        "nl": "Per bemanningslid een vluchtmasker voor noodgevallen (gecombineerd "
              "gas/stof filter A1B1E1K1-P1 of A2B2E2K2-P2)",
        "en": "An emergency escape mask per crew member (combined gas/dust filter "
              "A1B1E1K1-P1 or A2B2E2K2-P2)",
        "de": "Je Mitglied der Fahrzeugbesatzung eine Notfall-Fluchtmaske "
              "(Kombinationsfilter A1B1E1K1-P1 oder A2B2E2K2-P2)",
        "fr": "Un masque d'évacuation d'urgence par membre d'équipage (filtre combiné "
              "gaz/poussières A1B1E1K1-P1 ou A2B2E2K2-P2)",
    },
    "shovel": {"nl": "Een schop", "en": "A shovel", "de": "Eine Schaufel",
               "fr": "Une pelle"},
    "drain_seal": {"nl": "Een rioolafdichting", "en": "A drain seal",
                   "de": "Eine Kanalabdeckung", "fr": "Une protection d'obturation "
                                                      "d'égout"},
    "collecting_container": {
        "nl": "Een opvangreservoir", "en": "A collecting container",
        "de": "Ein Auffangbehälter", "fr": "Un récipient collecteur"},
}

_EXTINGUISHER_MESSAGE = {
    "nl": "Per transporteenheid ten minste {count} draagbare brandblusapparaten voor de "
          "brandbaarheidsklassen A, B en C. De totale capaciteit hangt af van de maximaal "
          "toegestane massa van de transporteenheid: {rows} (8.1.4.1). Eén exemplaar van "
          "ten minste 2 kg moet geschikt zijn voor een brand in de motor of de "
          "bestuurderscabine.",
    "en": "At least {count} portable fire extinguishers for flammability classes A, B and "
          "C per transport unit. The total capacity depends on the maximum permissible "
          "mass of the transport unit: {rows} (8.1.4.1). One of at least 2 kg has to be "
          "suitable for a fire in the engine or the driver's cab.",
    "de": "Je Beförderungseinheit mindestens {count} tragbare Feuerlöscher für die "
          "Brandklassen A, B und C. Die Gesamtkapazität hängt von der höchstzulässigen "
          "Masse der Beförderungseinheit ab: {rows} (8.1.4.1). Einer von mindestens 2 kg "
          "muss für einen Brand im Motor oder im Fahrerhaus geeignet sein.",
    "fr": "Au moins {count} extincteurs portatifs pour les classes d'inflammabilité A, B "
          "et C par unité de transport. La capacité totale dépend de la masse maximale "
          "admissible de l'unité de transport : {rows} (8.1.4.1). L'un d'au moins 2 kg "
          "doit convenir à un feu de moteur ou de cabine.",
}

_EXTINGUISHER_EXEMPT_MESSAGE = {
    "nl": "Vervoer overeenkomstig 1.1.3.6: één draagbaar brandblusapparaat voor de "
          "brandbaarheidsklassen A, B en C van ten minste 2 kg poeder (8.1.4.2).",
    "en": "Carriage under 1.1.3.6: one portable fire extinguisher for flammability "
          "classes A, B and C of at least 2 kg of powder (8.1.4.2).",
    "de": "Beförderung nach 1.1.3.6: ein tragbarer Feuerlöscher für die Brandklassen A, "
          "B und C mit mindestens 2 kg Pulver (8.1.4.2).",
    "fr": "Transport selon le 1.1.3.6 : un extincteur portatif pour les classes "
          "d'inflammabilité A, B et C d'au moins 2 kg de poudre (8.1.4.2).",
}

_EQUIPMENT_NOTE = {
    "nl": "Afgeleid uit de gevaarsetiketnummers van de lading, zoals 8.1.5.1 het "
          "voorschrijft. Wat er werkelijk aan boord ligt, weet EMCargo niet — dit is "
          "de lijst om mee af te vinken, geen vaststelling. De brandblusapparaten hangen "
          "bovendien aan de maximaal toegestane massa van de transporteenheid, en die is "
          "hier niet bekend.",
    "en": "Derived from the hazard label numbers of the load, the way 8.1.5.1 prescribes. "
          "What is actually on board EMCargo does not know — this is the list to check "
          "against, not a finding. The extinguishers moreover depend on the maximum "
          "permissible mass of the transport unit, which is not known here.",
    "de": "Abgeleitet aus den Gefahrzettelnummern der Ladung, wie 8.1.5.1 es vorschreibt. "
          "Was tatsächlich an Bord ist, weiß EMCargo nicht — dies ist die Liste zum "
          "Abhaken, keine Feststellung. Die Feuerlöscher hängen zudem von der "
          "höchstzulässigen Masse der Beförderungseinheit ab, die hier nicht bekannt ist.",
    "fr": "Déduit des numéros d'étiquette de danger du chargement, comme le prescrit le "
          "8.1.5.1. Ce qui se trouve réellement à bord, EMCargo l'ignore : ceci est la "
          "liste à cocher, pas un constat. Les extincteurs dépendent en outre de la masse "
          "maximale admissible de l'unité de transport, inconnue ici.",
}

#: 8.1.5.3 asks for the shovel, the drain seal and the collecting container for
#: *solids and liquids* only. Gases carry the same label numbers 3 and 9 in no
#: case, but class 2 does carry 9-labelled articles, and a gas cylinder needs no
#: shovel. The physical state follows from the classification code: G and A are
#: gases, and class 2 is a gas throughout.
def _label_numbers(product: dict[str, Any]) -> set[str]:
    """The hazard label numbers of a product, as 8.1.5.1 means them.

    Column (5) of Table A, not the class column, because that is what the
    article points at — and the two differ exactly where it matters. Class 2 is
    "2" in the class column and 2.1, 2.2 or 2.3 on the label, and the footnote
    to 8.1.5.2 exempts 2.1, 2.2 and 2.3 from the eye-rinsing liquid while saying
    nothing about a bare "2". Reading the class column would have made a load of
    propane cylinders carry an eye wash the ADR does not ask for.

    The model letter is not part of the number: label 9A is a class 9 label, and
    8.1.5.3 lists "9".
    """
    numbers: set[str] = set()
    raw = str(product.get("labels") or "").strip()
    if raw:
        for token in re.split(r"[,;/\s()+]+", raw):
            match = re.match(r"^(\d(?:\.\d)?)", token.strip().upper())
            if match:
                numbers.add(match.group(1))
    if not numbers:
        # An entry without a labels column — the IMDG-only additions had none —
        # falls back on the division and the subsidiary risks.
        for token in _hazard_tokens(product):
            match = re.match(r"^(\d(?:\.\d)?)", token)
            if match:
                numbers.add(match.group(1))
    return numbers


def _is_gas(product: dict[str, Any]) -> bool:
    return any(number.startswith("2") for number in _label_numbers(product))


def check_adn_hold_separation(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADN 7.1.4.3: how far apart packages must lie in a vessel's holds.

    `docs/dg-coverage.md` has ranked "mixed loading for ADN answered with ADR's
    7.5.2" as a gap for several releases, and that wording undersold it. It is
    not another mode's table applied for want of a better one. **It answers a
    different question.** ADR 7.5.2 asks whether two packages may share a
    vehicle, and answers yes or no. ADN 7.1.4.3 asks how many metres must lie
    between them and whether they may share a hold — and a distance is not an
    answer this application could give at all, so a consignor reading
    "permitted" was reading a yes to a question nobody had asked.

    Three rules, two of which have no counterpart in the road regime:

    - **7.1.4.3.1** — goods of different classes at least **3.00 m** apart
      horizontally, and never stacked on one another.
    - **7.1.4.3.3** — class 1, and the three-blue-cone goods of 4.1 and 5.2, at
      least **12 m** from goods of every other class.
    - **7.1.4.3.2** — two blue cones may not share a hold with one-blue-cone
      flammable goods, whatever the quantity.

    The cone provisions come out of column (12) of the ADN's *own* table A,
    which v1.61.0 read out of the Dutch edition, so both are answered now. What
    is *not* answered is named per substance rather than in general: the ADN
    table gives one row per UN number, and where the book prints several that
    differ in the vessel's columns, the cone count that was read may belong to a
    sibling. UN 1203 petrol is that case and UN 0015 smoke ammunition is not —
    its three rows all carry three cones. So the substances whose cones could
    not be settled are listed by name, and 439 of 2,352 is a number a consignor
    can act on where "the cone rules were not assessed" was not.

    **7.1.4.3.4** gives class 1 its own compatibility table — twelve groups,
    four numbered conditions — and it is applied since v1.64.0. Getting it took
    the two readings this repository insists on, and it was worth insisting: the
    Dutch HTML edition is *damaged* there. Row N carries thirteen cells where
    twelve belong, and the D/B cell lost its footnote marker so the table read
    "1)" one way and "(*)" the other. A compatibility table must mirror across
    its diagonal; that is a property of the thing itself, not of a typesetting,
    and checking it caught both defects. The English edition mirrors in all 144
    cells and is what this computes with.
    """
    rules = get_compliance_rules()["adn_hold_separation"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "findings": []}

    in_cargo_tanks = _adn_cargo_tank_positions(products)
    if in_cargo_tanks:
        return {"status": "not_available_for_mode", "findings": [],
                "mode_note": _adn_mode_note(in_cargo_tanks, lang)}

    classes = {str(p.get("class") or "").strip() for _e, _i, p in products}
    classes.discard("")
    findings: list[dict[str, Any]] = []
    by_provision = {rule["provision"]: rule for rule in rules["rules"]}

    if len(classes) > 1:
        rule = by_provision["7.1.4.3.1"]
        findings.append({
            "provision": rule["provision"],
            "metres": rule["metres"],
            "message": (rule["message"].get(lang) or rule["message"]["en"]).format(
                classes=", ".join(sorted(classes))),
        })

    # Column (12) per package, with the doubt attached. `cones` is None where
    # the ADN does not list the substance and where the count is not settled —
    # in both cases the provisions below must not fire, and the reason differs.
    cones: dict[int, int | None] = {}
    unsettled: list[str] = []
    for entry, index, product in products:
        un_number = str(product.get("un_number") or product.get("un") or "").strip()
        signal = database.adn_blue_cones(un_number)
        if signal is None or not signal["certain"]:
            cones[id(product)] = None
            if signal is not None:
                unsettled.append(_product_label(entry, product, index))
            continue
        cones[id(product)] = signal["cones"]

    rule = by_provision["7.1.4.3.3"]
    far_apart = [
        (entry, index, product) for entry, index, product in products
        if str(product.get("class") or "").strip() in rule["classes"]
        or (str(product.get("class") or "").strip() in rule["also_classes"]
            and cones[id(product)] == rule["cones"])
    ]
    if far_apart and len(classes) > 1:
        findings.append({
            "provision": rule["provision"],
            "metres": rule["metres"],
            "message": (rule["message"].get(lang) or rule["message"]["en"]).format(
                products=", ".join(sorted(
                    _product_label(entry, product, index)
                    for entry, index, product in far_apart))),
        })

    # 7.1.4.3.2 is a prohibition on sharing a hold, not a distance, and it needs
    # both sides: two cones on one package and one cone on a *flammable* one.
    # Flammable is read from the classification code, where F is the letter the
    # ADN itself sorts on, and from class 3, which is flammable by definition.
    two_cones = [(entry, index, product) for entry, index, product in products
                 if cones[id(product)] == 2]
    one_cone_flammable = [
        (entry, index, product) for entry, index, product in products
        if cones[id(product)] == 1 and (
            str(product.get("class") or "").strip() == "3"
            or "F" in re.sub(r"^\d(\.\d)?", "",
                             str(product.get("classification_code") or "").upper()))
    ]
    if two_cones and one_cone_flammable:
        rule = by_provision["7.1.4.3.2"]
        finding = {
            "provision": rule["provision"],
            "message": rule["message"].get(lang) or rule["message"]["en"],
            "two_cones": sorted(_product_label(entry, product, index)
                                for entry, index, product in two_cones),
            "one_cone_flammable": sorted(
                _product_label(entry, product, index)
                for entry, index, product in one_cone_flammable),
        }
        # 7.1.4.3.2 forbids *sharing a hold*, and until the stowage plan of
        # v1.84.0 there was no hold to compare: the finding could only say the
        # two kinds were both on board. Where the boatmaster has said which
        # hold each is in, the prohibition can be applied to what he wrote —
        # and the holds where it is actually breached are named.
        clashing = sorted({
            _hold_of(two) for _e, _i, two in two_cones
            if _hold_of(two) and _hold_of(two) in {
                _hold_of(one) for _e2, _i2, one in one_cone_flammable}})
        if clashing:
            finding["holds"] = clashing
            finding["message"] = (
                f"{finding['message']} "
                + (rules["shared_hold"].get(lang) or rules["shared_hold"]["en"]).format(
                    holds=", ".join(clashing)))
        elif all(_hold_of(product) for _e, _i, product in two_cones + one_cone_flammable):
            finding["holds"] = []
            finding["message"] = (
                f"{finding['message']} "
                + (rules["separate_holds"].get(lang) or rules["separate_holds"]["en"]))
        findings.append(finding)

    # 7.1.4.3.4 — class 1 against itself. Two explosives may share a hold only
    # where the table says so, and the table sorts on the *compatibility group*:
    # the trailing letter of the classification code, 1.1D → D. Each unordered
    # pair is judged once; the table mirrors, so the order the user typed them in
    # cannot change the answer.
    compat = rules.get("class_1_compatibility")
    if compat:
        by_group: dict[str, list[str]] = {}
        for entry, index, product in products:
            if not str(product.get("class") or "").strip().startswith("1"):
                continue
            code = str(product.get("classification_code") or "").strip().upper()
            group = re.sub(r"^\d(\.\d)?", "", code)[:1]
            if group in compat["table"]:
                by_group.setdefault(group, []).append(
                    _product_label(entry, product, index))
        present = sorted(by_group)
        for i, a in enumerate(present):
            for b in present[i:]:
                # A group against itself only matters where the table makes it
                # conditional — L with L, N with N — and never where it says X.
                if a == b and len(by_group[a]) < 2:
                    continue
                cell = compat["table"][a][b]
                if cell == "permitted":
                    continue
                names = ", ".join(sorted(set(by_group[a] + by_group[b])))
                if cell == "forbidden":
                    text = compat["forbidden_message"]
                    findings.append({
                        "provision": compat["provision"],
                        "compatibility_groups": [a, b],
                        "message": (text.get(lang) or text["en"]).format(
                            a=a, b=b, products=names),
                    })
                else:
                    text = compat["conditional_message"]
                    findings.append({
                        "provision": compat["provision"],
                        "compatibility_groups": [a, b],
                        "message": (text.get(lang) or text["en"]).format(
                            a=a, b=b, products=names),
                        "conditions": [
                            compat["conditions"][str(number)].get(lang)
                            or compat["conditions"][str(number)]["en"]
                            for number in cell
                        ],
                    })

    result: dict[str, Any] = {
        "status": "ok",
        "scope": "packages_in_holds",
        "findings": findings,
        "source": rules["source"],
    }
    if unsettled:
        unknown = rules["cones_not_settled"]
        result["not_assessed"] = (unknown.get(lang) or unknown["en"]).format(
            products=", ".join(sorted(unsettled)))
        result["cones_not_settled"] = sorted(unsettled)
    return result


def _adn_cargo_tank_positions(products: list[tuple[Any, int, dict[str, Any]]]) -> list[str]:
    """The positions that travel in cargo tanks, and are therefore not on a dry
    cargo vessel.

    Only `tank` counts. `portable_tank` is a tank container, and 7.1.1.18 puts
    the carriage of tank containers and portable tanks under the requirements
    for carriage of packages — so it sails on a dry cargo vessel and chapter 7.1
    is exactly the right chapter for it. Rounding the two together would take
    away answers that do apply.
    """
    return sorted({
        _product_label(entry, product, index)
        for entry, index, product in products
        if str(product.get("carriage_mode") or "").strip() == "tank"})


def _adn_mode_note(positions: list[str], lang: str) -> str:
    text = get_compliance_rules()["adn_carriage_admission"][
        "chapter_7_1_not_for_tank_vessels"]
    return (text.get(lang) or text["en"]).format(products=", ".join(positions))


def check_adn_mixed_loading(
    entries: list[dict[str, Any]], language: str = "nl",
) -> list[dict[str, str]]:
    """ADN 7.1.4.2, 7.1.4.4/7.1.4.5 and 7.1.4.10: the water's own prohibitions.

    Until this check an inland-only consignment was measured against ADR 7.5.2 —
    a road chapter the ADN does not prescribe — with a note claiming the ADN's
    own regime was not held. The distances of 7.1.4.3 have in fact been applied
    since v1.59.0 (`check_adn_hold_separation`); what was missing is the rest of
    the chapter, read now in the English edition (printed pages 394-399) and
    the Dutch edition, which agree:

    - **7.1.4.2** — a vessel carrying Class 5.1 in bulk carries nothing else.
      Within the consignment that is a finding; for the rest of the vessel it
      is a condition, because this application cannot see the other holds.
    - **7.1.4.10** — the foodstuffs precaution, gated by **special provision
      802** in column (6) of the ADN's own table A rather than assumed for
      every 6.1 label the way the road's CV28 was borrowed here before. Its
      separation measures are the ADN's own: full-height partitions, unmarked
      packages in between, or 0.8 m.
    - **7.1.4.4/7.1.4.5** — the container exceptions. 7.1.4.3 does not apply
      inside closed containers and closed vehicles or wagons; other containers
      reduce the 3.00 m to 2.40 m; and a vessel carrying only containers may
      answer the whole prohibition with the IMDG Code's stowage and
      segregation requirements. The trigger is the consignor's own statement
      (the `containers_only` field of 7.1.5.0.2), never a packaging type.
    """
    rules = get_compliance_rules()["adn_mixed_loading"]["rules"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    findings: list[dict[str, str]] = []
    if not products:
        return findings

    bulk_51 = [
        _product_label(entry, product, index)
        for entry, index, product in products
        if _primary_class(product).startswith("5.1")
        and str(product.get("carriage_mode") or "").strip() == "bulk"]
    if bulk_51:
        others = [
            label for entry, index, product in products
            if (label := _product_label(entry, product, index)) not in bulk_51]
        if others:
            findings.append({
                "rule": "ADN 7.1.4.2",
                "severity": "error",
                "message": pick(rules["bulk_51_with_others"], lang),
                "products": ", ".join(dict.fromkeys(bulk_51 + others)),
            })
        else:
            findings.append({
                "rule": "ADN 7.1.4.2",
                "severity": "warning",
                "message": pick(rules["bulk_51_alone"], lang),
                "products": ", ".join(bulk_51),
            })

    food = [
        _product_label(entry, product, index)
        for entry, index, product in products
        if "802" in database.adn_special_provisions(
            str(product.get("un_number") or "").strip())]
    if food:
        findings.append({
            "rule": "ADN 7.1.4.10 (802)",
            "severity": "warning",
            "message": pick(rules["foodstuffs_802"], lang),
            "products": ", ".join(food),
        })

    declared = [
        _product_label(entry, product, index)
        for entry, index, product in products if product.get("containers_only")]
    if declared and len(declared) == len(products):
        findings.append({
            "rule": "ADN 7.1.4.4 / 7.1.4.5",
            "severity": "info",
            "message": pick(rules["containers_exception"], lang),
            "products": ", ".join(declared),
        })
    return findings


#: 5.3.1.1.2 orders class 1 divisions by danger for the placard choice; 1.1
#: first. The provision spells the order out rather than leaving it to the
#: numeric sort, which would put 1.5 last instead of second.
_ADN_CLASS1_ORDER = ("1.1", "1.5", "1.2", "1.3", "1.6", "1.4")


def check_adn_placarding(
    entries: list[dict[str, Any]], language: str = "nl",
    exemption_status: str | None = None,
) -> dict[str, Any]:
    """ADN 5.3: what the cargo transport units on board must show.

    The road got this answer in v1.57.0 for its own vehicle; the water leg had
    nothing, while its chapter 5.3 addresses the containers, road vehicles and
    wagons that come on board a dry cargo vessel. Read in the English edition
    (printed pages 309–321) and sections 5.3.1–5.3.6 of the official Dutch
    edition, which agree.

    What shapes the answer is that **the application cannot see which kind of
    cargo transport unit the packages travel in** — and the kind decides
    everything. A container is placarded for any class, both sides and each
    end (5.3.1.2); a wagon carrying packages likewise, both sides (5.3.1.5.3);
    a road vehicle carrying packages placards only for class 1 and class 7
    (5.3.1.5.1/5.3.1.5.2) — *except* that the note to 5.3.1.5.2 placards it
    for every class when the ADN journey precedes a voyage by sea. So the
    label models are computed once from columns (5) and (6), and the placement
    rules are given per kind, each under its own provision, instead of one
    kind's answer standing in for the others.

    The elevated temperature mark of 5.3.3 was not derived until v1.151.0,
    because it turns on a carriage temperature nothing in the consignment
    implied. That is now a field, and 5.3.3 is answered from it — an absent
    temperature reports the mark as unassessed rather than as not required.
    Still not derived: the exclusive-use plates of 5.3.2.1.4, exclusive use
    not being a field.
    A cargo tank consignment is chapter 7.2: the vessel shows the signals of
    7.2.5.0, which `check_adn_signals` answers, and 5.3's units are not its
    question — so that case is named rather than answered here.
    """
    rules = get_compliance_rules()["adn_placarding"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "placards": [], "marks": []}

    in_cargo_tanks = _adn_cargo_tank_positions(products)
    if in_cargo_tanks:
        return {"status": "not_available_for_mode", "placards": [], "marks": [],
                "mode_note": _adn_mode_note(in_cargo_tanks, lang)}

    named = {id(product): _product_label(entry, product, index)
             for entry, index, product in products}
    goods = [product for _entry, _index, product in products]

    def text(key: str) -> str:
        block = rules[key]
        return block.get(lang) or block["en"]

    placards: list[dict[str, Any]] = []

    # The label models of columns (5) and (6), 9A folded into 9 (5.3.1.1.4)
    # and class 1 aggregated per 5.3.1.1.2 below.
    labels = sorted({
        "9" if part.strip().upper() == "9A" else part.strip()
        for p in goods
        for part in str(p.get("labels") or "").replace("+", ",").split(",")
        if part.strip() and not part.strip().startswith("1")})
    class1 = [p for p in goods
              if str(p.get("class") or "").strip().startswith("1")
              and str(p.get("classification_code") or "").strip().upper() != "1.4S"]
    def _division(product: dict[str, Any]) -> str:
        match = re.match(r"1\.\d",
                         str(product.get("classification_code") or "").strip())
        return match.group(0) if match else "1"

    divisions = sorted({_division(p) for p in class1})
    class1_aggregated = None
    if class1:
        known = [d for d in _ADN_CLASS1_ORDER if d in divisions]
        chosen = known[0] if known else "1"
        # 1.5 D beside Division 1.2 is placarded as 1.1 — the provision's own
        # escalation, not an ordering artefact.
        if "1.5" in divisions and "1.2" in divisions:
            chosen = "1.1"
        groups = {re.sub(r"^1(\.\d)?", "",
                         str(p.get("classification_code") or "").strip().upper())
                  for p in class1}
        groups.discard("")
        display = chosen if len(divisions) > 1 or len(groups) != 1 \
            else f"{chosen}{next(iter(groups))}"
        labels.append(display)
        if len(divisions) > 1:
            class1_aggregated = chosen
    labels = sorted(set(labels))

    if labels:
        placards.append({
            "class": None,
            "provision": "5.3.1.1.1",
            "message": text("label_models").format(labels=", ".join(labels)),
            "products": sorted(named.values()),
            "label_models": labels,
            "required": True,
        })
    if class1_aggregated:
        placards.append({
            "class": "1",
            "provision": "5.3.1.1.2",
            "message": text("class1_aggregated").format(division=class1_aggregated),
            "products": sorted({named[id(p)] for p in class1}),
        })
    subsidiary = any("," in str(p.get("labels") or "")
                     or "+" in str(p.get("labels") or "") for p in goods)
    if subsidiary and labels:
        placards.append({
            "class": None,
            "provision": "5.3.1.1.5",
            "message": text("no_subsidiary_duplicate"),
            "products": [],
        })

    # Where the placards go, per kind of cargo transport unit — the kind the
    # application cannot see, so every kind gets its rule.
    in_tanks_or_bulk = any(
        str(p.get("carriage_mode") or "").strip() in ("portable_tank", "bulk")
        for p in goods)
    has_class7 = any(str(p.get("class") or "").strip().startswith("7")
                     for p in goods)
    if in_tanks_or_bulk:
        placards.append({"class": None, "provision": "5.3.1.4.1",
                         "message": text("tank_bulk"), "products": [],
                         "required": True})
    placards.append({"class": None, "provision": "5.3.1.2",
                     "message": text("ctu_container"), "products": []})
    class1_ids = {id(p) for p in class1}
    if class1 or has_class7:
        placards.append({
            "class": None, "provision": "5.3.1.5.1/5.3.1.5.2",
            "message": text("ctu_vehicle_class17"),
            "products": sorted({named[id(p)] for p in goods
                                if id(p) in class1_ids
                                or str(p.get("class") or "").strip().startswith("7")}),
            "required": True,
        })
    elif not in_tanks_or_bulk:
        placards.append({"class": None, "provision": "5.3.1.5.2",
                         "message": text("ctu_vehicle_none"), "products": []})
    placards.append({"class": None, "provision": "5.3.1.5.3",
                     "message": text("ctu_wagon"), "products": []})

    empty = sorted({named[id(p)] for p in goods if p.get("empty_uncleaned")})
    if empty:
        placards.append({
            "class": None, "provision": "5.3.1.6.1",
            "message": text("empty_uncleaned").format(products=", ".join(empty)),
            "products": empty,
        })

    marks: list[dict[str, Any]] = []
    plates = rules["orange_plates"]
    marks.append({"provision": plates["provision"],
                  "message": plates.get(lang) or plates["en"],
                  "kind": "orange_plates"})

    if any(str(p.get("carriage_mode") or "").strip() == "portable_tank"
           for p in goods):
        numbers = sorted({
            (str(p.get("hazard_number") or "").strip(),
             str(p.get("un_number") or p.get("un") or "").strip())
            for p in goods
            if str(p.get("carriage_mode") or "").strip() == "portable_tank"
            and str(p.get("hazard_number") or "").strip()
            and str(p.get("un_number") or p.get("un") or "").strip()})
        without = sorted({
            named[id(p)] for p in goods
            if str(p.get("carriage_mode") or "").strip() == "portable_tank"
            and not str(p.get("hazard_number") or "").strip()})
        if numbers:
            tank = rules["tank_plates"]
            marks.append({
                "provision": tank["provision"],
                "message": (tank.get(lang) or tank["en"]).format(
                    numbers=", ".join(
                        f"{hazard} / UN {un}" for hazard, un in numbers)),
                "kind": "tank_plates",
                "required": True,
            })
        if without:
            marks.append({
                "provision": "5.3.2.1.2",
                "message": text("tank_plates_no_number").format(
                    products=", ".join(without)),
                "kind": "tank_plates",
                "required": None,
            })

    # 5.3.3, read on printed page 319 of the English edition: liquid at 100 °C
    # or above, solid at 240 °C or above. The thresholds match IMDG's; the
    # placement does not, and it is ADN's own wording that is given.
    hot = [p for p in goods
           if (_num(p.get("carriage_temperature")) or -273) >= 100]
    unknown_hot = [p for p in goods
                   if p.get("molten") and _num(p.get("carriage_temperature")) is None]
    if hot:
        block = rules["elevated_temperature"]
        marks.append({
            "provision": block["provision"],
            "message": (block.get(lang) or block["en"]).format(
                products=", ".join(sorted({named[id(p)] for p in hot})),
                temperature=", ".join(
                    f"{_num(p.get('carriage_temperature')):g} °C"
                    for p in sorted(hot, key=lambda x: _num(
                        x.get("carriage_temperature")) or 0))),
            "kind": "elevated_temperature",
            "required": True,
        })
    elif unknown_hot:
        block = rules["elevated_temperature_unknown"]
        marks.append({"provision": block["provision"],
                      "message": block.get(lang) or block["en"],
                      "kind": "elevated_temperature", "required": None})

    sea = rules["sea_chain"]
    marks.append({"provision": sea["provision"],
                  "message": sea.get(lang) or sea["en"], "kind": "sea_chain"})

    green = [p for p in goods if p.get("environmentally_hazardous")]
    if green:
        mark = rules["environmental_mark"]
        marks.append({
            "provision": mark["provision"],
            "message": (mark.get(lang) or mark["en"]).format(
                products=", ".join(sorted({named[id(p)] for p in green}))),
            "kind": "environmental_mark",
        })

    # The ADN exemption is reported as possible, never granted — and section
    # 5.3 is not among the conditions 1.1.3.6.2 keeps alive under it. The full
    # answer stands (over-signalling is the safe direction to be wrong in) and
    # the note says what carrying under the exemption would change.
    if exemption_status == "exempt_possible":
        note = rules["exempt_note"]
        marks.append({"provision": note["provision"],
                      "message": note.get(lang) or note["en"],
                      "kind": "exempt_note"})

    required = [p for p in placards if p.get("required") is True]
    return {
        "status": "ok",
        "scope": "tanks_or_bulk" if in_tanks_or_bulk else "packages",
        "placards": placards,
        "placards_required": bool(required),
        "marks": marks,
        "source": rules["source"],
    }


#: 5.3.1.1.2.2 asks for "the highest hazard" among several divisions of class 1
#: without printing an order, where ADN prints one. The order below is the
#: ordinary reading of hazard within class 1 and is used only to *choose which
#: placard to name*; every division present is still listed to the user, so a
#: wrong choice here cannot hide a division.
_IMDG_CLASS1_ORDER = ("1.1", "1.2", "1.3", "1.5", "1.6", "1.4")


def check_imdg_placarding(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """IMDG 5.3: what a cargo transport unit going to sea must show.

    Road, rail and inland waterway have had their chapter 5.3 derived since
    v1.57.0, v1.121.0 and v1.120.0; sea had nothing, because the Code was
    believed to be unavailable. It is not: resolution MSC.556(108) replaces
    the complete text of the Code, and chapter 5.3 was read out of it
    verbatim (``--quote sea_placarding``) before a line of this was written.

    The sea rule is emphatically not the road rule renumbered:

    * a freight container is placarded **on all four sides** (5.3.1.1.4.1.1),
      where a road vehicle carrying packages is often not placarded at all;
    * the UN number rides **inside the placard or on an orange panel beside
      it** (5.3.2.1.2), not on an orange plate of its own, and it is required
      only in the five cases of 5.3.2.1.1 — never for class 1;
    * the **proper shipping name itself** is marked on the unit (5.3.2.0.1),
      which no land regime asks for;
    * the **marine pollutant mark** (5.3.2.3) has no land counterpart;
    * **class 9 is placarded as model No. 9, never 9A** (5.3.1.1.2) — and 9A
      is exactly what table A gives for the lithium and sodium battery
      entries, so taking the label model across unchanged would put the wrong
      placard on a container of batteries.

    As with ADN, the application cannot see which kind of cargo transport unit
    the goods travel in, and the kind decides the placement. So the placement
    rules are given per kind, each under its own provision, rather than one
    kind's answer standing in for the others.

    One thing is derived here that ADN's 5.3.3 still reports as unassessed:
    the elevated temperature mark. It turns on the carriage temperature, which
    is now a field — absent, this says so rather than implying no mark is
    needed.
    """
    from app.services.dg.autofill import total_quantity

    rules = get_compliance_rules()["imdg_placarding"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "placards": [], "marks": []}

    named = {id(product): _product_label(entry, product, index)
             for entry, index, product in products}
    goods = [product for _entry, _index, product in products]

    def text(key: str) -> str:
        block = rules[key]
        return block.get(lang) or block["en"]

    def names(items: list[dict[str, Any]]) -> str:
        return ", ".join(sorted({named[id(p)] for p in items}))

    placards: list[dict[str, Any]] = []

    # --- 5.3.1.1.2, the primary hazard ---------------------------------------
    #
    # The primary hazard, not the label models: 5.3.1.1.2 says "the primary
    # hazard of the goods contained", and 5.3.1.1.3 adds the subsidiary ones
    # separately. Class 9 is placarded as 9 even where table A gives 9A.
    def _placard_class(product: dict[str, Any]) -> str:
        value = _primary_class(product) or str(product.get("class") or "").strip()
        return "9" if value.upper() in {"9A", "9"} else value

    # 1.4S carries no placard at any quantity, so it is taken out before the
    # primary hazards are collected rather than filtered out of the result.
    class1_4s = [p for p in goods
                 if str(p.get("classification_code") or "").strip().upper() == "1.4S"]
    placardable = [p for p in goods if p not in class1_4s]

    class1 = [p for p in placardable if _placard_class(p).startswith("1")]
    others = [p for p in placardable if not _placard_class(p).startswith("1")]

    primary = sorted({_placard_class(p) for p in others if _placard_class(p)})

    def _division(product: dict[str, Any]) -> str:
        """1.1 through 1.6, from the classification code or the class itself.

        The classification code ("1.4S") carries the division and the
        compatibility group; the class column ("1.4") carries the division
        alone. Either will do, and a class 1 entry that gives neither is
        reported as plain "1" rather than guessed at.
        """
        for value in (product.get("classification_code"), product.get("class")):
            match = re.match(r"1\.\d", str(value or "").strip())
            if match:
                return match.group(0)
        return "1"

    class1_highest = None
    if class1:
        divisions = sorted({_division(p) for p in class1})
        known = [d for d in _IMDG_CLASS1_ORDER if d in divisions]
        chosen = known[0] if known else "1"
        primary.append(chosen)
        if len(divisions) > 1:
            class1_highest = chosen
        primary = sorted(set(primary))

    if primary:
        placards.append({
            "class": None,
            "provision": "5.3.1.1.2",
            "message": text("label_models").format(labels=", ".join(primary)),
            "products": sorted(named.values()),
            "label_models": primary,
            "required": True,
        })
    if class1_highest:
        placards.append({
            "class": "1",
            "provision": "5.3.1.1.2.2",
            "message": text("class1_highest").format(division=class1_highest),
            "products": sorted({named[id(p)] for p in class1}),
        })
    if class1_4s:
        placards.append({
            "class": "1.4S",
            "provision": "5.3.1.1.2.1",
            "message": text("class1_4s").format(products=names(class1_4s)),
            "products": sorted({named[id(p)] for p in class1_4s}),
            "required": False,
        })

    # --- 5.3.1.1.3, the subsidiary hazards -----------------------------------
    subsidiary_labels = sorted({
        part.strip()
        for p in placardable
        for part in str(p.get("subsidiary_risks") or "").replace(
            "+", ",").split(",")
        if part.strip() and part.strip() not in {"-", "–"}})
    if subsidiary_labels:
        placards.append({
            "class": None,
            "provision": "5.3.1.1.3",
            "message": text("subsidiary").format(
                labels=", ".join(subsidiary_labels)),
            "products": [],
            "required": True,
        })
        if len(primary) > 1:
            placards.append({
                "class": None, "provision": "5.3.1.1.3",
                "message": text("no_subsidiary_duplicate"), "products": [],
            })

    if primary or subsidiary_labels:
        placards.append({"class": None, "provision": "5.3.1.2.1",
                         "message": text("contrast"), "products": []})

    # --- 5.3.1.1.4.1, where they go, per kind of unit -------------------------
    placards.append({"class": None, "provision": "5.3.1.1.4.1.1",
                     "message": text("where_container"), "products": []})
    placards.append({"class": None, "provision": "5.3.1.1.4.1.2",
                     "message": text("where_wagon"), "products": []})
    placards.append({"class": None, "provision": "5.3.1.1.4.1.3",
                     "message": text("where_multi_compartment"), "products": []})
    placards.append({"class": None, "provision": "5.3.1.1.4.1.4",
                     "message": text("where_flexible_bulk"), "products": []})
    placards.append({"class": None, "provision": "5.3.1.1.4.1.5",
                     "message": text("where_other"), "products": []})

    if any(_placard_class(p).startswith("7") for p in placardable):
        placards.append({
            "class": "7", "provision": "5.3.1.1.5.1",
            "message": text("class7"),
            "products": sorted({named[id(p)] for p in placardable
                                if _placard_class(p).startswith("7")}),
            "required": True,
        })

    placards.append({"class": None, "provision": "5.3.1.1.1.1",
                     "message": text("visible_labels"), "products": []})

    # --- 5.3.2, the marking half ---------------------------------------------
    marks: list[dict[str, Any]] = []
    marks.append({"provision": "5.3.2.0.1", "message": text("psn_marking"),
                  "kind": "proper_shipping_name"})

    in_tank = [p for p in goods
               if str(p.get("carriage_mode") or "").strip() == "portable_tank"]
    in_bulk = [p for p in goods
               if str(p.get("carriage_mode") or "").strip() == "bulk"]
    packaged = [p for p in goods
                if str(p.get("carriage_mode") or "packages").strip()
                not in ("portable_tank", "bulk")]

    if in_tank:
        marks.append({"provision": "5.3.2.1.1.1", "message": text("un_number_tank"),
                      "kind": "un_number", "required": True})
    if in_bulk:
        marks.append({"provision": "5.3.2.1.1.5", "message": text("un_number_bulk"),
                      "kind": "un_number", "required": True})

    # 5.3.2.1.1.2 is arithmetic the application can do: more than 4,000 kg
    # gross of a single UN number that is the only dangerous goods aboard.
    # Both halves of the condition have to hold, and the mass has to be known —
    # an unentered mass is reported as unassessed, never as "under 4,000 kg".
    non_class1 = [p for p in packaged if not _placard_class(p).startswith("1")]
    un_numbers = {str(p.get("un_number") or p.get("un") or "").strip()
                  for p in goods}
    single_un = len({u for u in un_numbers if u}) == 1 and len(goods) == len(non_class1)
    if single_un and non_class1:
        heavy: list[dict[str, Any]] = []
        unknown: list[dict[str, Any]] = []
        total_gross = 0.0
        measured = False
        for product in non_class1:
            gross = _num(product.get("gross_mass_per_package"))
            packages = _num(product.get("quantity_packages"))
            if gross is not None and packages is not None:
                total_gross += gross * packages
                measured = True
            else:
                amount, unit = total_quantity(product)
                if amount is not None and unit == "kg":
                    total_gross += amount
                    measured = True
                else:
                    unknown.append(product)
        if measured and not unknown and total_gross > 4000:
            heavy = non_class1
        if heavy:
            marks.append({
                "provision": "5.3.2.1.1.2",
                "message": text("un_number_4000kg").format(products=names(heavy)),
                "kind": "un_number", "required": True,
            })
        elif unknown:
            marks.append({
                "provision": "5.3.2.1.1.2",
                "message": text("un_number_4000kg_unknown").format(
                    products=names(unknown)),
                "kind": "un_number", "required": None,
            })

    if any(_placard_class(p).startswith("7") for p in goods):
        marks.append({"provision": "5.3.2.1.1.3/5.3.2.1.1.4",
                      "message": text("un_number_class7"),
                      "kind": "un_number", "required": None})
    if class1 or class1_4s:
        marks.append({"provision": "5.3.2.1.1",
                      "message": text("un_number_not_class1"), "kind": "un_number"})

    marks.append({"provision": "5.3.2.1.2", "message": text("un_number_how"),
                  "kind": "un_number"})

    # 5.3.2.3, the mark no land regime has. The sea layer sets marine_pollutant
    # from column (4) of the Dangerous Goods List; the environmentally
    # hazardous flag is the land mark of 5.2.1.6 and is not the same thing, so
    # only the sea value decides here.
    polluting = [p for p in goods
                 if str(p.get("marine_pollutant") or "").strip().upper()
                 in {"P", "Y", "YES", "JA", "TRUE", "1"}]
    if polluting:
        marks.append({
            "provision": "5.3.2.3.1",
            "message": text("marine_pollutant").format(products=names(polluting)),
            "kind": "marine_pollutant", "required": True,
        })

    # 5.3.2.2, the elevated temperature mark — liquid at 100 °C or above, solid
    # at 240 °C or above. The threshold depends on the state, and the state is
    # not a field either; the liquid threshold is the lower of the two, so
    # using it is the safe direction to be wrong in, and the message names both.
    hot: list[dict[str, Any]] = []
    unknown_temperature: list[dict[str, Any]] = []
    temperatures: set[float] = set()
    for product in goods:
        value = _num(product.get("carriage_temperature"))
        if value is None:
            if product.get("molten"):
                unknown_temperature.append(product)
            continue
        if value >= 100:
            hot.append(product)
            temperatures.add(value)
    if hot:
        marks.append({
            "provision": "5.3.2.2.1",
            "message": text("elevated_temperature").format(
                products=names(hot),
                temperature=", ".join(f"{t:g} °C" for t in sorted(temperatures))),
            "kind": "elevated_temperature", "required": True,
        })
    elif unknown_temperature:
        marks.append({
            "provision": "5.3.2.2.1",
            "message": text("elevated_temperature_unknown"),
            "kind": "elevated_temperature", "required": None,
        })

    # 5.3.2.4 hands the answer to 3.4.5.5, and whether a consignment travels as
    # a limited quantity is the LQ check's answer, not this chapter's. So the
    # substances with a non-zero column 7a value are named as the ones it can
    # apply to — which is what the provision lets this check honestly say.
    limited = [p for p in goods
               if str(p.get("limited_quantity") or "").strip() not in ("", "0", "-", "–")]
    if limited:
        marks.append({
            "provision": "5.3.2.4",
            "message": text("limited_quantities").format(products=names(limited)),
            "kind": "limited_quantities",
        })

    marks.append({"provision": "5.3.1.1.1.2", "message": text("seawater"),
                  "kind": "seawater"})
    marks.append({"provision": "5.3.1.1.1.3",
                  "message": text("remove_after_discharge"), "kind": "removal"})

    required = [p for p in placards if p.get("required") is True]
    return {
        "status": "ok",
        "scope": "tanks_or_bulk" if (in_tank or in_bulk) else "packages",
        "placards": placards,
        "placards_required": bool(required),
        "marks": marks,
        "source": rules["source"],
    }


def check_rid_placarding(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """RID 5.3: what the wagons and large containers on the rail leg must show.

    Read in the English edition (printed pages 837–845, plus the column (5)
    explanation of 3.2.1 on page 258) and the German edition, which agree.
    Three things make the rail answer its own rather than the road's on loan:

    - **A wagon carrying packages is placarded for every class** (5.3.1.5),
      where a road vehicle carrying packages placards only for classes 1 and 7.
      Both sides, no rear.
    - **The orange plates attach only where column (20) gives a hazard
      identification number** (5.3.2.1.1), and then they carry the two numbers
      on each side of the tank, bulk wagon or container. There are no plain
      front-and-rear plates on rail — printing the road's plate rule on a rail
      answer would prescribe equipment RID does not ask for.
    - **The shunting labels of 5.3.4** are only ever affixed in two cases —
      class 1 on both sides of full-load wagons, class 2 on both sides of
      tank-type wagons (column (5) explanation, page 258). Which substances
      carry the bracketed model in RID's own column (5) this application
      cannot see: its table is the ADR's, which carries neither model 13 nor
      model 15. So the case is named as a condition, and 5.4.1.1.1 (c) keeps
      model 13 off the document either way.

    Also derived: the orange band of 5.3.5, because the state of the gas is
    the first digit of the classification code (2 liquefied, 3 refrigerated
    liquefied, 4 dissolved), and the environmentally hazardous mark of 5.3.6.
    There is no exemption branch, and since v1.124.0 that is a reading rather
    than caution: RID 1.1.3.6 only bounds the ancillary-carriage exemption of
    1.1.3.1 (c) — RID has no general small-load relief — so chapter 5.3 stands
    for every ordinary rail consignment whatever its points total.
    """
    rules = get_compliance_rules()["rid_placarding"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "placards": [], "marks": []}

    named = {id(product): _product_label(entry, product, index)
             for entry, index, product in products}
    goods = [product for _entry, _index, product in products]

    def text(key: str) -> str:
        block = rules[key]
        return block.get(lang) or block["en"]

    placards: list[dict[str, Any]] = []
    labels = sorted({
        "9" if part.strip().upper() == "9A" else part.strip()
        for p in goods
        for part in str(p.get("labels") or "").replace("+", ",").split(",")
        if part.strip() and not part.strip().startswith("1")})
    class1 = [p for p in goods
              if str(p.get("class") or "").strip().startswith("1")
              and str(p.get("classification_code") or "").strip().upper() != "1.4S"]

    def _division(product: dict[str, Any]) -> str:
        match = re.match(r"1\.\d",
                         str(product.get("classification_code") or "").strip())
        return match.group(0) if match else "1"

    divisions = sorted({_division(p) for p in class1})
    class1_aggregated = None
    if class1:
        known = [d for d in _ADN_CLASS1_ORDER if d in divisions]
        chosen = known[0] if known else "1"
        if "1.5" in divisions and "1.2" in divisions:
            chosen = "1.1"
        groups = {re.sub(r"^1(\.\d)?", "",
                         str(p.get("classification_code") or "").strip().upper())
                  for p in class1}
        groups.discard("")
        display = chosen if len(divisions) > 1 or len(groups) != 1 \
            else f"{chosen}{next(iter(groups))}"
        labels.append(display)
        if len(divisions) > 1:
            class1_aggregated = chosen
    labels = sorted(set(labels))

    if labels:
        placards.append({
            "class": None,
            "provision": "5.3.1.1.1",
            "message": text("label_models").format(labels=", ".join(labels)),
            "products": sorted(named.values()),
            "label_models": labels,
            "required": True,
        })
    if class1_aggregated:
        placards.append({
            "class": "1",
            "provision": "5.3.1.1.2",
            "message": text("class1_aggregated").format(division=class1_aggregated),
            "products": sorted({named[id(p)] for p in class1}),
        })
    if any("," in str(p.get("labels") or "") or "+" in str(p.get("labels") or "")
           for p in goods) and labels:
        placards.append({
            "class": None, "provision": "5.3.1.1.5",
            "message": text("no_subsidiary_duplicate"), "products": [],
        })

    in_tanks_or_bulk = any(
        str(p.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank", "bulk") for p in goods)
    if in_tanks_or_bulk:
        placards.append({"class": None, "provision": "5.3.1.4.1",
                         "message": text("tank_bulk"), "products": [],
                         "required": True})
    placards.append({"class": None, "provision": "5.3.1.2",
                     "message": text("ctu_container"), "products": []})
    if not in_tanks_or_bulk:
        placards.append({"class": None, "provision": "5.3.1.5",
                         "message": text("ctu_wagon_packages"), "products": [],
                         "required": True})

    empty = sorted({named[id(p)] for p in goods if p.get("empty_uncleaned")})
    if empty:
        placards.append({
            "class": None, "provision": "5.3.1.6",
            "message": text("empty_uncleaned").format(products=", ".join(empty)),
            "products": empty,
        })

    marks: list[dict[str, Any]] = []
    tank_bulk_goods = [
        p for p in goods
        if str(p.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank", "bulk")]
    if tank_bulk_goods:
        numbers = sorted({
            (str(p.get("hazard_number") or "").strip(),
             str(p.get("un_number") or p.get("un") or "").strip())
            for p in tank_bulk_goods
            if str(p.get("hazard_number") or "").strip()
            and str(p.get("un_number") or p.get("un") or "").strip()})
        without = sorted({
            named[id(p)] for p in tank_bulk_goods
            if not str(p.get("hazard_number") or "").strip()})
        plates = rules["orange_plates_hin"]
        if numbers:
            marks.append({
                "provision": plates["provision"],
                "message": (plates.get(lang) or plates["en"]).format(
                    numbers=", ".join(
                        f"{hazard} / UN {un}" for hazard, un in numbers)),
                "kind": "orange_plates",
                "required": True,
            })
        if without:
            marks.append({
                "provision": "5.3.2.1.1",
                "message": text("orange_plates_no_number").format(
                    products=", ".join(without)),
                "kind": "orange_plates",
                "required": None,
            })
    else:
        single = {str(p.get("un_number") or p.get("un") or "").strip()
                  for p in goods}
        if len(single) == 1:
            full = rules["orange_plates_full_load"]
            marks.append({"provision": full["provision"],
                          "message": full.get(lang) or full["en"],
                          "kind": "orange_plates", "required": None})

    # 5.3.4 — since v1.123.0 the per-substance half is read: column (5) of
    # RID's own table A, extracted from the English and German editions,
    # which agree on all 351 rows that bracket a model. A substance the seed
    # does not list prints no model in either edition — a real absence — so
    # the trigger classes without a model are told so instead of hedged at.
    # What stays a condition is what stays invisible: whether a wagon
    # comprises a full load.
    has_class2_tank = any(
        str(p.get("class") or "").strip() == "2"
        and str(p.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank") for p in goods)
    if class1 or has_class2_tank:
        # Whether a substance carries a bracketed model is read (v1.123.0);
        # whether its case is met is decidable per line since v1.124.0 — the
        # class 2 case by the declared mode of carriage, the class 1 case by
        # the consignor's own full-load statement.
        decided: dict[str, list[str]] = {}
        conditional: dict[str, list[str]] = {}
        seed_read = True
        for p in goods:
            models = database.rid_shunting_models(
                str(p.get("un_number") or p.get("un") or "").strip())
            if models is None:
                seed_read = False
                break
            if not models:
                continue
            label = named[id(p)]
            cls = str(p.get("class") or "").strip()
            in_tank = str(p.get("carriage_mode") or "").strip() \
                in ("tank", "portable_tank")
            if (cls == "2" and in_tank) or (
                    cls.startswith("1") and p.get("full_load")):
                decided[label] = models
            else:
                conditional[label] = models
        if not seed_read:
            shunt = rules["shunting_labels"]
            marks.append({
                "provision": shunt["provision"],
                "message": shunt.get(lang) or shunt["en"],
                "kind": "shunting_labels",
                "required": None,
            })
        else:
            if decided:
                shunt = rules["shunting_required"]
                items = "; ".join(
                    f"{label} — {', '.join(models)}"
                    for label, models in sorted(decided.items()))
                marks.append({
                    "provision": shunt["provision"],
                    "message": (shunt.get(lang) or shunt["en"]).format(
                        items=items),
                    "kind": "shunting_labels",
                    "required": True,
                })
            if conditional:
                shunt = rules["shunting_models_read"]
                items = "; ".join(
                    f"{label} — {', '.join(models)}"
                    for label, models in sorted(conditional.items()))
                marks.append({
                    "provision": shunt["provision"],
                    "message": (shunt.get(lang) or shunt["en"]).format(
                        items=items),
                    "kind": "shunting_labels",
                    "required": None,
                })
            if not decided and not conditional:
                marks.append({
                    "provision": "5.3.4",
                    "message": text("shunting_none_read"),
                    "kind": "shunting_labels",
                    "required": False,
                })

    band = sorted({
        named[id(p)] for p in goods
        if str(p.get("class") or "").strip() == "2"
        and str(p.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank")
        and str(p.get("classification_code") or "").strip()[:1] in ("2", "3", "4")})
    if band:
        mark = rules["orange_band"]
        marks.append({
            "provision": mark["provision"],
            "message": (mark.get(lang) or mark["en"]).format(
                products=", ".join(band)),
            "kind": "orange_band",
            "required": True,
        })

    green = [p for p in goods if p.get("environmentally_hazardous")]
    if green:
        mark = rules["environmental_mark"]
        marks.append({
            "provision": mark["provision"],
            "message": (mark.get(lang) or mark["en"]).format(
                products=", ".join(sorted({named[id(p)] for p in green}))),
            "kind": "environmental_mark",
        })

    required = [p for p in placards if p.get("required") is True]
    return {
        "status": "ok",
        "scope": "tanks_or_bulk" if in_tanks_or_bulk else "packages",
        "placards": placards,
        "placards_required": bool(required),
        "marks": marks,
        "source": rules["source"],
    }


def check_adn_carriage_admission(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADN 3.2.1, column (8): may these goods travel this way on the water?

    The road side got this answer in v1.66.0 and the water side did not, so an
    inland consignment declared as bulk or as a cargo tank was measured against
    chapter 7.1 as though it were a stack of packages. Column (8) is where the
    ADN says which of the three is allowed, and it is a short list:

    - **empty** — carriage in packages only.
    - **B** — packages and bulk, and 7.1.1.11 forbids bulk without it.
    - **T** — packages and tank vessels, and 7.2.1.21 hands that carriage to
      table C.

    Two provisions decide what the modes mean here. **7.1.1.21** forbids carriage
    in cargo tanks on a dry cargo vessel, so a cargo tank load is a tank vessel
    and belongs to chapter 7.2 rather than to the chapter every other ADN check
    in this file implements. **7.1.1.18** goes the other way for tank containers
    and portable tanks: their carriage must meet the requirements for carriage of
    packages, so they sail on a dry cargo vessel and column (8) is not their gate.

    Table C is not in this repository. Where column (8) permits a tank vessel,
    saying so is the whole of the answer — the vessel type, the cargo tank type
    and the conditions that go with them are in table C, and this says plainly
    that it has not read them rather than leaving the silence to be discovered.
    """
    rules = get_compliance_rules()["adn_carriage_admission"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "items": []}

    def text(key: str, **values: Any) -> str:
        block = rules[key]
        return (block.get(lang) or block["en"]).format(**values)

    items: list[dict[str, Any]] = []
    blocked = False
    table_c: list[str] = []
    table_c_single: list[str] = []
    for entry, index, product in products:
        mode = str(product.get("carriage_mode") or "packages").strip()
        if mode not in ("tank", "portable_tank", "bulk"):
            continue
        label = _product_label(entry, product, index)
        rows = database.get_un_entries(str(product.get("un_number") or "").strip())
        row = rows[0] if rows else {}
        codes = str(row.get("adn_carriage_permitted") or "").upper()

        if mode == "portable_tank":
            items.append({
                "position": label, "mode": mode, "permitted": True,
                "provision": "7.1.1.18",
                "message": text("portable_tank_as_packages", product=label),
            })
        elif mode == "bulk":
            permitted = "B" in codes
            blocked = blocked or not permitted
            items.append({
                "position": label, "mode": mode, "permitted": permitted,
                "provision": "3.2.1 column (8)" if permitted else "7.1.1.11",
                "message": text("bulk_permitted" if permitted
                                else "bulk_not_permitted", product=label),
            })
        else:
            permitted = "T" in codes
            blocked = blocked or not permitted
            item: dict[str, Any] = {
                "position": label, "mode": mode, "permitted": permitted,
                "provision": "7.2.1.21" if permitted else "7.1.1.21",
                "message": text("tank_permitted" if permitted
                                else "tank_not_permitted", product=label),
            }
            if permitted:
                answer = database.adn_tank_vessel_answer(
                    str(product.get("un_number") or "").strip())
                if answer and answer["vessel_type"]:
                    item["vessel_type"] = answer["vessel_type"]
                    item["vessel_message"] = text(
                        "tank_vessel_type", product=label,
                        type=answer["vessel_type"])
                elif answer and answer["vessel_types_seen"]:
                    item["vessel_types"] = answer["vessel_types_seen"]
                    item["vessel_message"] = text(
                        "tank_vessel_variants", product=label,
                        rows=answer["rows"],
                        types=", ".join(answer["vessel_types_seen"]))
                if answer and answer["readings_min"] < 2:
                    table_c_single.append(label)
                table_c.append(label)
            items.append(item)

    if not items:
        return {"status": "not_checked", "items": []}
    result: dict[str, Any] = {
        "status": "not_permitted" if blocked else "ok",
        "items": items,
        "source": rules["source"],
    }
    if table_c:
        result["conditions_note"] = text("tank_conditions_note")
    if table_c_single:
        result["single_reading_note"] = text(
            "single_reading_note", products=", ".join(sorted(table_c_single)))
    return result


def _tank_vessel_signals(products, rules, lang: str) -> dict[str, Any]:
    """ADN 7.2.5.0: the signals a tank vessel shows, from table C column (19).

    7.2.5.0.1 takes the count from the column; 7.2.5.0.2 ranks the options
    where several apply — two blue cones or lights before one. The count is
    used only where table C settles it: every variant row of the substance
    agrees and neither reading disputes the cell. Petrol settles at one cone
    across all six of its rows; a substance whose variants disagree is named
    instead of averaged.
    """
    highest: int | None = None
    setters: list[str] = []
    unsettled: list[str] = []
    for entry, index, product in products:
        label = _product_label(entry, product, index)
        answer = database.adn_tank_vessel_answer(
            str(product.get("un_number") or "").strip())
        if answer is None:
            continue
        if answer["cones"] is None:
            unsettled.append(label)
            continue
        count = int(answer["cones"])
        if highest is None or count > highest:
            highest, setters = count, [label]
        elif count == highest:
            setters.append(label)

    if highest is None:
        result: dict[str, Any] = {"status": "not_checked"}
        if unsettled:
            result["not_assessed"] = (
                rules["tank_not_settled"].get(lang)
                or rules["tank_not_settled"]["en"]).format(
                products=", ".join(sorted(unsettled)))
        return result

    described = rules["cones"][str(highest)]
    result = {
        "status": "ok",
        "provision": "7.2.5.0.1",
        "cones": highest,
        "message": described.get(lang) or described["en"],
        "set_by": sorted(setters),
        "source": "ADN 2025, 7.2.5 and table C column (19)",
    }
    if len(products) > 1:
        result["highest_wins"] = (
            rules["tank_highest"].get(lang)
            or rules["tank_highest"]["en"]).format(
            products=", ".join(sorted(setters)))
    if unsettled:
        result["not_assessed"] = (
            rules["tank_not_settled"].get(lang)
            or rules["tank_not_settled"]["en"]).format(
            products=", ".join(sorted(unsettled)))
        result["cones_not_settled"] = sorted(unsettled)
    return result



def _containers_reduction(count: int, product: dict[str, Any],
                          rules: dict[str, Any]) -> int | None:
    """7.1.5.0.2 for one substance, from the table read in v1.64.0.

    None where the statement was made but the gross mass the threshold compares
    against is missing — the caller then keeps the full count and says why,
    because a reduction granted without its mass would understate the signals.
    """
    from app.services.dg.autofill import total_quantity

    pg = str(product.get("packing_group") or "").strip().upper()
    hazard = _primary_class(product)
    if not hazard or not pg:
        # A caller that sends only the UN number still deserves the right
        # selector: the class and packing group are table A's to give, and
        # defaulting to "other" would reduce a chlorine load to no cones.
        rows = database.get_un_entries(
            str(product.get("un_number") or product.get("un") or "").strip())
        if rows:
            hazard = hazard or str(rows[0].get("class") or "").strip()
            pg = pg or str(rows[0].get("packing_group") or "").strip().upper()
    is_class2_or_pgi = hazard.startswith("2") or pg == "I"
    selector = "class_2_or_pg_i" if is_class2_or_pgi else "other"
    mass_kg: float | None = None
    gross = _num(product.get("gross_mass_per_package"))
    packages = _num(product.get("quantity_packages"))
    if gross is not None and packages is not None:
        mass_kg = gross * packages
    else:
        total, unit = total_quantity(product)
        if total is not None and unit == "kg":
            mass_kg = total

    for row in rules["containers_reduction"]["rows"]:
        if row["column_12"] != count:
            continue
        if row["selector"] not in (selector, "all"):
            continue
        if row.get("any_mass"):
            return row["cones"]
        if mass_kg is None:
            return None
        if "above_kg" in row and mass_kg > row["above_kg"]:
            return row["cones"]
        if "at_or_below_kg" in row and mass_kg <= row["at_or_below_kg"]:
            return row["cones"]
    return count


def check_adn_signals(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADN 7.1.5.0: the blue cones and blue lights the vessel must show.

    This is not a warning and that is the point of it. A vessel carrying
    dangerous goods on the inland waterways shows nought, one, two or three blue
    cones by day and the same number of blue lights by night, and which it is
    follows from column (12) of the ADN's table A. Until v1.61.0 EMCargo did
    not hold column (12) and so could not answer at all — not "unknown", not
    "check the text": the question had no place to be asked.

    Two provisions, and the second is why a consignment is more than a list:

    - **7.1.5.0.1** — the vessel shows what column (12) gives for the goods.
    - **7.1.5.0.4** — where several apply, the heaviest is the one to show:
      three before two before one. So the answer belongs to the *load*, and a
      single package of a two-cone substance sets the signals for everything
      else on board.

    **7.1.5.0.2** — the reduction for goods carried exclusively in containers —
    is applied since v1.94.0, and only where the consignor has *stated* the
    exclusive container carriage per substance: that statement is the
    provision's own condition, and inferring it from a packaging type would be
    guessing at the very fact it turns on. The thresholds were read in v1.64.0
    and have sat in the configuration since, recorded so they would not be read
    a second time when the input arrived. Where the statement is made but the
    gross mass the threshold compares against is missing, the full signals
    stand and the answer says why — over-signalling is the safe direction.
    """
    rules = get_compliance_rules()["adn_signals"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked"}

    in_cargo_tanks = _adn_cargo_tank_positions(products)
    if in_cargo_tanks:
        modes = {str(p.get("carriage_mode") or "packages").strip()
                 for _e, _i, p in products}
        if modes == {"tank"}:
            return _tank_vessel_signals(products, rules, lang)
        # A consignment that mixes cargo tanks with packages is not one vessel
        # under either chapter; the honest answer stays the chapter note.
        return {"status": "not_available_for_mode",
                "mode_note": _adn_mode_note(in_cargo_tanks, lang)}

    highest: int | None = None
    setters: list[str] = []
    unsettled: list[str] = []
    reduced: list[str] = []
    reduction_blocked: list[str] = []
    for entry, index, product in products:
        un_number = str(product.get("un_number") or product.get("un") or "").strip()
        signal = database.adn_blue_cones(un_number)
        if signal is None:
            continue
        label = _product_label(entry, product, index)
        if not signal["certain"]:
            unsettled.append(label)
            continue
        count = signal["cones"]
        if count is None:
            continue
        if product.get("containers_only") and count:
            lowered = _containers_reduction(count, product, rules)
            if lowered is None:
                reduction_blocked.append(label)
            elif lowered != count:
                count = lowered
                reduced.append(label)
        if highest is None or count > highest:
            highest, setters = count, [label]
        elif count == highest:
            setters.append(label)

    if highest is None:
        return {"status": "not_checked",
                "not_assessed": (rules["not_settled"].get(lang)
                                 or rules["not_settled"]["en"]).format(
                    products=", ".join(sorted(unsettled))) if unsettled else None}

    described = rules["cones"][str(highest)]
    result: dict[str, Any] = {
        "status": "ok",
        "provision": "7.1.5.0.1",
        "cones": highest,
        "message": described.get(lang) or described["en"],
        "set_by": sorted(setters),
        "containers_note": (rules["containers_note"].get(lang)
                            or rules["containers_note"]["en"]),
        "source": rules["source"],
    }
    # Only worth saying when the load actually disagrees with itself; on a
    # single-substance consignment "the heaviest applies" is noise.
    if len(products) > 1 and any(
            (database.adn_blue_cones(
                str(p.get("un_number") or p.get("un") or "").strip()) or {}
             ).get("cones") not in (None, highest) for _e, _i, p in products):
        result["highest_wins"] = (rules["highest_wins"].get(lang)
                                  or rules["highest_wins"]["en"]).format(
            products=", ".join(sorted(setters)))
    if unsettled:
        result["not_assessed"] = (rules["not_settled"].get(lang)
                                  or rules["not_settled"]["en"]).format(
            products=", ".join(sorted(unsettled)))
        result["cones_not_settled"] = sorted(unsettled)
    if reduced:
        result["containers_reduction_applied"] = (
            rules["reduction_applied"].get(lang)
            or rules["reduction_applied"]["en"]).format(
            products=", ".join(sorted(reduced)))
    if reduction_blocked:
        result["containers_reduction_incomplete"] = (
            rules["reduction_needs_mass"].get(lang)
            or rules["reduction_needs_mass"]["en"]).format(
            products=", ".join(sorted(reduction_blocked)))
    return result


def check_adr_tank_admission(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADR 3.2.1: may these goods travel in a tank at all?

    The wizard has always modelled packages, and every check in this file was
    written for them. A consignor filling in a tank load got the packages answer
    with nothing to say it was the wrong one — the most expensive shape of wrong
    this application can produce, because it looks like an answer.

    The admission rule is in the explanation of table A's own columns, and the
    two tank columns do **not** say the same thing:

    - **Column (12), ADR tanks** — where no code is given, carriage in ADR tanks
      is not permitted. The sentence carries no exception.
    - **Column (10), portable tanks** — where no code is given, carriage in
      portable tanks is not permitted *unless the competent authority allows it*
      under 6.7.1.3.

    Rounding those two to one answer would either invent a prohibition or hide
    one, so they stay apart and the finding says which it is. A blank column is
    not a missing value here — it is the regulation's way of saying no, and it is
    the reason class 1 explosives have every tank column empty.

    Carriage in packages is not judged here: this check answers a question that
    only arises once somebody says the goods travel in a tank.
    """
    rules = get_compliance_rules()["adr_tank_admission"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "items": []}

    def text(key: str, **values: Any) -> str:
        block = rules[key]
        return (block.get(lang) or block["en"]).format(**values)

    items: list[dict[str, Any]] = []
    blocked = False
    for entry, index, product in products:
        mode = str(product.get("carriage_mode") or "packages").strip()
        if mode not in ("tank", "portable_tank"):
            continue
        label = _product_label(entry, product, index)
        rows = database.get_un_entries(str(product.get("un_number") or "").strip())
        row = rows[0] if rows else {}
        if mode == "tank":
            code = str(row.get("tank_code") or "").strip()
            if code:
                items.append({
                    "position": label, "mode": mode, "permitted": True,
                    "tank_code": code,
                    "tank_vehicle": str(row.get("tank_vehicle") or "").strip(),
                    "tank_provisions": str(row.get("tank_provisions") or "").strip(),
                    "message": text("tank_permitted", product=label, code=code,
                                    vehicle=str(row.get("tank_vehicle") or "").strip()
                                    or text("no_vehicle")),
                })
            else:
                blocked = True
                items.append({
                    "position": label, "mode": mode, "permitted": False,
                    "provision": "3.2.1 column (12)",
                    "message": text("tank_not_permitted", product=label),
                })
        else:
            code = str(row.get("portable_tank_instructions") or "").strip()
            if code:
                items.append({
                    "position": label, "mode": mode, "permitted": True,
                    "portable_tank_instructions": code,
                    "portable_tank_provisions":
                        str(row.get("portable_tank_provisions") or "").strip(),
                    "message": text("portable_tank_permitted", product=label,
                                    code=code),
                })
            else:
                # Not a blocker: the competent authority may still permit it, and
                # refusing outright would invent a prohibition the book does not
                # make.
                items.append({
                    "position": label, "mode": mode, "permitted": False,
                    "subject_to_approval": True,
                    "provision": "3.2.1 column (10) / 6.7.1.3",
                    "message": text("portable_tank_not_permitted", product=label),
                })

    if not items:
        return {"status": "not_checked", "items": []}
    return {
        "status": "not_permitted" if blocked else "ok",
        "items": items,
        "source": rules["source"],
    }


#: The three codes each bulk column can carry, and nothing else counts as one:
#: a stray word in the cell must not read as a permission.
_BK_CODE = re.compile(r"\bBK[123]\b")
_VC_CODE = re.compile(r"\bVC[123]\b")
_AP_CODE = re.compile(r"\bAP\d+\b")


def check_adr_bulk_admission(
    entries: list[dict[str, Any]], language: str = "nl",
    profiles: list[str] | None = None,
) -> dict[str, Any]:
    """ADR 7.3.1.1: may these goods travel in bulk at all, and in what?

    The columns have been in the seed since v1.65.0 — the BK codes inside
    column (10) and the VC and AP codes of column (17) — and nothing computed
    with them: a bulk consignment got no admission answer where a tank load has
    had one since v1.66.0. The rule is the same shape as the tank rule, read in
    the Dutch edition (printed 1398-1403) and the UNECE English and French
    volumes II, which agree:

    - a **BK code in column (10)** admits the goods to bulk containers, under
      the conditions of 7.3.2 (equipment conditions this application cannot
      see, so they travel as conditions);
    - a **VC code in column (17)** admits them to sheeted or closed vehicles
      and containers, with any **AP provisions** of 7.3.3.2 alongside;
    - **neither** means bulk carriage is not permitted, full stop — with the
      one exception 7.3.1.1 itself makes for empty uncleaned packagings whose
      former contents are admitted.
    """
    rules = get_compliance_rules()["adr_bulk_admission"]
    lang = _lang(language)
    # RID 7.3 was read in the OTIF English and German editions (printed
    # 1092-1095 / 1176-1179): the ADR's provisions word for word, wagons in
    # place of vehicles, the same BK/VC/AP codes. Same answer — but a rail
    # document cites the RID and the VC meanings speak of wagons, the same
    # split the compatibility table and CW 28 already make.
    active = {str(p).upper() for p in (profiles or [])}
    regime = "RID" if active == {"RID"} else "ADR"
    vc_meanings = rules["vc_meanings_rail" if regime == "RID" else "vc_meanings"]

    def text(key: str, **values: Any) -> str:
        block = rules["rules"][key]
        return (block.get(lang) or block["en"]).format(**values)

    items: list[dict[str, Any]] = []
    blocked = False
    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        if str(product.get("carriage_mode") or "").strip() != "bulk":
            continue
        label = _product_label(entry, product, index)
        rows = database.get_un_entries(str(product.get("un_number") or "").strip())
        row = rows[0] if rows else {}
        bk = _BK_CODE.findall(str(row.get("portable_tank_instructions") or ""))
        vc = _VC_CODE.findall(str(row.get("carriage_bulk") or ""))
        ap = _AP_CODE.findall(str(row.get("carriage_bulk") or ""))

        if not bk and not vc:
            if product.get("empty_uncleaned"):
                # 7.3.1.1's own exception — but it turns on what the packagings
                # *contained*, and an empty-uncleaned line still names its
                # substance, so the finding stays on the substance's answer and
                # the exception is said next to it rather than granted.
                items.append({
                    "position": label, "permitted": False,
                    "provision": f"{regime} 7.3.1.1",
                    "message": text("not_permitted", product=label)
                               + " " + text("empty_uncleaned"),
                })
            else:
                items.append({
                    "position": label, "permitted": False,
                    "provision": f"{regime} 7.3.1.1",
                    "message": text("not_permitted", product=label),
                })
            blocked = True
            continue

        codes = bk + vc
        meanings = "; ".join(
            (rules["bk_meanings"] if code.startswith("BK")
             else vc_meanings)[code].get(lang)
            or (rules["bk_meanings"] if code.startswith("BK")
                else vc_meanings)[code]["en"]
            for code in codes)
        conditions = " + ".join(p for p, present in
                                (("7.3.2", bool(bk)), ("7.3.3", bool(vc)))
                                if present)
        message = text("permitted", product=label, codes=", ".join(codes),
                       meanings=meanings, conditions=conditions)
        if ap:
            message += " " + text("ap_conditions", codes=", ".join(ap))
        items.append({
            "position": label, "permitted": True,
            "bk_codes": bk, "vc_codes": vc, "ap_codes": ap,
            "provision": f"{regime} 7.3.1.1",
            "message": message,
        })

    if not items:
        return {"status": "not_checked", "items": []}
    return {
        "status": "not_permitted" if blocked else "ok",
        "items": items,
        "source": rules["source_rid" if regime == "RID" else "source"],
    }


def check_adr_tank_fit(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADR 4.3: may *this* tank carry these goods?

    Column (12) says which tank code the substance requires. It does not say
    whether the tank standing on the yard may carry it, and that is the
    question a consignor actually has — the vehicle has the code it has. ADR
    answers it twice and the two answers share nothing but their purpose:

    - **4.3.3.1.2**, gases, is a hierarchy of *codes*. A substance under C*BN
      may also travel in C#BN, C#CN, C#DN, C#BH, C#CH and C#DH, where the
      figure standing for # is at least the figure standing for *. So the
      answer is read off the offered code's own letters and pressure.
    - **4.3.4.1.2**, classes 3 to 9, is the rationalized approach and is not a
      hierarchy of codes at all. Each tank code names the group of substances
      it may carry — class, classification code and packing group — and
      inherits the groups of the codes below it. The required code is not
      compared with the offered one; the substance is looked up in the offered
      code's group.

    Rounding those two to one rule is the mistake that would make this check
    wrong, so they stay apart.

    Three outcomes, and the third is not a failure of the check but an answer:
    **fits**, **does not fit**, and **cannot be assessed** — the last where the
    seed's readings did not settle a cell the answer would rest on, or where
    the offered code is not one the table names.

    The regulation's own note is why a fit is never the whole answer: the
    hierarchy takes no account of the special provisions of 4.3.5 and 6.8.4,
    which are column (13). Where the substance carries any, they are named with
    the answer, because one of them can require equipment the hierarchy knows
    nothing about, and another can switch the hierarchy off altogether.
    """
    rules = get_compliance_rules()["adr_tank_fit"]
    lang = _lang(language)

    def text(key: str, **values: Any) -> str:
        block = rules[key]
        return (block.get(lang) or block["en"]).format(**values)

    items: list[dict[str, Any]] = []
    blocked = False
    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        if str(product.get("carriage_mode") or "").strip() != "tank":
            continue
        typed = str(product.get("tank_code") or "").strip()
        offered = typed.upper()
        if not offered:
            continue
        label = _product_label(entry, product, index)
        rows = database.get_un_entries(str(product.get("un_number") or "").strip())
        row = rows[0] if rows else {}
        required = str(row.get("tank_code") or "").strip().upper()
        provisions = str(row.get("tank_provisions") or "").strip()
        item: dict[str, Any] = {
            # What the consignor typed is what the answer names: a code read
            # back in a case nobody used reads like a different code.
            "position": label, "offered": typed, "required": required,
            "tank_provisions": provisions,
        }
        if not required:
            # Column (12) empty means the goods may not travel in an ADR tank
            # at all; the admission check says so, and this one does not repeat
            # it in different words.
            continue
        if _same_tank_code(offered, required):
            item["fit"] = "fits"
            item["message"] = text("same_code", product=label, code=required)
        elif str(row.get("class") or "").strip() == "2":
            item.update(_gas_fit(offered, required, label, text, typed))
        else:
            item.update(_rationalised_fit(offered, row, label, text, typed))
        if provisions:
            item["provisions_note"] = text("provisions", codes=provisions)
        blocked = blocked or item.get("fit") == "does_not_fit"
        items.append(item)

    if not items:
        return {"status": "not_checked", "items": []}
    return {
        "status": "not_permitted" if blocked else "ok",
        "items": items,
        "source": rules["source"],
    }


def _same_tank_code(one: str, other: str) -> bool:
    return one.replace(",", ".") == other.replace(",", ".")


#: A gas tank code as column (12) and the tank's own plate print it: C10BN,
#: PxBH(M). The figure is often the letter x — "the minimum test pressure
#: according to 4.3.3.2.5" — and the code can carry a suffix the hierarchy
#: itself says nothing about, so both are read rather than refused.
_GAS_CODE = re.compile(r"^([CPR])(x|\d+(?:[.,]\d+)?)([BCD])([NH])(\(.*\))?$",
                       re.IGNORECASE)


def _gas_fit(offered: str, required: str, label: str, text: Any,
             typed: str) -> dict[str, Any]:
    """4.3.3.1.2: the offered code against the required one, for gases."""
    here = _GAS_CODE.match(offered.replace(",", "."))
    there = _GAS_CODE.match(required.replace(",", "."))
    if not here or not there:
        return {"fit": "cannot_be_assessed",
                "message": text("unknown_code", product=label, code=typed)}
    row = database.adr_gas_hierarchy(f"{there.group(1)}*{there.group(3)}{there.group(4)}")
    if row is None or (row.get("disputed") or {}):
        return {"fit": "cannot_be_assessed",
                "message": text("not_settled", product=label, code=required)}
    wanted = f"{here.group(1)}#{here.group(3)}{here.group(4)}"
    if wanted not in (row.get("also_permitted") or []):
        return {"fit": "does_not_fit",
                "message": text("gas_no", product=label, offered=typed,
                                required=required)}
    # "The figure represented by # shall be equal to or greater than the figure
    # represented by *" — the one line of arithmetic in the whole hierarchy.
    # "The figure represented by # shall be equal to or greater than the figure
    # represented by *" — the one line of arithmetic in the whole hierarchy,
    # and it can only be done when both codes print a figure. Column (12)
    # prints x for most gases: the minimum test pressure then comes from
    # 4.3.3.2.5, which is a table of gases this application does not hold.
    if there.group(2).lower() == "x" or here.group(2).lower() == "x":
        return {"fit": "fits_under_condition",
                "message": text("gas_pressure_from_table", product=label,
                                offered=typed, required=required)}
    if float(here.group(2)) < float(there.group(2)):
        return {"fit": "does_not_fit",
                "message": text("gas_pressure", product=label, offered=typed,
                                required=required)}
    if there.group(5) and there.group(5) != here.group(5):
        return {"fit": "fits_under_condition",
                "message": text("gas_suffix", product=label, offered=typed,
                                required=required, suffix=there.group(5))}
    return {"fit": "fits",
            "message": text("gas_yes", product=label, offered=typed,
                            required=required)}


def _rationalised_fit(offered: str, row: dict[str, Any], label: str,
                      text: Any, typed: str) -> dict[str, Any]:
    """4.3.4.1.2: is the substance in the group the offered tank may carry?"""
    permissions = database.adr_tank_permissions(offered)
    if permissions is None:
        return {"fit": "cannot_be_assessed",
                "message": text("unknown_code", product=label, code=typed)}
    klass = str(row.get("class") or "").strip()
    code = str(row.get("classification_code") or "").strip()
    group = str(row.get("packing_group") or "").strip()
    if not klass or not code:
        return {"fit": "cannot_be_assessed",
                "message": text("no_classification", product=label)}
    for permission in permissions["permitted"]:
        if (permission["class"] != klass
                or permission["classification_code"] != code):
            continue
        if permission.get("packing_group") and permission["packing_group"] != group:
            continue
        answer = {"fit": "fits",
                  "message": text("group_yes", product=label, offered=typed,
                                  klass=klass, code=code,
                                  group=group or text("no_packing_group"))}
        if permission.get("condition"):
            answer["condition"] = permission["condition"]
            answer["fit"] = "fits_under_condition"
            answer["message"] = text("group_condition", product=label,
                                     offered=typed,
                                     condition=permission["condition"])
        return answer
    if permissions["unsettled"]:
        # The substance is not in what was settled, and part of the chain was
        # not settled at all. Saying "does not fit" here would be a claim the
        # books have not made.
        return {"fit": "cannot_be_assessed",
                "unsettled": permissions["unsettled"],
                "message": text("chain_not_settled", product=label,
                                offered=typed,
                                codes=", ".join(permissions["unsettled"]))}
    return {"fit": "does_not_fit",
            "message": text("group_no", product=label, offered=typed,
                            klass=klass, code=code,
                            group=group or text("no_packing_group"))}


def check_adr_filling_degree(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADR 4.3.2.2: how full the tank may be.

    Read in the English volume II and the printed Dutch edition, which agree.
    4.3.2.2.1 gives four maxima for a tank carrying a substance that is liquid
    at normal temperatures, and they differ only in their numerator:

    ======  ====================================================  ==========
    case    the tank, and the substance                           numerator
    ======  ====================================================  ==========
    (a)     breather device or safety valves; flammable or         100
            environmentally hazardous, no toxic or corrosive
            subsidiary hazard
    (b)     breather device or safety valves; toxic or corrosive    98
    (c)     hermetically closed, no safety device; flammable,       97
            environmentally hazardous, slightly toxic or
            slightly corrosive
    (d)     hermetically closed, no safety device; highly toxic,    95
            toxic, highly corrosive or corrosive
    ======  ====================================================  ==========

    all over ``1 + α (50 − tF)``, with ``α = (d15 − d50) / (35 d50)`` from
    4.3.2.2.2 — the mean coefficient of cubical expansion between 15 °C and
    50 °C — and tF the mean temperature of the liquid during filling.

    **What decides which of the four is the interesting part.** The tank's
    venting is the *fourth letter of the tank code*: N is a tank with a
    breather device or safety valves, H is hermetically closed without a
    safety device. Since v1.82.0 the consignor types that code, so this half is
    read rather than guessed. The other half — toxic or corrosive against
    merely flammable — is derived from the class, the subsidiary risks and the
    packing group, and *is* a derivation: it is shown with the answer so it can
    be overruled, never applied in silence.

    Table A carries neither density, so the arithmetic runs only once the
    consignor has supplied d15, d50 and tF. Without them the formula itself is
    the answer, and it goes on the document as a condition — which is the
    honest end of a calculation whose inputs nobody has.
    """
    rules = get_compliance_rules()["adr_filling_degree"]
    lang = _lang(language)

    def text(key: str, **values: Any) -> str:
        block = rules[key]
        return (block.get(lang) or block["en"]).format(**values)

    items: list[dict[str, Any]] = []
    for entry, index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        if str(product.get("carriage_mode") or "").strip() != "tank":
            continue
        label = _product_label(entry, product, index)
        rows = database.get_un_entries(str(product.get("un_number") or "").strip())
        row = rows[0] if rows else {}
        item: dict[str, Any] = {"position": label}

        # Classes 1, 5.2 and 7 are excepted by the provision's own footnote.
        klass = str(row.get("class") or product.get("class") or "").strip()
        if klass.split(".")[0] in ("1", "7") or klass == "5.2":
            item.update({"status": "own_rule", "provision": "4.3.4.1.3",
                         "message": text("own_rule", product=label)})
            items.append(item)
            continue

        temperature = _num(product.get("filling_temperature"))
        if temperature is not None and temperature > 50:
            item.update({"status": "above_fifty", "provision": "4.3.2.2.3",
                         "message": text("above_fifty", product=label)})
            items.append(item)
            continue

        offered = str(product.get("tank_code") or "").strip().upper()
        case = _filling_case(offered, row, product)
        if case is None:
            item.update({"status": "no_tank_code", "provision": "4.3.2.2.1",
                         "message": text("no_tank_code", product=label)})
            items.append(item)
            continue

        letter, spec = case
        item.update({"case": letter, "provision": spec["provision"],
                     "numerator": spec["numerator"],
                     "formula": text("formula", numerator=spec["numerator"]),
                     "derivation": text(
                         "derivation", provision=spec["provision"], code=offered,
                         venting=text("vented" if spec["vented"] else "hermetic"),
                         hazard=text("toxic_or_corrosive" if spec["toxic_or_corrosive"]
                                     else "not_toxic_or_corrosive"))})

        alpha = _expansion(product)
        if alpha is None or temperature is None:
            item.update({"status": "needs_input",
                         "message": text("needs_input", product=label,
                                         provision=spec["provision"])})
            items.append(item)
            continue

        degree = spec["numerator"] / (1 + alpha * (50 - temperature))
        item.update({
            "status": "computed",
            "alpha": round(alpha, 6),
            "filling_temperature": temperature,
            "degree": round(degree, 1),
            "message": text("computed", product=label, degree=f"{degree:.1f}",
                            provision=spec["provision"], alpha=f"{alpha:.5f}",
                            temperature=_fmt_number(temperature)),
        })
        items.append(item)

    if not items:
        return {"status": "not_checked", "items": []}
    return {"status": "ok", "items": items, "source": rules["source"]}


def _fmt_number(value: float) -> str:
    return f"{value:g}"


def _expansion(product: dict[str, Any]) -> float | None:
    """α, from the two densities the provision names or straight from input.

    4.3.2.2.2 defines it as (d15 − d50) / (35 d50). A user who has the figure
    already may give it; a user who has the densities gives those. Neither is
    in table A, which is the whole reason this is an input at all.
    """
    given = _num(product.get("expansion_coefficient"))
    if given is not None and given > 0:
        return given
    d15 = _num(product.get("density_15"))
    d50 = _num(product.get("density_50"))
    if d15 is None or d50 is None or d50 <= 0 or d15 <= d50:
        return None
    return (d15 - d50) / (35 * d50)


#: The letters of a tank code that say how it vents. The fourth letter of an
#: ADR tank code is N where the tank has a breather device or safety valves and
#: H where it is hermetically closed; 4.3.2.2.1 turns on exactly that.
_VENTING = re.compile(r"^[LS](?:[A-Z]{2}|\d+(?:[.,]\d+)?[A-Z])([NH])$", re.IGNORECASE)


def _filling_case(offered: str, row: dict[str, Any],
                  product: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """Which of 4.3.2.2.1 (a) to (d) applies, or None where the tank is unknown."""
    match = _VENTING.match(offered.replace(",", "."))
    if not match:
        return None
    vented = match.group(1).upper() == "N"
    hazards = {str(row.get("class") or product.get("class") or "").strip()}
    hazards |= {part.strip() for part in
                str(row.get("subsidiary_risks")
                    or product.get("subsidiary_risks") or "").split(",")}
    toxic_or_corrosive = bool({"6.1", "8"} & hazards)
    rules = get_compliance_rules()["adr_filling_degree"]["cases"]
    for letter, spec in rules.items():
        if spec["vented"] == vented and spec["toxic_or_corrosive"] == toxic_or_corrosive:
            return letter, spec
    return None  # pragma: no cover - the four cases cover both booleans


def check_adr_security(
    entries: list[dict[str, Any]], language: str = "nl",
) -> dict[str, Any]:
    """ADR 1.10.3: high consequence dangerous goods, and the security plan.

    Chapter 1.10 was named in the 1.1.3.6 exemption text and nowhere else — the
    one remaining heading in `docs/dg-coverage.md` with nothing behind it.

    Table 1.10.3.1.2 is the rare regulatory table that is *easier* than it looks,
    and only once it has been read. For carriage in packages its column holds two
    values and no others: **0**, meaning any quantity at all, and footnote
    **b)**, "whatever the quantity, the provisions of 1.10.3 do not apply". There
    is no threshold to compare against and no arithmetic to get wrong. A full
    load of packaged petrol of packing group II is not high consequence dangerous
    goods and does not become so at a larger quantity; a single kilogram of a
    packing group I toxic is.

    So this is a membership test, and it is worth having precisely because the
    intuition it corrects runs the other way. Flammable liquids, corrosives and
    packing group I oxidisers all look like the dangerous end of the load and are
    all footnote b) in packages. What is caught instead is class 1, the toxic
    gases, the desensitised explosives, packing group I toxics and category A
    infectious substances.

    Since v1.68.0 the **tank and bulk columns are answered too**, and they turn
    the packages reading on its head: seven rows that are footnote b) in packages
    — never high consequence, whatever the quantity — carry 3,000 litres in a
    tank. Flammable liquids of packing groups I and II are among them, so a road
    tanker of petrol is high consequence dangerous goods and this check used to
    say it was not. Footnotes c) and d) are applied with the figures: a tank or
    bulk value counts only where table A admits that form of carriage, which is
    what the columns carried since v1.65.0 settle.

    A threshold needs a quantity. Where none is entered the row is reported as
    unanswered rather than read as "under the figure" — the difference between
    not knowing and knowing it is safe.

    Class 7 is still not answered: 1.10.3.1.3 measures it in activity against
    3,000 A2, and EMCargo is not told an activity.
    """
    rules = get_compliance_rules()["adr_security"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "items": []}

    items: list[dict[str, Any]] = []
    for entry, index, product in products:
        hazard = str(product.get("class") or "").strip()
        code = str(product.get("classification_code") or "").strip().upper()
        division = code if re.match(r"^\d\.\d", code) else hazard
        un_number = str(product.get("un_number") or product.get("un") or "").strip()
        group = str(product.get("packing_group") or "").strip().upper()
        # The classification code carries the division for class 1 and the
        # hazard letters for everything else — "1.2G" against "TFC" — which is
        # exactly the two things the table sorts on.
        letters = re.sub(r"^\d(\.\d)?", "", code)

        for rule in rules["rows"]:
            kind = rule["match"]
            hit = False
            if kind == "class_1":
                hit = division.split(" ")[0][:3] in rule["divisions"]
            elif kind == "class_1_group_c":
                hit = (division[:3] in rule["divisions"]
                       and letters[:1] in rule["compatibility_groups"])
            elif kind == "un_numbers":
                hit = un_number.zfill(4) in rule["un_numbers"]
            elif kind == "classification_letters":
                hit = (hazard == rule["hazard_class"]
                       and letters in rule["letters"]
                       and un_number.zfill(4) not in rule.get("exclude_un_numbers", []))
            elif kind == "packing_group":
                hit = hazard == rule["hazard_class"] and group in rule["packing_groups"]
            if not hit:
                continue
            # Which column of table 1.10.3.1.2 applies, and whether it applies
            # at all. Footnotes c) and d) make a tank or bulk figure relevant
            # only where table A admits that form of carriage, so the columns
            # v1.65.0 carried are what settles it — not the figure alone.
            mode = str(product.get("carriage_mode") or "packages").strip()
            row = database.get_un_entries(un_number)
            row = row[0] if row else {}
            if mode in ("tank", "portable_tank"):
                threshold = rule.get("tank_litres")
                by_division = rule.get("tank_litres_by_division") or {}
                if division[:3] in by_division:
                    threshold = by_division[division[:3]]
                admitted = bool(str(row.get("tank_code") or "").strip()
                                or str(row.get("portable_tank_instructions") or "").strip())
                unit, message_key = "litres", "tank_threshold_message"
            elif mode == "bulk":
                threshold = rule.get("bulk_kg")
                admitted = bool(str(row.get("carriage_bulk") or "").strip())
                unit, message_key = "kg", "bulk_threshold_message"
            else:
                threshold = rule.get("packages_kg")
                admitted, unit, message_key = True, "kg", None
            # Footnote a) — not relevant for this form of carriage — or a form
            # table A does not admit: either way the row says nothing about
            # this consignment.
            if threshold is None or not admitted:
                break
            quantity = _num(product.get("adr_total_quantity"))
            if threshold > 0 and (quantity is None or quantity <= threshold):
                # Below the figure, or no figure entered. Not high consequence
                # on this row — and where the quantity is missing that is a
                # statement about the input, so it is recorded rather than
                # silently treated as "under".
                if quantity is None:
                    items.append({
                        "position": _product_label(entry, product, index),
                        "un_number": un_number,
                        "reason": (rule.get(lang) or rule["en"]).format(
                            division=division[:3]),
                        "threshold_kg": threshold,
                        "carriage_mode": mode,
                        "not_answered": True,
                    })
                break
            item = {
                "position": _product_label(entry, product, index),
                "un_number": un_number,
                # The division and not the whole classification code:
                # table 1.10.3.1.2 sorts on 1.2, and "division 1.2G" would
                # quote the table as saying something it does not.
                "reason": (rule.get(lang) or rule["en"]).format(
                    division=division[:3]),
                "threshold_kg": threshold,
                "carriage_mode": mode,
            }
            if message_key and threshold > 0:
                block = rules[message_key]
                item["threshold_note"] = (block.get(lang) or block["en"]).format(
                    threshold=threshold)
            items.append(item)
            break

    if str(rules["class_7"]["provision"]) and any(
            str(p.get("class") or "").strip() == "7" for _e, _i, p in products):
        items.append({"position": None, "un_number": None,
                      "reason": rules["class_7"].get(lang) or rules["class_7"]["en"],
                      "threshold_kg": None, "not_answered": True})

    answered = [item for item in items if not item.get("not_answered")]
    if answered:
        plan = rules["plan"]
        message = (plan.get(lang) or plan["en"]).format(
            products=", ".join(sorted({item["position"] for item in answered})))
    else:
        none = rules["none"]
        message = none.get(lang) or none["en"]

    return {
        "status": "high_consequence" if answered else "ok",
        "scope": "packages",
        "items": items,
        "message": message,
        "provision": rules["plan"]["provision"] if answered else "1.10.3.1.2",
        "source": rules["source"],
    }


def check_adr_placarding(
    entries: list[dict[str, Any]], language: str = "nl",
    points_status: str | None = None,
) -> dict[str, Any]:
    """ADR 5.3: what goes on the outside of the vehicle.

    `docs/dg-coverage.md` has ranked this as the last of the seven gaps for
    several releases with a note that it is "the most common real-world
    failure", and the application named chapter 5.3 in its 1.1.3.6 output
    without deriving a word of it. The half about equipment closed in v1.53.0
    the same way this one does: by reading what the provision chooses on, and
    finding that EMCargo already holds it.

    **The point of this check is that it says no.** 5.3.1.5 gives a vehicle
    carrying packages exactly two reasons to placard — 5.3.1.5.1 for class 1
    other than division 1.4 compatibility group S, and 5.3.1.5.2 for class 7 in
    packagings or IBCs other than excepted packages. A load of packaged petrol,
    nitric acid or a toxic liquid needs no placard at all; the orange plates of
    5.3.2.1.1 are the whole of it. Telling a driver to placard anyway is not a
    harmless excess. It teaches that the placard is decoration, and the next time
    it is class 1 on board that lesson is already learnt.

    The same reading runs through 5.3.6.1, which opens "When a placard is
    required to be displayed in accordance with the provisions of section
    5.3.1". The environmentally hazardous mark on the *vehicle* therefore hangs
    on the placard and not on the substance: packaged environmentally hazardous
    class 9 puts no mark on the truck. The mark on the *package* is 5.2.1.8.3
    and a different question, which is said out loud so this cannot be read as
    relieving it.

    Since v1.67.0 the plates branch on the mode of carriage. For packages
    5.3.2.1.6 *permits* the hazard and UN numbers on the front and rear plates,
    and only where a single substance is on board; for a tank 5.3.2.1.2
    *requires* them, on both sides of every tank and every compartment, for each
    substance it holds. Permitted and required are not the same finding.

    What is still not answered: the placards themselves for tanks and bulk —
    5.3.1 gives them their own subsections — and 5.3.2.1.4 for containers under
    exclusive use. Nor is the elevated temperature mark of 5.3.3 derived: it
    turns on a carriage temperature of 100 °C liquid or 240 °C solid, and
    EMCargo is not told the temperature.
    """
    rules = get_compliance_rules()["adr_placarding"]
    lang = _lang(language)
    products = [(entry, index, product)
                for entry, index, product in _iter_products(entries)
                if not product.get("transport_forbidden")]
    if not products:
        return {"status": "not_checked", "placards": [], "marks": []}
    named = {id(product): _product_label(entry, product, index)
             for entry, index, product in products}
    goods = [product for _entry, _index, product in products]

    exempt = points_status == "exempt"
    placards: list[dict[str, Any]] = []
    for hazard, rule in rules["placard_classes"].items():
        matched = [p for p in goods
                   if str(p.get("class") or "").split(".")[0] == hazard
                   and str(p.get("classification_code") or "").upper()
                   not in {c.upper() for c in rule.get("except_classification_codes", [])}]
        if matched:
            placards.append({
                "class": hazard,
                "provision": rule["provision"],
                "message": rule.get(lang) or rule["en"],
                "products": sorted({named[id(p)] for p in matched}),
            })

    # 5.3.1.4.1 against 5.3.1.5: for packages a placard goes on the vehicle only
    # for class 1 and class 7, which is why the packages answer is mostly that
    # none is needed. A tank does not work that way — every label model of the
    # load goes on both long sides and the rear. Answering a tank with the
    # packages rule turns a requirement into an absence.
    in_tanks_or_bulk = any(
        str(p.get("carriage_mode") or "").strip()
        in ("tank", "portable_tank", "bulk") for p in goods)
    if in_tanks_or_bulk:
        tank = rules["tank_placards"]
        labels = sorted({
            part.strip()
            for p in goods
            for part in str(p.get("labels") or "").replace("+", ",").split(",")
            if part.strip()})
        without = sorted({named[id(p)] for p in goods
                          if not str(p.get("labels") or "").strip()})
        if labels:
            placards.append({
                "class": None,
                "provision": tank["provision_vehicle"],
                "message": (tank["vehicle"].get(lang) or tank["vehicle"]["en"]).format(
                    labels=", ".join(labels)),
                "products": sorted({named[id(p)] for p in goods}),
                "label_models": labels,
                "required": True,
            })
            placards.append({
                "class": None,
                "provision": tank["provision_container"],
                "message": tank["container"].get(lang) or tank["container"]["en"],
                "products": [],
            })
        if without:
            placards.append({
                "class": None,
                "provision": tank["provision_vehicle"],
                "message": (tank["no_labels"].get(lang) or tank["no_labels"]["en"]).format(
                    products=", ".join(without)),
                "products": without,
                "required": None,
            })
    elif not placards:
        # The finding this check exists for. An empty list is not an answer —
        # it reads as "not computed" — so the absence is stated with the
        # provision that makes it an absence.
        none = rules["no_placards"]
        placards.append({"class": None, "provision": "5.3.1.5",
                         "message": none.get(lang) or none["en"],
                         "products": []})

    marks: list[dict[str, Any]] = []
    plates = rules["orange_plates"]
    if exempt:
        marks.append({"provision": rules["exempt"]["provision"],
                      "message": rules["exempt"].get(lang) or rules["exempt"]["en"],
                      "kind": "exempt"})
    else:
        marks.append({"provision": plates["provision"],
                      "message": plates.get(lang) or plates["en"],
                      "kind": "orange_plates"})
        # 5.3.2.1.6 — one substance and nothing else on board, and the plates
        # may carry the two numbers. Both come out of table A, so the check can
        # print them rather than describe them.
        numbers = {(str(p.get("hazard_number") or "").strip(),
                    str(p.get("un_number") or p.get("un") or "").strip())
                   for p in goods}
        numbers = {n for n in numbers if n[0] and n[1]}
        # 5.3.2.1.2 against 5.3.2.1.6: for a tank the numbered plates are
        # *required*, on both sides of every tank and compartment, for each
        # substance in it. For packages 5.3.2.1.6 merely permits them, and only
        # where a single substance is on board. Permitted and required are not
        # the same finding, and a tank load used to be shown the permitted one.
        in_tanks = any(
            str(p.get("carriage_mode") or "").strip() in ("tank", "portable_tank")
            for p in goods)
        if in_tanks:
            without = sorted(
                str(p.get("un_number") or p.get("un") or "").strip()
                for p in goods
                if not str(p.get("hazard_number") or "").strip())
            if numbers:
                tank = rules["tank_plates"]
                marks.append({
                    "provision": tank["provision"],
                    "message": (tank.get(lang) or tank["en"]).format(
                        numbers=", ".join(
                            f"{hazard} / UN {un}" for hazard, un in sorted(numbers))),
                    "kind": "tank_plates",
                    "required": True,
                })
            if without:
                missing_text = rules["tank_plates_no_number"]
                marks.append({
                    "provision": "5.3.2.1.2",
                    "message": (missing_text.get(lang) or missing_text["en"]).format(
                        products=", ".join(f"UN {un}" for un in without if un)),
                    "kind": "tank_plates",
                    "required": None,
                })
        elif len(numbers) == 1:
            hazard_number, un_number = next(iter(numbers))
            numbered = rules["numbered_plates"]
            marks.append({
                "provision": numbered["provision"],
                "message": (numbered.get(lang) or numbered["en"]).format(
                    numbers=f"{hazard_number} / UN {un_number}"),
                "kind": "numbered_plates",
                "hazard_number": hazard_number,
                "un_number": un_number,
            })

    # A placard finding carries a class where 5.3.1.5 chose it by class, and
    # none where 5.3.1.4.1 chose it because the load is in a tank — that one
    # says so in `required` instead. Counting only the classed ones told a tank
    # load it needed no placards at all, and told 5.3.6.1 the same, so the
    # environmentally hazardous mark came out wrong with it.
    required_placards = [p for p in placards
                         if p.get("class") or p.get("required") is True]
    green = [p for p in goods if p.get("environmentally_hazardous")]
    if green:
        mark = rules["environmental_mark"]
        applies = bool(required_placards) and not exempt
        marks.append({
            "provision": mark["provision"],
            "message": (mark.get(lang) or mark["en"]).format(
                products=", ".join(sorted({named[id(p)] for p in green})),
                applies=_YES_NO[lang][applies]),
            "kind": "environmental_mark",
            "applies": applies,
        })

    return {
        "status": "exempt" if exempt else "ok",
        # What the answer was computed for. A tank load is not a packages load,
        # and a card that says "computed for carriage in packages" over a tank
        # answer is worse than no note at all.
        "scope": "tanks_or_bulk" if _in_tanks(goods) else "packages",
        "placards": placards,
        "placards_required": bool(required_placards),
        "marks": marks,
        "source": rules["source"],
    }


def _hold_of(product: dict[str, Any]) -> str:
    """Which hold the boatmaster put this in, normalised for comparison.

    Only for comparing one position with another: what the plan prints is what
    was typed. "1" and " 1 " are one hold; "dek" and "deck" are one deck.
    """
    value = str(product.get("hold") or "").strip().lower()
    return "deck" if value in {"dek", "deck", "aan dek", "an deck", "auf deck",
                               "pont", "sur le pont"} else value


def _in_tanks(goods: list[dict[str, Any]]) -> bool:
    return any(str(product.get("carriage_mode") or "").strip()
               in ("tank", "portable_tank", "bulk") for product in goods)


#: "yes" and "no" in the four languages the interface speaks, for the one
#: message that has to say which of the two applies inside a sentence.
_YES_NO = {
    "nl": {True: "het geval", False: "niet het geval"},
    "en": {True: "the case", False: "not the case"},
    "de": {True: "der Fall", False: "nicht der Fall"},
    "fr": {True: "le cas", False: "pas le cas"},
}


def check_adr_equipment(
    entries: list[dict[str, Any]], language: str = "nl",
    points_status: str | None = None,
) -> dict[str, Any]:
    """ADR 8.1.4 and 8.1.5: what has to be aboard the transport unit.

    Equipment was the one heading in ``docs/dg-coverage.md`` that named itself
    "the most common real-world failure" and was absent from every mode. It is
    absent for a reason worth stating: EMCargo cannot see a vehicle, so it can
    never establish that a wheel chock is in the cab.

    What it *can* do is derive the list, and that turns out to be most of the
    value. 8.1.5.1 says so itself: the equipment is chosen **according to the
    hazard label numbers of the goods loaded**, and it points at the transport
    document to identify them — which is precisely the document this application
    produces. So the label numbers are the input, and the output is the list a
    driver checks against, with the provision beside each line.

    Two things stay outside it. The number of crew members is not known, so the
    per-crew items say "per crew member" rather than a count. And the fire
    extinguishers of 8.1.4.1 hang on the maximum permissible mass of the
    transport unit, which is a property of the vehicle; the three rows of the
    table are given instead of one answer. Where the consignment stays inside the
    1.1.3.6 exemption, 8.1.4.2 replaces the table with a single 2 kg extinguisher
    — which is one of the few places where the exemption makes a visible
    difference to what has to be in the cab.
    """
    rules = get_compliance_rules()["adr_equipment"]
    lang = _lang(language)

    labels: set[str] = set()
    has_non_gas = False
    for _entry, _index, product in _iter_products(entries):
        if product.get("transport_forbidden"):
            continue
        labels |= _label_numbers(product)
        if not _is_gas(product):
            has_non_gas = True

    if not labels:
        return {"items": [], "status": "not_checked", "labels": [],
                "basis": "ADR 8.1.4 / 8.1.5", "note": pick(_EQUIPMENT_NOTE, lang)}

    items: list[dict[str, str]] = []

    exempt = points_status == "exempt_possible"
    if exempt:
        items.append({"key": "fire_extinguisher", "rule": "ADR 8.1.4.2",
                      "text": pick(_EXTINGUISHER_EXEMPT_MESSAGE, lang)})
    else:
        table = rules["fire_extinguishers"]["rows"]
        rows = "; ".join(
            (f"≤ {row['max_mass_tonnes']} t: {row['total_kg']} kg"
             if row["max_mass_tonnes"] else f"> 7,5 t: {row['total_kg']} kg")
            for row in table
        )
        items.append({
            "key": "fire_extinguisher", "rule": "ADR 8.1.4.1",
            "text": pick(_EXTINGUISHER_MESSAGE, lang).format(
                count=table[0]["count"], rows=rows),
        })

    general = rules["general"]
    for key in general["per_unit"]:
        items.append({"key": key, "rule": "ADR 8.1.5.2",
                      "text": pick(_EQUIPMENT_LABELS[key], lang)})
    for key, excluded in general["per_unit_unless_label"].items():
        # The footnote is an exemption, not a requirement: eye-rinsing liquid is
        # *not* prescribed for the label numbers listed, so a load that carries
        # nothing else does not need it.
        if labels - set(excluded):
            items.append({"key": key, "rule": "ADR 8.1.5.2",
                          "text": pick(_EQUIPMENT_LABELS[key], lang)})
    for key in general["per_crew_member"]:
        items.append({"key": key, "rule": "ADR 8.1.5.2",
                      "text": pick(_EQUIPMENT_LABELS[key], lang)})

    per_label = rules["per_label"]
    if labels & set(per_label["escape_mask"]["labels"]):
        items.append({"key": "escape_mask", "rule": "ADR 8.1.5.3",
                      "text": pick(_EQUIPMENT_LABELS["escape_mask"], lang)})
    spill = per_label["spill_kit"]
    if labels & set(spill["labels"]) and (has_non_gas or not spill["solids_and_liquids_only"]):
        for key in spill["items"]:
            items.append({"key": key, "rule": "ADR 8.1.5.3",
                          "text": pick(_EQUIPMENT_LABELS[key], lang)})

    return {
        "items": items,
        "labels": sorted(labels),
        "status": "derived",
        "basis": "ADR 8.1.4 / 8.1.5",
        "note": pick(_EQUIPMENT_NOTE, lang),
    }


def check_iata_segregation(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, str]]:
    """IATA Table 9.3.A: segregation between packages, lithium rule included."""
    rules = get_compliance_rules()["iata_segregation"]
    lang = _lang(language)
    warnings: list[dict[str, str]] = []

    products: list[tuple[str, list[str], str]] = []
    for entry, index, product in _iter_products(entries):
        label = _product_label(entry, product, index)
        tokens = _hazard_tokens(product)
        un = str(product.get("un_number") or "").strip()
        products.append((label, tokens, un))

    seen: set[tuple[str, str]] = set()
    for i, (label_a, tokens_a, un_a) in enumerate(products):
        for label_b, tokens_b, un_b in products[i + 1:]:
            for key_a, key_b in rules["incompatible_pairs"]:
                hit = (
                    any(_matches_iata_key(t, key_a) for t in tokens_a)
                    and any(_matches_iata_key(t, key_b) for t in tokens_b)
                ) or (
                    any(_matches_iata_key(t, key_b) for t in tokens_a)
                    and any(_matches_iata_key(t, key_a) for t in tokens_b)
                )
                if hit:
                    pair_id = tuple(sorted((label_a, label_b)))
                    if pair_id in seen:
                        continue
                    seen.add(pair_id)
                    warnings.append({
                        "rule": f"IATA Table 9.3.A ({key_a} × {key_b})",
                        "severity": "error",
                        "message": pick(rules["note"], lang),
                        "products": f"{label_a}  ×  {label_b}",
                    })

            lithium_a = un_a in rules["lithium_battery_un_numbers"]
            lithium_b = un_b in rules["lithium_battery_un_numbers"]
            if lithium_a or lithium_b:
                other_tokens = tokens_b if lithium_a else tokens_a
                if any(
                    _matches_iata_key(t, key)
                    for t in other_tokens
                    for key in rules["lithium_incompatible_with"]
                ):
                    pair_id = tuple(sorted((label_a, label_b, "lithium")))
                    if pair_id not in seen:
                        seen.add(pair_id)
                        warnings.append({
                            "rule": "IATA 9.3.2 (lithiumbatterijen)",
                            "severity": "error",
                            "message": pick(rules["lithium_note"], lang),
                            "products": f"{label_a}  ×  {label_b}",
                        })
    return warnings


def _imdg_row_key(token: str, class_order: list[str]) -> str | None:
    """Map a hazard token onto a row of the IMDG segregation table."""
    token = token.strip().upper()
    if not token:
        return None
    if token.startswith("1"):
        # 1.4S falls outside the table for most combinations, but the Code does
        # know 1.4 as a row of its own; the compatibility group is ignored here.
        division = re.match(r"^1(\.\d)?", token)
        if not division:
            return None
        value = division.group(0)
        if value in {"1.1", "1.2", "1.5", "1"}:
            return "1.1-1.2-1.5"
        if value in {"1.3", "1.6"}:
            return "1.3-1.6"
        if value == "1.4":
            return "1.4"
        return None
    for key in class_order:
        if key == token:
            return key
    # '2' without a division or '6' without a division cannot be classified
    # reliably; those are skipped rather than guessed at.
    return None


def check_imdg_segregation(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IMDG 7.2.4: separation between packages based on the class table."""
    rules = get_compliance_rules().get("imdg_segregation")
    if not rules:
        return []
    lang = _lang(language)
    class_order: list[str] = rules["class_order"]
    table: dict[str, list[str]] = rules["table"]
    codes: dict[str, dict[str, str]] = rules["codes"]

    products: list[tuple[str, list[str]]] = []
    for entry, index, product in _iter_products(entries):
        keys: list[str] = []
        primary = _imdg_row_key(_primary_class(product), class_order)
        if primary:
            keys.append(primary)
        # IMDG 7.2.3.3: a subsidiary risk of class 1 is treated as division 1.3
        # for segregation purposes.
        for token in re.split(r"[,;/\s()+]+", str(product.get("subsidiary_risks") or "")):
            token = token.strip().upper()
            if not token:
                continue
            key = "1.3-1.6" if token.startswith("1") else _imdg_row_key(token, class_order)
            if key and key not in keys:
                keys.append(key)
        if keys:
            products.append((_product_label(entry, product, index), keys))

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i, (label_a, keys_a) in enumerate(products):
        for label_b, keys_b in products[i + 1:]:
            worst = ""
            worst_pair = ("", "")
            for key_a in keys_a:
                for key_b in keys_b:
                    value = table[key_a][class_order.index(key_b)]
                    # A digit always beats a "*": that one refers on to 7.2.7
                    # and states no distance itself. `not worst` as the test
                    # allowed int("*") as soon as the first cell was a "*" and a
                    # later one a digit — a class 1 package with a subsidiary
                    # risk next to another class 1 package did exactly that.
                    if value in {"1", "2", "3", "4"} and (
                        not worst.isdigit() or int(value) > int(worst)
                    ):
                        worst = value
                        worst_pair = (key_a, key_b)
                    elif value == "*" and not worst:
                        worst = "*"
                        worst_pair = (key_a, key_b)
            if not worst:
                continue
            pair_id = tuple(sorted((label_a, label_b)))
            if pair_id in seen:
                continue
            seen.add(pair_id)
            warnings.append({
                "rule": f"IMDG 7.2.4 ({worst_pair[0]} × {worst_pair[1]})",
                "severity": "error" if worst in {"3", "4"} else "warning",
                "code": worst,
                "message": pick(codes[worst], lang),
                "products": f"{label_a}  ×  {label_b}",
                "source": "table",
                "pair": "|".join(pair_id),
            })
    return warnings


def check_imdg_class1_compatibility(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.7.1.4: permitted mixed stowage of compatibility groups."""
    rules = get_compliance_rules().get("imdg_class1_compatibility")
    if not rules:
        return []
    lang = _lang(language)
    order: list[str] = rules["group_order"]
    matrix: dict[str, list[str]] = rules["matrix"]
    special: dict[str, dict[str, str]] = rules.get("special_notes", {})

    products: list[tuple[str, str]] = []
    for entry, index, product in _iter_products(entries):
        group = _compat_group(product)
        if group and group in order:
            products.append((_product_label(entry, product, index), group))

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i, (label_a, group_a) in enumerate(products):
        for label_b, group_b in products[i + 1:]:
            pair_id = tuple(sorted((label_a, label_b)))
            if pair_id in seen:
                continue
            permitted = matrix[group_a][order.index(group_b)] == "X"
            note = special.get(group_a) or special.get(group_b)
            if not permitted:
                seen.add(pair_id)
                warnings.append({
                    "rule": f"IMDG 7.2.7.1.4 ({group_a} × {group_b})",
                    "severity": "error",
                    "message": pick(rules["note"], lang),
                    "products": f"{label_a}  ×  {label_b}",
                })
            elif note and group_a != group_b:
                seen.add(pair_id)
                warnings.append({
                    "rule": f"IMDG 7.2.7.1.4 ({group_a} × {group_b})",
                    "severity": "warning",
                    "message": pick(note, lang),
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# Segregation groups that may not travel together (IMDG 7.2.5 read with column
# 16b): the classic dangerous combinations.
_SGG_CONFLICTS: list[tuple[str, str, dict[str, str]]] = [
    ("SGG1", "SGG18", {
        "nl": "zuren en alkaliën",
        "en": "acids and alkalis",
        "de": "Säuren und Laugen", "fr": 'acides et alcalis'}),
    ("SGG1", "SGG6", {
        "nl": "zuren en cyaniden (ontwikkeling van blauwzuur)",
        "en": "acids and cyanides (release of hydrogen cyanide)",
        "de": "Säuren und Cyanide (Freisetzung von Blausäure)", "fr": "acides et cyanures (dégagement d'acide cyanhydrique)"}),
    ("SGG1", "SGG5", {
        "nl": "zuren en chlorieten (ontwikkeling van chloordioxide)",
        "en": "acids and chlorites (release of chlorine dioxide)",
        "de": "Säuren und Chlorite (Freisetzung von Chlordioxid)", "fr": 'acides et chlorites (dégagement de dioxyde de chlore)'}),
    ("SGG1", "SGG8", {
        "nl": "zuren en hypochlorieten (ontwikkeling van chloorgas)",
        "en": "acids and hypochlorites (release of chlorine gas)",
        "de": "Säuren und Hypochlorite (Freisetzung von Chlorgas)", "fr": 'acides et hypochlorites (dégagement de chlore gazeux)'}),
    ("SGG1", "SGG12", {
        "nl": "zuren en nitrieten (ontwikkeling van nitreuze dampen)",
        "en": "acids and nitrites (release of nitrous fumes)",
        "de": "Säuren und Nitrite (Freisetzung nitroser Gase)", "fr": 'acides et nitrites (dégagement de vapeurs nitreuses)'}),
    ("SGG1", "SGG17", {
        "nl": "zuren en aziden (vorming van explosief waterstofazide)",
        "en": "acids and azides (formation of explosive hydrazoic acid)",
        "de": "Säuren und Azide (Bildung von explosiver Stickstoffwasserstoffsäure)", "fr": "acides et azotures (formation d'acide hydrazoïque explosible)"}),
    ("SGG1", "SGG14", {
        "nl": "zuren en permanganaten",
        "en": "acids and permanganates",
        "de": "Säuren und Permanganate", "fr": 'acides et permanganates'}),
    ("SGG1", "SGG15", {
        "nl": "zuren en metaalpoeders (ontwikkeling van waterstof)",
        "en": "acids and powdered metals (release of hydrogen)",
        "de": "Säuren und Metallpulver (Freisetzung von Wasserstoff)", "fr": "acides et métaux en poudre (dégagement d'hydrogène)"}),
    ("SGG16", "SGG1", {
        "nl": "peroxiden en zuren",
        "en": "peroxides and acids",
        "de": "Peroxide und Säuren", "fr": 'peroxydes et acides'}),
]


def check_imdg_segregation_groups(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.5/3.1.4.4: incompatible segregation groups within the consignment."""
    lang = _lang(language)
    products: list[tuple[str, set[str]]] = []
    for entry, index, product in _iter_products(entries):
        groups = set(segregation_groups_for(product.get("un_number", ""),
                                            str(product.get("packing_group") or "")))
        # Manually entered groups count too.
        for token in re.split(r"[,;/\s]+", str(product.get("segregation_group") or "")):
            if token.strip().upper().startswith("SGG"):
                groups.add(token.strip().upper())
        if groups:
            products.append((_product_label(entry, product, index), groups))

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for i, (label_a, groups_a) in enumerate(products):
        for label_b, groups_b in products[i + 1:]:
            for code_a, code_b, names in _SGG_CONFLICTS:
                hit = (code_a in groups_a and code_b in groups_b) or (
                    code_b in groups_a and code_a in groups_b
                )
                if not hit:
                    continue
                key = (*sorted((label_a, label_b)), f"{code_a}-{code_b}")
                if key in seen:
                    continue
                seen.add(key)
                warnings.append({
                    "rule": f"IMDG 7.2.5 ({code_a} × {code_b})",
                    "severity": "warning",
                    "message": pick(
                        {
                            "nl": "Scheidingsgroepen {groups}: kolom 16b van de Dangerous "
                                  "Goods List schrijft hier scheiding voor. Controleer de "
                                  "vermelding per stof.",
                            "en": "Segregation groups {groups}: column 16b of the Dangerous "
                                  "Goods List prescribes segregation here. Check the entry "
                                  "per substance.",
                            "de": "Trenngruppen {groups}: Spalte 16b der Dangerous Goods List "
                                  "schreibt hier eine Trennung vor. Prüfen Sie den Eintrag je "
                                  "Stoff.", "fr": 'Groupes de séparation {groups} : la colonne 16b de la liste des marchandises dangereuses prescrit ici une séparation. Vérifiez la rubrique de chaque matière.'},
                        lang,
                    ).format(groups=pick(names, lang)),
                    "products": f"{label_a}  ×  {label_b}",
                })
    return warnings


# How strict a segregation provision is, in plain words.
_ACTION_TEXT = {
    # The German IMDG edition distinguishes "entfernt von" (away from) from
    # "getrennt von" (separated from); that difference is the whole point here.
    "away_from": {
        "nl": "uit de buurt van",
        "en": "away from",
        "de": "entfernt von", "fr": "à l'écart de"},
    "separated_from": {
        "nl": "gescheiden van",
        "en": "separated from",
        "de": "getrennt von", "fr": 'séparé de'},
    "separated_by_compartment": {
        "nl": "gescheiden door een volledig compartiment of ruim van",
        "en": "separated by a complete compartment or hold from",
        "de": "durch eine vollständige Abteilung oder einen vollständigen Laderaum getrennt von", "fr": 'séparé par un compartiment ou une cale complète de'},
    "separated_longitudinally": {
        "nl": "in de lengterichting gescheiden door een tussenliggend compartiment of ruim van",
        "en": "separated longitudinally by an intervening complete compartment or hold from",
        "de": "in Längsrichtung durch eine dazwischenliegende vollständige Abteilung oder "
              "einen vollständigen Laderaum getrennt von", "fr": 'séparé longitudinalement par un compartiment ou une cale complète intercalaire de'},
}

# The same four segregation codes as in the table of 7.2.4, so that an SG code
# and a table value can be compared with each other (7.2.3.1).
_ACTION_CODE = {
    "away_from": "1",
    "separated_from": "2",
    "separated_by_compartment": "3",
    "separated_longitudinally": "4",
}


def _classes_of(product: dict[str, Any]) -> set[str]:
    """Primary class, division and subsidiary risks of a package."""
    found: set[str] = set()
    for field in ("class", "subsidiary_risks", "labels"):
        for token in re.split(r"[+,;/\s]+", str(product.get(field) or "")):
            token = token.strip().strip("()")
            if token and re.fullmatch(r"\d(?:\.\d[A-Z]?)?", token):
                found.add(token)
    return found


def _matches_class(target: str, classes: set[str]) -> bool:
    """"class 5.1" touches 5.1; "class 1" touches every division of class 1."""
    if target in classes:
        return True
    if "." not in target:
        return any(c.split(".")[0] == target for c in classes)
    return False


def _wording(code: str, rules: dict[str, Any]) -> str:
    """The description of an SG code, preferably the one belonging to the code.

    Chapter 7.2.8 gives the official wording; the sentence that came from the UN
    card is a paraphrase and remains only as a fallback.
    """
    return imdg_code_text(code) or str(rules.get(code, {}).get("text", ""))


def check_imdg_segregation_provisions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG column 16b: the segregation provisions (SG) of the substance itself.

    The segregation table of 7.2.4 works on class; column 16b lays provisions per
    substance on top of that. Those codes now come from the Dangerous Goods List
    itself, as it stands in 42-24, and no longer only from the 41-22 UN cards —
    which covered nowhere near every substance. What is checked here is whether
    another consignment in the same shipment is the target of such a provision.
    """
    lang = _lang(language)
    rules = segregation_provisions()

    parties: list[dict[str, Any]] = []
    for entry, index, product in _iter_products(entries):
        un = str(product.get("un_number") or "").strip()
        packing_group = str(product.get("packing_group") or "").strip()
        groups = set(segregation_groups_for(un, packing_group))
        for token in re.split(r"[,;/\s]+", str(product.get("segregation_group") or "")):
            if token.strip().upper().startswith("SGG"):
                groups.add(token.strip().upper())
        parties.append({
            "label": _product_label(entry, product, index),
            "un": "".join(ch for ch in un if ch.isdigit()).zfill(4) if un else "",
            "codes": imdg_segregation_codes_for(un, packing_group),
            "classes": _classes_of(product),
            "groups": groups,
        })

    config = get_compliance_rules()
    named = config.get("imdg_segregation_named_targets", {})
    cargo = config.get("imdg_segregation_cargo_requirements", {})

    warnings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    # Provisions that name ordinary cargo — foodstuffs, oils, odour-absorbing
    # cargo. The app does not know what else goes on board, so these are
    # reported as soon as the substance travels, just like the ADR CV28 note.
    raised_cargo: set[tuple[str, str]] = set()
    for source in parties:
        for code in source["codes"]:
            requirement = cargo.get(code)
            if not isinstance(requirement, dict):
                continue
            # SG26 applies only next to certain classes; the rest always.
            needed = requirement.get("classes")
            if needed and not any(
                any(_matches_class(t, other["classes"]) for t in needed)
                for other in parties if other is not source
            ):
                continue
            key = (source["label"], code)
            if key in raised_cargo:
                continue
            raised_cargo.add(key)
            warnings.append({
                "rule": f"IMDG 16b ({code})",
                "severity": "warning",
                "message": f"{pick(requirement, lang)} {_wording(code, rules)}".strip(),
                "products": source["label"],
            })

    for source in parties:
        for code in source["codes"]:
            rule = rules.get(code)
            if not rule:
                continue

            # Provisions that name a substance explicitly: which UN numbers
            # those are is in dg_compliance.json — checkable and adjustable.
            target = named.get(code)
            if isinstance(target, dict):
                for other in parties:
                    if other is source:
                        continue
                    by_un = other["un"] in (target.get("un") or [])
                    by_group = any(g in other["groups"] for g in target.get("groups") or [])
                    by_class = any(
                        _matches_class(t, other["classes"]) for t in target.get("classes") or []
                    )
                    if target.get("require_both"):
                        hit = by_class and by_group
                    else:
                        hit = by_un or by_group or by_class
                    if not hit:
                        continue
                    key = (source["label"], other["label"], code)
                    if key in seen:
                        continue
                    seen.add(key)
                    caveat = ""
                    if target.get("broader"):
                        caveat = pick(
                            {
                                "nl": " Gematcht op de scheidingsgroep, die ruimer is dan de "
                                      "tekst; controleer.",
                                "en": " Matched on the segregation group, which is broader "
                                      "than the wording; verify.",
                                "de": " Über die Trenngruppe zugeordnet, die weiter reicht als "
                                      "der Wortlaut; bitte prüfen.", "fr": ' Correspondance établie sur le groupe de séparation, plus large que le libellé ; à vérifier.'},
                            lang,
                        )
                    warnings.append({
                        "rule": f"IMDG 16b ({code})",
                        "severity": "warning",
                        "message": f"{_wording(code, rules)}{caveat}",
                        "products": f"{source['label']}  \u00d7  {other['label']}",
                    })
                continue

            if rule.get("informational") or not rule.get("targets"):
                continue
            targets = rule["targets"]
            for other in parties:
                if other is source:
                    continue
                # An exception in the provision ("except 1.4S") excludes that
                # consignment; otherwise the app would warn about something the
                # Code specifically permits.
                if any(c in other["classes"] for c in rule.get("excepted_classes") or []):
                    continue
                hit_class = next(
                    (t for t in targets.get("classes", []) if _matches_class(t, other["classes"])),
                    None,
                )
                hit_group = next(
                    (g for g in targets.get("groups", []) if g in other["groups"]), None
                )
                if not hit_class and not hit_group:
                    continue
                key = (source["label"], other["label"], code)
                if key in seen:
                    continue
                seen.add(key)
                action = pick(
                    _ACTION_TEXT.get(str(rule.get("action")), {}),
                    lang,
                    pick(_ACTION_TEXT["separated_from"], lang),
                )
                # "SGG1" says nothing; "SGG1 (acids)" does.
                if hit_class:
                    what = pick(
                        {"nl": "klasse {c}", "en": "class {c}", "de": "Klasse {c}", "fr": 'classe {c}'}, lang
                    ).format(c=hit_class)
                else:
                    what = f"{hit_group} ({segregation_group_label(hit_group, lang)})"
                warnings.append({
                    "rule": f"IMDG 16b ({code})",
                    "severity": "warning",
                    "message": pick(
                        {
                            "nl": "Stuw {action} {what}. {wording}",
                            "en": "Stow {action} {what}. {wording}",
                            "de": "Stauen Sie {action} {what}. {wording}", "fr": 'Arrimer {action} {what}. {wording}'},
                        lang,
                    ).format(action=action, what=what, wording=_wording(code, rules)),
                    "products": f"{source['label']}  \u00d7  {other['label']}",
                    "source": "column_16b",
                    "code": _ACTION_CODE.get(str(rule.get("action")), ""),
                    "pair": "|".join(sorted((source["label"], other["label"]))),
                })
    return warnings


def apply_column_16b_precedence(
    findings: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.3.1: where provisions conflict, column 16b always prevails.

    The class segregation table of 7.2.4 and the substance-specific SG codes of
    column 16b can say different things about the same pair. The Code leaves no
    doubt about that: "In case of conflicting provisions, the provisions of
    column 16b of the Dangerous Goods List, always take precedence."

    Nothing is removed. Both findings stay, with the provision that prevails
    according to the Code alongside them, so it is visible why one sets the other
    aside. Taking away a justified warning is worse than showing one too many;
    that is the same trade-off as with the exemptions of 7.2.6.3.
    """
    lang = _lang(language)
    by_pair: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for finding in findings:
        pair = finding.get("pair")
        origin = finding.get("source")
        if pair and origin in {"table", "column_16b"}:
            by_pair.setdefault(pair, {}).setdefault(origin, []).append(finding)

    for buckets in by_pair.values():
        table = buckets.get("table") or []
        column = [f for f in buckets.get("column_16b") or [] if f.get("code")]
        if not table or not column:
            continue
        # Several SG codes can apply to the same pair, in both directions. The
        # strictest determines what has to happen; every code at that level gets
        # named, because they all carry equal weight.
        strictest_code = max(int(f["code"]) for f in column)
        governing = [f for f in column if int(f["code"]) == strictest_code]
        rules = [f["rule"] for f in governing]
        for finding in table:
            if str(finding.get("code")) == str(strictest_code):
                continue  # No conflict: both provisions come out the same.
            finding["superseded_by"] = rules
            finding["severity"] = "info"
            finding["message"] += pick(
                {
                    "nl": " Let op 7.2.3.1: {rules} in kolom 16b gaat hierop voor "
                          "(scheidingscode {code} in plaats van {was}).",
                    "en": " Note 7.2.3.1: {rules} in column 16b takes precedence over this "
                          "(segregation code {code} instead of {was}).",
                    "de": " Beachten Sie 7.2.3.1: {rules} in Spalte 16b geht dem vor "
                          "(Trennkennzahl {code} statt {was}).", "fr": ' Note 7.2.3.1 : {rules} à la colonne 16b prime sur ce résultat (code de séparation {code} au lieu de {was}).'},
                lang,
            ).format(rules=", ".join(rules), code=strictest_code, was=finding["code"])
        for finding in governing:
            finding["takes_precedence_over"] = [f["rule"] for f in table]
            finding["message"] += pick(
                {
                    "nl": " Deze bepaling uit kolom 16b gaat volgens 7.2.3.1 voor op de "
                          "klassescheidingstabel.",
                    "en": " Per 7.2.3.1 this column 16b provision takes precedence over the "
                          "class segregation table.",
                    "de": " Diese Bestimmung aus Spalte 16b geht nach 7.2.3.1 der "
                          "Klassentrenntabelle vor.", "fr": ' En vertu du 7.2.3.1, cette disposition de la colonne 16b prime sur le tableau de séparation par classe.'},
                lang,
            )
            if strictest_code >= 3:
                finding["severity"] = "error"
    return findings


def check_imdg_segregation_exemptions(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.6.3: substances in the same table need not be segregated.

    This is the exemption that SG72 in column 16b refers to. The app removes no
    warning with it — suppressing a justified message is worse than showing a
    redundant one — but reports the exemption alongside, table and all. That way
    the finding and its legal basis are in view together and the choice stays
    with the consignor.
    """
    config = get_compliance_rules().get("imdg_segregation_exemptions")
    if not config:
        return []
    lang = _lang(language)
    tables = config["tables"]

    parties: list[tuple[str, str]] = []
    for entry, index, product in _iter_products(entries):
        un = "".join(ch for ch in str(product.get("un_number") or "") if ch.isdigit())
        if un:
            parties.append((_product_label(entry, product, index), un.zfill(4)))

    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for i, (label_a, un_a) in enumerate(parties):
        for label_b, un_b in parties[i + 1:]:
            for name, members in tables.items():
                if un_a not in members or un_b not in members:
                    continue
                key = (*sorted((label_a, label_b)), name)
                if key in seen:
                    continue
                seen.add(key)
                extra = ""
                if name == "7.2.6.3.4":
                    extra = pick(
                        {
                            "nl": " Let op 7.2.6.4: de gevaarlijke reacties van 7.2.6.1.1 "
                                  "t/m 7.2.6.1.4 blijven gelden.",
                            "en": " Note 7.2.6.4: the dangerous reactions of 7.2.6.1.1 to "
                                  "7.2.6.1.4 continue to apply.",
                            "de": " Beachten Sie 7.2.6.4: die gefährlichen Reaktionen nach "
                                  "7.2.6.1.1 bis 7.2.6.1.4 gelten weiterhin.", "fr": ' Note 7.2.6.4 : les réactions dangereuses des 7.2.6.1.1 à 7.2.6.1.4 restent applicables.'},
                        lang,
                    )
                findings.append({
                    "rule": f"IMDG {name}",
                    "severity": "info",
                    "message": pick(
                        {
                            "nl": "Beide stoffen staan in tabel {name}: hiertussen hoeft geen "
                                  "scheiding te worden toegepast.{extra}",
                            "en": "Both substances appear in table {name}: no segregation "
                                  "needs to be applied between them.{extra}",
                            "de": "Beide Stoffe stehen in Tabelle {name}: zwischen ihnen ist "
                                  "keine Trennung anzuwenden.{extra}", "fr": "Les deux matières figurent au tableau {name} : aucune séparation n'est à appliquer entre elles.{extra}"},
                        lang,
                    ).format(name=name, extra=extra),
                    "products": f"{label_a}  \u00d7  {label_b}",
                })
    return findings


def append_class8_pair_exception(
    entries: list[dict[str, Any]], findings: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """IMDG 7.2.6.5 next to the pair concerned, not only as general text.

    Two substances of class 8, packing group II or III, which have to stay
    segregated according to column 16b, may nevertheless travel together in
    packages of up to 30 L/30 kg under 7.2.6.5 — provided they do not react
    dangerously with each other and the document carries the declaration of
    5.4.1.5.11.3. That is the same trade-off as with 7.2.6.3: the exemption is
    reported, the warning stays, and the choice stays with the consignor.
    """
    lang = _lang(language)
    eligible: set[str] = set()
    for entry, index, product in _iter_products(entries):
        primary = _primary_class(product)
        pg = str(product.get("packing_group") or "").strip().upper()
        if primary.startswith("8") and pg in {"II", "III"}:
            eligible.add(_product_label(entry, product, index))

    if len(eligible) < 2:
        return findings

    seen: set[tuple[str, str]] = set()
    extra: list[dict[str, Any]] = []
    for finding in findings:
        if finding.get("severity") not in {"warning", "error"}:
            continue
        parts = [p.strip() for p in str(finding.get("products") or "").split("\u00d7")]
        if len(parts) != 2 or not all(p in eligible for p in parts):
            continue
        pair = tuple(sorted(parts))
        if pair in seen:
            continue
        seen.add(pair)
        extra.append({
            "rule": "IMDG 7.2.6.5",
            "severity": "info",
            "message": pick(
                {
                    "nl": "Mogelijke uitzondering: stoffen van klasse 8, verpakkingsgroep "
                          "II of III, in colli tot 30 L of 30 kg hoeven onderling niet "
                          "gescheiden te worden, mits ze niet gevaarlijk met elkaar "
                          "reageren en het vervoersdocument de verklaring van "
                          "5.4.1.5.11.3 draagt. De scheidingsmelding hierboven blijft "
                          "staan; de beoordeling is aan de afzender.",
                    "en": "Possible exception: class 8 substances of packing group II or "
                          "III in packages up to 30 L or 30 kg need not be segregated "
                          "from one another, provided they do not react dangerously with "
                          "each other and the transport document carries the "
                          "5.4.1.5.11.3 statement. The segregation finding above stands; "
                          "the judgement rests with the shipper.",
                    "de": "Mögliche Ausnahme: Stoffe der Klasse 8, Verpackungsgruppe II "
                          "oder III, in Versandstücken bis 30 L oder 30 kg müssen "
                          "untereinander nicht getrennt werden, sofern sie nicht "
                          "gefährlich miteinander reagieren und das Beförderungspapier "
                          "die Erklärung nach 5.4.1.5.11.3 trägt. Der Trennhinweis oben "
                          "bleibt bestehen; die Beurteilung liegt beim Versender.", "fr": "Exception possible : les matières de la classe 8 des groupes d'emballage II ou III en colis d'au plus 30 L ou 30 kg n'ont pas à être séparées entre elles, à condition qu'elles ne réagissent pas dangereusement entre elles et que le document de transport porte la mention du 5.4.1.5.11.3. La constatation de séparation ci-dessus reste valable ; l'appréciation appartient au chargeur."},
                lang,
            ),
            "products": "  \u00d7  ".join(pair),
        })
    return findings + extra


def check_imdg_amendment_42_24(
    entries: list[dict[str, Any]], language: str = "nl"
) -> list[dict[str, Any]]:
    """What Amendment 42-24 changes about the declared substances.

    The substance-specific IMDG layer comes from the 41-22 UN cards, while the
    basic classification comes from ADR 2025. Where 42-24 differs from that, it
    has to appear with the consignment and not only in the documentation.

    The classification is not silently overwritten. If 42-24 changes the class,
    the subsidiary risk or the packing group, then the segregation the app
    computes is based on the old classification, and that is said in so many
    words. Applying an amended class under one's breath would change the outcome
    without anybody being able to see why.
    """
    lang = _lang(language)
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for entry, index, product in _iter_products(entries):
        un = str(product.get("un_number") or "").strip()
        if not un:
            continue
        label = _product_label(entry, product, index)
        pg = str(product.get("packing_group") or "").strip().upper()
        overlay = amendment_42_24.overlay_for(un, pg)

        for line in amendment_42_24.changes_for(un, pg, lang):
            key = (label, line)
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                "rule": f"IMDG {amendment_42_24.amendment()}",
                "severity": "info",
                "message": line,
                "products": label,
            })

        reclassified = {"class", "subsidiary_risks_add", "packing_group"} & set(overlay)
        if reclassified:
            findings.append({
                "rule": f"IMDG {amendment_42_24.amendment()} — " + pick(
                    {
                        "nl": "classificatie",
                        "en": "classification",
                        "de": "Klassifizierung", "fr": 'classification'},
                    lang,
                ),
                "severity": "warning",
                "message": pick(
                    {
                        "nl": "De classificatie van deze stof is in 42-24 gewijzigd. De app "
                              "rekent de scheiding door op de classificatie van ADR Tabel A "
                              "en past die niet vanzelf aan; controleer de uitkomst tegen de "
                              "vermelding in de Dangerous Goods List van 42-24.",
                        "en": "The classification of this substance changed in 42-24. The app "
                              "computes segregation on the ADR Table A classification and does "
                              "not adjust it automatically; check the outcome against the "
                              "42-24 Dangerous Goods List entry.",
                        "de": "Die Klassifizierung dieses Stoffes hat sich in 42-24 geändert. "
                              "Die App berechnet die Trennung anhand der Klassifizierung nach "
                              "ADR Tabelle A und passt sie nicht selbsttätig an; prüfen Sie "
                              "das Ergebnis gegen den Eintrag in der Dangerous Goods List von "
                              "42-24.", "fr": "La classification de cette matière a changé dans l'amendement 42-24. L'application calcule la séparation sur la classification du tableau A de l'ADR et ne l'ajuste pas automatiquement ; vérifiez le résultat au regard de la rubrique de la liste des marchandises dangereuses 42-24."},
                    lang,
                ),
                "products": label,
            })

        requirement = amendment_42_24.document_requirement(un, lang)
        if requirement:
            findings.append({
                "rule": f"IMDG {requirement['section']}",
                "severity": "warning",
                "message": requirement["text"],
                "products": label,
            })
    return findings


# Divisions that are (almost always) forbidden in aviation; the ICAO TI lists
# chlorine and related 2.3 gases as forbidden on passenger *and* cargo aircraft,
# with only an A1/A2 approval as a way out.
_AIR_FORBIDDEN_DIVISIONS = {"2.3"}


def check_air_forbidden(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """ICAO TI / IATA DGR: divisions that may not travel by air.

    The class column of Table A only says "2" for gases; the division comes from
    the labels. So both the hazard tokens of the product and the division
    resolved via parse_hazards are tested here — otherwise chlorine (UN 1017,
    class "2", label 2.3) stays invisible until /dg/prepare has put the division
    in the class field.
    """
    lang = _lang(language)
    warnings: list[dict[str, Any]] = []
    for entry, index, product in _iter_products(entries):
        tokens = {t.lower() for t in _hazard_tokens(product)}
        division = str(parse_hazards(product).get("division") or "").strip().lower()
        if division:
            tokens.add(division)
        if not tokens & {d.lower() for d in _AIR_FORBIDDEN_DIVISIONS}:
            continue
        warnings.append({
            "rule": "ICAO TI / IATA DGR — divisie 2.3",
            "severity": "error",
            "message": pick(
                {
                    "nl": "Divisie 2.3 (giftige gassen) is in de luchtvaart verboden op "
                          "passagiers- én vrachttoestellen, op enkele uitzonderingen na. "
                          "Vervoer is alleen mogelijk met een ontheffing of voorafgaande "
                          "goedkeuring van de betrokken autoriteiten (A1/A2).",
                    "en": "Division 2.3 (toxic gases) is forbidden in air transport on "
                          "passenger and cargo aircraft alike, with few exceptions. "
                          "Carriage is only possible under an exemption or prior approval "
                          "of the authorities concerned (A1/A2).",
                    "de": "Unterklasse 2.3 (giftige Gase) ist in der Luftbeförderung auf "
                          "Passagier- wie Frachtflugzeugen bis auf wenige Ausnahmen "
                          "verboten. Eine Beförderung ist nur mit einer Ausnahme oder "
                          "vorheriger Genehmigung der betroffenen Behörden möglich "
                          "(A1/A2).", "fr": "La division 2.3 (gaz toxiques) est interdite au transport aérien, tant sur aéronef de passagers que sur aéronef cargo, à de rares exceptions près. Le transport n'est possible que sous dérogation ou accord préalable des autorités concernées (A1/A2)."},
                lang,
            ),
            "products": _product_label(entry, product, index),
        })
    return warnings


def check_q_value(entries: list[dict[str, Any]], language: str = "nl") -> list[dict[str, Any]]:
    """IATA 5.0.2.11: Q value per position for 'all packed in one'.

    Computed with Decimal and without intermediate rounding: two components of
    0.50001 each are 1.00002 together and therefore Q = 1.1 — exceeded. Rounding
    per component first turned that into 1.0, a false negative.

    A component with missing, zero or negative values does not disappear
    silently: the position gets status "incomplete" with the reason alongside.
    """
    rules = get_compliance_rules()["q_value"]
    lang = _lang(language)
    results: list[dict[str, Any]] = []

    for entry in entries:
        products = entry.get("products") or []
        # A position only takes part once somebody has filled in an M (maximum
        # per package according to the packing instruction). The n is filled
        # automatically by /dg/prepare from the net per package; going on that
        # alone put every air consignment on "incomplete", including those where
        # 'all packed in one' does not come into play at all.
        if not any(
            str(product.get("q_max_net_quantity") or "").strip()
            for product in products
        ):
            # Two or more substances in one position without any Q input: then
            # 'all packed in one' *may* apply and nothing has been computed.
            # Skipping that position silently let the consignment count as
            # "checked" as soon as one other position had been filled in — a
            # check that did not run then looked like a check that passed.
            if len([p for p in products if str(p.get("un_number") or "").strip()]) >= 2:
                results.append({
                    "position": entry.get("vehicle") or entry.get("line_id"),
                    "components": [],
                    "status": "not_checked",
                    "q_value": None,
                    "exceeded": None,
                    "note": pick(
                        {
                            "nl": "Geen Q berekend voor deze positie: er staan meer "
                                  "stoffen op één positie, maar n en M zijn niet "
                                  "ingevuld. Speelt 'all packed in one', vul ze dan in.",
                            "en": "No Q computed for this position: it holds more than "
                                  "one substance but n and M were not entered. If all "
                                  "packed in one applies, enter them.",
                            "de": "Kein Q für diese Position berechnet: sie enthält "
                                  "mehrere Stoffe, aber n und M wurden nicht angegeben. "
                                  "Falls All packed in one zutrifft, geben Sie sie an.", "fr": "Aucune valeur Q calculée pour cette position : elle contient plusieurs matières mais n et M n'ont pas été saisis. Si le « tout compris dans un seul emballage » s'applique, indiquez-les."},
                        lang,
                    ),
                })
            continue
        components: list[dict[str, Any]] = []
        invalid: list[str] = []
        for index, product in enumerate(entry.get("products") or []):
            raw_n = product.get("q_net_quantity")
            raw_m = product.get("q_max_net_quantity")
            participates = any(str(v or "").strip() for v in (raw_n, raw_m))
            if not participates:
                continue
            label = _product_label(entry, product, index)
            n = _num(raw_n)
            m = _num(raw_m)
            if n is None or m is None or n <= 0 or m <= 0:
                reason_nl = "ontbrekende, nul of negatieve n of M"
                reason_en = "missing, zero or negative n or M"
                invalid.append(f"{label} ({reason_nl if lang == 'nl' else reason_en})")
                continue
            ratio = Decimal(str(n)) / Decimal(str(m))
            components.append({
                "product": label,
                "net_quantity": n,
                "max_per_package": m,
                # Rounded for display only; the sum uses the raw ratio.
                "ratio": float(ratio.quantize(Decimal("0.0001"), rounding=ROUND_CEILING)),
                "_ratio_exact": ratio,
            })

        if not components and not invalid:
            continue

        if invalid:
            results.append({
                "position": entry.get("vehicle") or entry.get("line_id"),
                "components": [
                    {k: v for k, v in c.items() if k != "_ratio_exact"} for c in components
                ],
                "status": "incomplete",
                "q_value": None,
                "exceeded": None,
                "invalid_components": invalid,
                "note": pick(
                    {
                        "nl": "Q kan niet worden bepaald: ",
                        "en": "Q cannot be determined: ",
                        "de": "Q kann nicht bestimmt werden: ", "fr": 'Q ne peut pas être déterminé : '},
                    lang,
                ) + "; ".join(invalid),
            })
            continue

        if len(components) < 2:
            # One participating product: no 'all packed in one', no Q needed.
            continue

        q_raw = sum((c["_ratio_exact"] for c in components), Decimal(0))
        # Rounded up to one decimal, over the unrounded sum.
        q_rounded = float(q_raw.quantize(Decimal("0.1"), rounding=ROUND_CEILING))
        results.append({
            "position": entry.get("vehicle") or entry.get("line_id"),
            "components": [
                {k: v for k, v in c.items() if k != "_ratio_exact"} for c in components
            ],
            "status": "exceeded" if q_rounded > rules["limit"] else "ok",
            "q_value": q_rounded,
            "exceeded": q_rounded > rules["limit"],
            "note": pick(rules["note"], lang),
        })
    return results


# Mass in grams, volume in millilitres: the common denominator in which the
# limits of 3.4 (column 7a) and 3.5.1.2 (E codes) are expressed.
_Q_STATUS_MESSAGE = {
    "nl": {
        "checked": "De Q-controle is uitgevoerd voor de ingevoerde 'all packed in one'-gegevens.",
        "incomplete": "De Q-controle is niet volledig: vul voor iedere deelnemende stof n en M groter dan nul in.",
        "exceeded": "De berekende Q-waarde is groter dan 1.",
        "not_checked": "Geen Q-controle uitgevoerd. Is 'all packed in one' van toepassing, vul dan per stof de nettohoeveelheid n en de maximaal toegestane hoeveelheid M in.",
    },
    "en": {
        "checked": "The Q check was performed for the entered all-packed-in-one data.",
        "incomplete": "The Q check is incomplete: enter n and M greater than zero for every participating substance.",
        "exceeded": "The calculated Q value exceeds 1.",
        "not_checked": "No Q check was performed. If all packed in one applies, enter net quantity n and maximum permitted quantity M for each substance.",
    },
    "de": {
        "checked": "Die Q-Prüfung wurde für die eingegebenen All-packed-in-one-Daten durchgeführt.",
        "incomplete": "Die Q-Prüfung ist unvollständig: Geben Sie für jeden beteiligten Stoff n und M größer als null ein.",
        "exceeded": "Der berechnete Q-Wert ist größer als 1.",
        "not_checked": "Keine Q-Prüfung durchgeführt. Falls All packed in one zutrifft, geben Sie je Stoff die Nettomenge n und die höchstzulässige Menge M ein.",
    },
    "fr": {
        "checked": "Le contrôle Q a été effectué pour les données « all packed in one » saisies.",
        "incomplete": "Le contrôle Q est incomplet : indiquez pour chaque matière participante un n et un M supérieurs à zéro.",
        "exceeded": "La valeur Q calculée est supérieure à 1.",
        "not_checked": "Aucun contrôle Q effectué. Si le « all packed in one » s'applique, indiquez pour chaque matière la quantité nette n et la quantité maximale admissible M.",
    },
}


def q_check_status(q_values: list[dict[str, Any]], language: str = "nl") -> dict[str, str]:
    """Whether the Q check ran, and if not, that this is said.

    A position that was silently skipped was indistinguishable on screen from a
    position that passed. One unchecked position makes the whole consignment
    unchecked: "checked" must not come to mean "one of the two positions was
    checked".
    """
    lang = _lang(language)
    statuses = {item.get("status") for item in q_values}
    if not q_values:
        status = "not_checked"
    elif "exceeded" in statuses:
        status = "exceeded"
    elif "incomplete" in statuses:
        status = "incomplete"
    elif "not_checked" in statuses:
        status = "not_checked"
    else:
        status = "checked"
    return {"status": status, "message": _Q_STATUS_MESSAGE[lang][status]}


_MEASURE_UNITS: dict[str, tuple[float, str]] = {
    "kg": (1000.0, "mass"),
    "g": (1.0, "mass"),
    "gr": (1.0, "mass"),
    "gram": (1.0, "mass"),
    "mg": (0.001, "mass"),
    "l": (1000.0, "volume"),
    "ltr": (1000.0, "volume"),
    "liter": (1000.0, "volume"),
    "litre": (1000.0, "volume"),
    "ml": (1.0, "volume"),
}

_MEASURE_RE = re.compile(
    r"(-?\d[\d.,]*)\s*(kg|mg|gram|gr|g|ml|ltr|litre|liter|l)\b", re.IGNORECASE
)


def _parse_measures(value: Any) -> list[tuple[float, str]]:
    """Every quantity with a unit out of a text, in g or ml.

    '0,5 L' → [(500.0, 'volume')]; '500 ml oder 500 g' → both. A number without
    a unit yields nothing: '0,5' can mean 0.5 g or 0.5 kg, and at an exemption
    limit of all places that must not be guessed at.
    """
    found: list[tuple[float, str]] = []
    for match in _MEASURE_RE.finditer(str(value or "")):
        amount = parse_number(match.group(1))
        if amount is None:
            continue
        factor, kind = _MEASURE_UNITS[match.group(2).lower()]
        found.append((amount * factor, kind))
    return found


def _format_base(amount: float, kind: str) -> str:
    """500.0 → '500 ml' of '500 g'; 5000.0 → '5 L' of '5 kg'."""
    unit = "ml" if kind == "volume" else "g"
    if amount >= 1000 and amount % 1000 == 0:
        amount, unit = amount / 1000, "L" if kind == "volume" else "kg"
    text = str(int(amount)) if float(amount).is_integer() else f"{amount:g}"
    return f"{text} {unit}"


# A reference to a special provision in column 7a/7b ("siehe SV 340",
# "See SP277"): not a limit the app can test against.
_SPECIAL_PROVISION_REF = re.compile(r"\b(?:siehe|see)\b|\bS[VP]\s*\d+", re.IGNORECASE)

_LQ_MESSAGES = {
    "no_data": {
        "nl": "Geen LQ-waarde (kolom 7a) beschikbaar voor deze stof; niet getoetst.",
        "en": "No LQ value (column 7a) available for this substance; not assessed.",
        "de": "Kein LQ-Wert (Spalte 7a) für diesen Stoff verfügbar; nicht geprüft.", "fr": 'Aucune valeur QL (colonne 7a) disponible pour cette matière ; non évaluée.'},
    "special_provision": {
        "nl": "Kolom 7a verwijst naar een bijzondere bepaling ({raw}); die tekst staat "
              "niet in EMCargo. Raadpleeg hoofdstuk 3.3.",
        "en": "Column 7a refers to a special provision ({raw}); that text is not held "
              "by EMCargo. Consult chapter 3.3.",
        "de": "Spalte 7a verweist auf eine Sondervorschrift ({raw}); dieser Text ist "
              "nicht in EMCargo enthalten. Ziehen Sie Kapitel 3.3 heran.", "fr": 'La colonne 7a renvoie à une disposition spéciale ({raw}) dont EMCargo ne dispose pas. Consultez le chapitre 3.3.'},
    "not_permitted": {
        "nl": "Kolom 7a is '0': vervoer als gelimiteerde hoeveelheid (3.4) is voor "
              "deze stof niet toegestaan.",
        "en": "Column 7a is '0': carriage as limited quantity (3.4) is not permitted "
              "for this substance.",
        "de": "Spalte 7a ist '0': Die Beförderung als begrenzte Menge (3.4) ist für "
              "diesen Stoff nicht zugelassen.", "fr": "La colonne 7a porte « 0 » : le transport en quantité limitée (3.4) n'est pas autorisé pour cette matière."},
    "missing_inner": {
        "nl": "LQ-grens {limit}: niet getoetst. Vul de netto hoeveelheid per "
              "binnenverpakking in, met eenheid (bijv. '500 g' of '0,5 L').",
        "en": "LQ limit {limit}: not assessed. Enter the net quantity per inner "
              "packaging, with a unit (e.g. '500 g' or '0.5 L').",
        "de": "LQ-Grenze {limit}: nicht geprüft. Geben Sie die Nettomenge je "
              "Innenverpackung mit Einheit an (z. B. '500 g' oder '0,5 L').", "fr": 'Limite QL {limit} : non évaluée. Indiquez la quantité nette par emballage intérieur, avec son unité (p. ex. « 500 g » ou « 0,5 L »).'},
    "unit_mismatch": {
        "nl": "De eenheid van de binnenverpakking ({inner}) past niet bij de "
              "LQ-grens ({limit}): massa en volume zijn niet uitwisselbaar. "
              "Controleer de invoer.",
        "en": "The unit of the inner packaging ({inner}) does not match the LQ limit "
              "({limit}): mass and volume are not interchangeable. Check the input.",
        "de": "Die Einheit der Innenverpackung ({inner}) passt nicht zur LQ-Grenze "
              "({limit}): Masse und Volumen sind nicht austauschbar. Prüfen Sie die "
              "Eingabe.", "fr": "L'unité de l'emballage intérieur ({inner}) ne correspond pas à celle de la limite QL ({limit}) : masse et volume ne sont pas interchangeables. Vérifiez la saisie."},
    "inner_exceeded": {
        "nl": "De netto hoeveelheid per binnenverpakking ({inner}) is groter dan de "
              "LQ-grens van {limit}. Deze regel kan niet als gelimiteerde hoeveelheid "
              "(3.4) reizen en blijft volledig onder de voorschriften vallen.",
        "en": "The net quantity per inner packaging ({inner}) exceeds the LQ limit of "
              "{limit}. This line cannot travel as a limited quantity (3.4) and "
              "remains fully regulated.",
        "de": "Die Nettomenge je Innenverpackung ({inner}) überschreitet die LQ-Grenze "
              "von {limit}. Diese Zeile kann nicht als begrenzte Menge (3.4) befördert "
              "werden und unterliegt weiterhin allen Vorschriften.", "fr": 'La quantité nette par emballage intérieur ({inner}) dépasse la limite QL de {limit}. Cette ligne ne peut pas voyager en quantité limitée (3.4) et reste intégralement soumise à la réglementation.'},
    "missing_gross": {
        "nl": "Binnenverpakking ({inner}) ≤ LQ-grens {limit}. Vul de bruto massa per "
              "collo in om ook de grens van 30 kg (3.4.2) te toetsen.",
        "en": "Inner packaging ({inner}) ≤ LQ limit {limit}. Enter the gross mass per "
              "package to also assess the 30 kg limit (3.4.2).",
        "de": "Innenverpackung ({inner}) ≤ LQ-Grenze {limit}. Geben Sie die Bruttomasse "
              "je Versandstück an, um auch die 30-kg-Grenze (3.4.2) zu prüfen.", "fr": 'Emballage intérieur ({inner}) ≤ limite QL {limit}. Indiquez la masse brute par colis pour évaluer également la limite de 30 kg (3.4.2).'},
    "gross_exceeded": {
        "nl": "Binnenverpakking ({inner}) ≤ LQ-grens {limit}, maar de bruto massa per "
              "collo ({gross} kg) is groter dan de 30 kg van 3.4.2. Deze regel kan zo "
              "niet als gelimiteerde hoeveelheid reizen.",
        "en": "Inner packaging ({inner}) ≤ LQ limit {limit}, but the gross mass per "
              "package ({gross} kg) exceeds the 30 kg of 3.4.2. As packed, this line "
              "cannot travel as a limited quantity.",
        "de": "Innenverpackung ({inner}) ≤ LQ-Grenze {limit}, aber die Bruttomasse je "
              "Versandstück ({gross} kg) überschreitet die 30 kg nach 3.4.2. So "
              "verpackt kann diese Zeile nicht als begrenzte Menge befördert werden.", "fr": 'Emballage intérieur ({inner}) ≤ limite QL {limit}, mais la masse brute par colis ({gross} kg) dépasse les 30 kg du 3.4.2. Emballée ainsi, cette ligne ne peut pas voyager en quantité limitée.'},
    "within_limits": {
        "nl": "Binnen de grenzen van 3.4: {inner} per binnenverpakking ≤ {limit} en "
              "{gross} kg bruto per collo ≤ 30 kg (voor trays met krimp- of rekfolie "
              "geldt 20 kg, 3.4.3). Het LQ-kenmerk en de verpakkingseisen van 3.4 "
              "blijven gelden.",
        "en": "Within the limits of 3.4: {inner} per inner packaging ≤ {limit} and "
              "{gross} kg gross per package ≤ 30 kg (20 kg for shrink- or "
              "stretch-wrapped trays, 3.4.3). The LQ mark and the packaging "
              "requirements of 3.4 still apply.",
        "de": "Innerhalb der Grenzen von 3.4: {inner} je Innenverpackung ≤ {limit} und "
              "{gross} kg brutto je Versandstück ≤ 30 kg (für Trays mit Schrumpf- "
              "oder Dehnfolie gelten 20 kg, 3.4.3). Die LQ-Kennzeichnung und die "
              "Verpackungsvorschriften von 3.4 gelten weiterhin.", "fr": "Dans les limites du 3.4 : {inner} par emballage intérieur ≤ {limit} et {gross} kg bruts par colis ≤ 30 kg (20 kg pour les plateaux houssés ou filmés, 3.4.3). La marque QL et les prescriptions d'emballage du 3.4 restent applicables."},
}

# Only meaningful next to a points table, so only with a land profile: a line
# that actually travels as LQ does not count towards the 1.1.3.6 points under
# 1.1.3.6.5. The table keeps counting it — an exemption never silently removes
# a result here.
_LQ_POINTS_NOTE = {
    "nl": " Reist deze regel als LQ, dan telt hij volgens 1.1.3.6.5 niet mee in de "
          "1.1.3.6-punten; de puntentabel telt hem volledigheidshalve wél mee.",
    "en": " If this line travels as LQ it does not count towards the 1.1.3.6 points "
          "per 1.1.3.6.5; the points table still includes it for completeness.",
    "de": " Wird diese Zeile als LQ befördert, zählt sie nach 1.1.3.6.5 nicht zu den "
          "Punkten nach 1.1.3.6; die Punktetabelle führt sie der Vollständigkeit "
          "halber dennoch auf.", "fr": " Si cette ligne voyage en quantité limitée, elle ne compte pas dans les points du 1.1.3.6 en vertu du 1.1.3.6.5 ; le tableau des points la reprend néanmoins par souci d'exhaustivité."}

#: What the sea asks of an LQ line that the land does not. IMDG 3.4.1.2.5
#: keeps chapter 5.4 applicable where ADR's chapter 3.4 lifts the transport
#: document altogether, and 3.4.6.1 then adds its own words to it. The CTU
#: sentence is here because it is the sharpest difference from the land: the
#: sea's unit mark of 3.4.5.5 turns on no tonnage at all — no 12 t trigger,
#: no 8 t dispensation — only on whether the unit also carries other
#: dangerous goods that placard it. Read from the registered 42-24 edition,
#: PDF pages 797-799, on 2026-08-26.
_LQ_SEA_NOTE = {
    "nl": " Voor het zeetraject: reist deze regel als LQ, dan hoort volgens "
          "IMDG 3.4.6.1 \"LIMITED QUANTITY\" of \"LTD QTY\" bij de omschrijving "
          "op het vervoersdocument. En anders dan op de weg kent het "
          "LQ-kenmerk op de laadeenheid (3.4.5.5, 250 × 250 mm) geen "
          "tonnagegrens: een eenheid met uitsluitend LQ draagt het altijd; "
          "voert zij plakkaten voor andere gevaarlijke goederen, dan gelden "
          "die.",
    "en": " For the sea leg: if this line travels as LQ, IMDG 3.4.6.1 puts "
          "\"LIMITED QUANTITY\" or \"LTD QTY\" beside the description on the "
          "transport document. And unlike the road, the LQ mark on the cargo "
          "transport unit (3.4.5.5, 250 × 250 mm) turns on no tonnage: a unit "
          "carrying only LQ always bears it; where it carries placards for "
          "other dangerous goods, those apply.",
    "de": " Für die Seestrecke: Wird diese Zeile als LQ befördert, gehört "
          "nach IMDG 3.4.6.1 \"LIMITED QUANTITY\" oder \"LTD QTY\" zur "
          "Beschreibung im Beförderungsdokument. Und anders als auf der "
          "Straße kennt die LQ-Kennzeichnung an der Beförderungseinheit "
          "(3.4.5.5, 250 × 250 mm) keine Tonnagegrenze: eine Einheit mit "
          "ausschließlich LQ trägt sie immer; führt sie Großzettel für "
          "andere gefährliche Güter, gelten diese.",
    "fr": " Pour le trajet maritime : si cette ligne voyage en quantités "
          "limitées, l'IMDG 3.4.6.1 ajoute « LIMITED QUANTITY » ou « LTD "
          "QTY » à la description sur le document de transport. Et "
          "contrairement à la route, la marque QL sur l'engin de transport "
          "(3.4.5.5, 250 × 250 mm) ne dépend d'aucun tonnage : un engin ne "
          "contenant que des QL la porte toujours ; s'il porte des "
          "plaques-étiquettes pour d'autres marchandises dangereuses, "
          "celles-ci s'appliquent.",
}

_EQ_MESSAGES = {
    "no_data": {
        "nl": "Geen E-code (kolom 7b) beschikbaar voor deze stof; niet getoetst.",
        "en": "No E code (column 7b) available for this substance; not assessed.",
        "de": "Kein E-Code (Spalte 7b) für diesen Stoff verfügbar; nicht geprüft.", "fr": 'Aucun code E (colonne 7b) disponible pour cette matière ; non évalué.'},
    "special_provision": {
        "nl": "Kolom 7b verwijst naar een bijzondere bepaling ({raw}); die tekst staat "
              "niet in EMCargo. Raadpleeg hoofdstuk 3.3.",
        "en": "Column 7b refers to a special provision ({raw}); that text is not held "
              "by EMCargo. Consult chapter 3.3.",
        "de": "Spalte 7b verweist auf eine Sondervorschrift ({raw}); dieser Text ist "
              "nicht in EMCargo enthalten. Ziehen Sie Kapitel 3.3 heran.", "fr": 'La colonne 7b renvoie à une disposition spéciale ({raw}) dont EMCargo ne dispose pas. Consultez le chapitre 3.3.'},
    "not_permitted": {
        "nl": "E0: vervoer als vrijgestelde hoeveelheid (3.5) is voor deze stof niet "
              "toegestaan.",
        "en": "E0: carriage as excepted quantity (3.5) is not permitted for this "
              "substance.",
        "de": "E0: Die Beförderung als freigestellte Menge (3.5) ist für diesen Stoff "
              "nicht zugelassen.", "fr": "E0 : le transport en quantité exceptée (3.5) n'est pas autorisé pour cette matière."},
    "missing_inner": {
        "nl": "{code} (max. {inner_cap} g/ml per binnenverpakking, {outer_cap} g/ml "
              "per collo): niet getoetst. Vul de netto hoeveelheid per "
              "binnenverpakking in, met eenheid.",
        "en": "{code} (max. {inner_cap} g/ml per inner packaging, {outer_cap} g/ml per "
              "package): not assessed. Enter the net quantity per inner packaging, "
              "with a unit.",
        "de": "{code} (max. {inner_cap} g/ml je Innenverpackung, {outer_cap} g/ml je "
              "Versandstück): nicht geprüft. Geben Sie die Nettomenge je "
              "Innenverpackung mit Einheit an.", "fr": '{code} (max. {inner_cap} g/ml par emballage intérieur, {outer_cap} g/ml par colis) : non évalué. Indiquez la quantité nette par emballage intérieur, avec son unité.'},
    "missing_outer": {
        "nl": "{code}: binnenverpakking ({inner}) ≤ {inner_cap} g/ml. Vul de netto "
              "hoeveelheid per collo in (met eenheid) om ook de grens van {outer_cap} "
              "g/ml per buitenverpakking te toetsen.",
        "en": "{code}: inner packaging ({inner}) ≤ {inner_cap} g/ml. Enter the net "
              "quantity per package (with a unit) to also assess the {outer_cap} g/ml "
              "limit per outer packaging.",
        "de": "{code}: Innenverpackung ({inner}) ≤ {inner_cap} g/ml. Geben Sie die "
              "Nettomenge je Versandstück (mit Einheit) an, um auch die Grenze von "
              "{outer_cap} g/ml je Außenverpackung zu prüfen.", "fr": '{code} : emballage intérieur ({inner}) ≤ {inner_cap} g/ml. Indiquez la quantité nette par colis (avec son unité) pour évaluer également la limite de {outer_cap} g/ml par emballage extérieur.'},
    "inner_exceeded": {
        "nl": "De netto hoeveelheid per binnenverpakking ({inner}) is groter dan de "
              "{inner_cap} g/ml van {code} (3.5.1.2). Deze regel kan niet als "
              "vrijgestelde hoeveelheid reizen.",
        "en": "The net quantity per inner packaging ({inner}) exceeds the {inner_cap} "
              "g/ml of {code} (3.5.1.2). This line cannot travel as an excepted "
              "quantity.",
        "de": "Die Nettomenge je Innenverpackung ({inner}) überschreitet die "
              "{inner_cap} g/ml von {code} (3.5.1.2). Diese Zeile kann nicht als "
              "freigestellte Menge befördert werden.", "fr": 'La quantité nette par emballage intérieur ({inner}) dépasse les {inner_cap} g/ml du {code} (3.5.1.2). Cette ligne ne peut pas voyager en quantité exceptée.'},
    "outer_exceeded": {
        "nl": "De netto hoeveelheid per collo ({outer}) is groter dan de {outer_cap} "
              "g/ml van {code} (3.5.1.2). Deze regel kan zo niet als vrijgestelde "
              "hoeveelheid reizen.",
        "en": "The net quantity per package ({outer}) exceeds the {outer_cap} g/ml of "
              "{code} (3.5.1.2). As packed, this line cannot travel as an excepted "
              "quantity.",
        "de": "Die Nettomenge je Versandstück ({outer}) überschreitet die {outer_cap} "
              "g/ml von {code} (3.5.1.2). So verpackt kann diese Zeile nicht als "
              "freigestellte Menge befördert werden.", "fr": 'La quantité nette par colis ({outer}) dépasse les {outer_cap} g/ml du {code} (3.5.1.2). Emballée ainsi, cette ligne ne peut pas voyager en quantité exceptée.'},
    "within_limits": {
        "nl": "Binnen de grenzen van {code}: {inner} per binnenverpakking ≤ "
              "{inner_cap} g/ml en {outer} per collo ≤ {outer_cap} g/ml (3.5.1.2). De "
              "verpakkings- en beproevingseisen van 3.5.2 en 3.5.3 en het EQ-kenmerk "
              "blijven gelden; per voertuig of container zijn ten hoogste 1000 colli "
              "toegestaan (3.5.5).",
        "en": "Within the limits of {code}: {inner} per inner packaging ≤ {inner_cap} "
              "g/ml and {outer} per package ≤ {outer_cap} g/ml (3.5.1.2). The "
              "packaging and testing requirements of 3.5.2 and 3.5.3 and the EQ mark "
              "still apply; at most 1,000 packages are permitted per vehicle or "
              "container (3.5.5).",
        "de": "Innerhalb der Grenzen von {code}: {inner} je Innenverpackung ≤ "
              "{inner_cap} g/ml und {outer} je Versandstück ≤ {outer_cap} g/ml "
              "(3.5.1.2). Die Verpackungs- und Prüfvorschriften nach 3.5.2 und 3.5.3 "
              "sowie die EQ-Kennzeichnung gelten weiterhin; je Fahrzeug oder "
              "Container sind höchstens 1000 Versandstücke zulässig (3.5.5).", "fr": "Dans les limites du {code} : {inner} par emballage intérieur ≤ {inner_cap} g/ml et {outer} par colis ≤ {outer_cap} g/ml (3.5.1.2). Les prescriptions d'emballage et d'épreuve des 3.5.2 et 3.5.3 ainsi que la marque QE restent applicables ; 1 000 colis au plus sont admis par véhicule ou conteneur (3.5.5)."},
    "relief_3_5_1_4": {
        "nl": "Ten hoogste 1 g/ml per binnenverpakking en 100 g/ml per collo: "
              "hiervoor gelden alleen 3.5.2 en 3.5.3 (3.5.1.4). Het EQ-kenmerk van "
              "3.5.4 en de grens van 1000 colli van 3.5.5 gelden niet, en een "
              "tussenverpakking is niet vereist als de binnenverpakkingen met "
              "opvulmateriaal zijn verpakt en er bij vloeistoffen genoeg absorberend "
              "materiaal in de buitenverpakking zit.",
        "en": "At most 1 g/ml per inner packaging and 100 g/ml per package: only "
              "3.5.2 and 3.5.3 apply to these (3.5.1.4). The EQ mark of 3.5.4 and the "
              "1,000-package limit of 3.5.5 do not, and no intermediate packaging is "
              "required where the inner packagings are cushioned and, for liquids, "
              "the outer packaging holds enough absorbent material.",
        "de": "Höchstens 1 g/ml je Innenverpackung und 100 g/ml je Versandstück: "
              "hierfür gelten nur 3.5.2 und 3.5.3 (3.5.1.4). Die EQ-Kennzeichnung "
              "nach 3.5.4 und die Grenze von 1000 Versandstücken nach 3.5.5 gelten "
              "nicht, und eine Zwischenverpackung ist nicht erforderlich, wenn die "
              "Innenverpackungen mit Polstermaterial verpackt sind und bei "
              "Flüssigkeiten genügend saugfähiges Material in der Außenverpackung "
              "vorhanden ist.",
        "fr": "Au plus 1 g/ml par emballage intérieur et 100 g/ml par colis : seuls "
              "les 3.5.2 et 3.5.3 s'y appliquent (3.5.1.4). La marque QE du 3.5.4 et "
              "la limite de 1 000 colis du 3.5.5 ne s'appliquent pas, et aucun "
              "emballage intermédiaire n'est exigé si les emballages intérieurs sont "
              "calés et si, pour les liquides, l'emballage extérieur contient assez "
              "de matériau absorbant.",
    },
}

# ADR 3.4.2 / IMDG 3.4.2.1: total gross mass of an LQ package.
_LQ_GROSS_LIMIT_KG = 30.0
# ADR 3.4.13/3.4.14: above this gross mass of LQ packages the transport unit
# carries the large mark of 3.4.15 — and with it, per 8.6.4, a tunnel
# restriction it would not otherwise have had.
_LQ_MARKING_THRESHOLD_KG = 8000.0
# ADR/IMDG 3.5.5: ten hoogste 1000 EQ-colli per voertuig of container.
_EQ_PACKAGE_CAP = 1000

# ADR 3.5.1.4: the smallest excepted quantities. For the codes E1, E2, E4 and E5
# with at most 1 g or 1 ml per inner packaging and at most 100 g or 100 ml per
# outer packaging, only 3.5.2 (packagings, with the intermediate packaging
# waived where the inner ones are cushioned and, for liquids, absorbed) and
# 3.5.3 (the package tests) apply. Everything else in chapter 3.5 falls away —
# including the marking of 3.5.4 and the cap of 3.5.5, which is what makes this
# more than a note on screen: such packages do not count towards the 1,000.
_EQ_RELIEF_CODES = frozenset({"E1", "E2", "E4", "E5"})
_EQ_RELIEF_INNER = 1.0
_EQ_RELIEF_OUTER = 100.0

#: ADR/IMDG 3.5.1.3, the other provision that only shows up across lines.
_EQ_TOGETHER_MESSAGE = {
    "nl": "Deze positie bevat vrijgestelde hoeveelheden met verschillende E-codes "
          "({codes}). Zijn zij samen in één buitenverpakking verpakt, dan geldt de "
          "meest restrictieve code: ten hoogste {cap} g/ml per buitenverpakking "
          "({code}, 3.5.1.3). De ingevoerde hoeveelheden tellen op tot {total} g/ml.",
    "en": "This position holds excepted quantities with different E codes ({codes}). "
          "Packed together in one outer packaging, the most restrictive code applies: "
          "at most {cap} g/ml per outer packaging ({code}, 3.5.1.3). The entered "
          "quantities total {total} g/ml.",
    "de": "Diese Position enthält freigestellte Mengen mit verschiedenen E-Codes "
          "({codes}). Zusammen in einer Außenverpackung verpackt gilt der "
          "restriktivste Code: höchstens {cap} g/ml je Außenverpackung ({code}, "
          "3.5.1.3). Die eingegebenen Mengen ergeben zusammen {total} g/ml.",
    "fr": "Cette position contient des quantités exceptées avec des codes E "
          "différents ({codes}). Emballées ensemble dans un même emballage "
          "extérieur, le code le plus restrictif s'applique : au plus {cap} g/ml par "
          "emballage extérieur ({code}, 3.5.1.3). Les quantités saisies totalisent "
          "{total} g/ml.",
}


def _fmt_kg(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _assess_lq(
    raw: str, inner: list[tuple[float, str]], gross_kg: float | None, lang: str
) -> dict[str, Any]:
    """Test one line against column 7a and the 30 kg limit of 3.4.2."""
    raw = raw.strip()
    result: dict[str, Any] = {"value": raw or None}

    def outcome(status: str, message_key: str, **kwargs: Any) -> dict[str, Any]:
        result["status"] = status
        result["message"] = pick(_LQ_MESSAGES[message_key], lang).format(**kwargs)
        return result

    if not raw or raw in {"-", "–", "—"} or "VERBOTEN" in raw.upper():
        return outcome("no_data", "no_data")
    if _num(raw) == 0:
        return outcome("not_permitted", "not_permitted")
    limits = _parse_measures(raw)
    if not limits:
        if _SPECIAL_PROVISION_REF.search(raw):
            return outcome("no_data", "special_provision", raw=raw)
        return outcome("no_data", "no_data")

    if not inner:
        return outcome("incomplete", "missing_inner", limit=raw)
    inner_amount, inner_kind = inner[0]
    # "500 ml oder 500 g": the variant matching the entered unit is the one that
    # counts.
    limit = next(((a, k) for a, k in limits if k == inner_kind), None)
    if limit is None:
        return outcome(
            "incomplete", "unit_mismatch",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
        )
    if inner_amount > limit[0]:
        return outcome(
            "not_within", "inner_exceeded",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
        )
    if gross_kg is None:
        return outcome(
            "incomplete", "missing_gross",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
        )
    if gross_kg > _LQ_GROSS_LIMIT_KG:
        return outcome(
            "not_within", "gross_exceeded",
            inner=_format_base(inner_amount, inner_kind), limit=raw,
            gross=_fmt_kg(gross_kg),
        )
    return outcome(
        "within_limits", "within_limits",
        inner=_format_base(inner_amount, inner_kind), limit=raw,
        gross=_fmt_kg(gross_kg),
    )


def _assess_eq(
    raw: str,
    inner: list[tuple[float, str]],
    outer: list[tuple[float, str]],
    lang: str,
) -> dict[str, Any]:
    """Test one line against the E code of column 7b (table 3.5.1.2)."""
    code = raw.strip().upper()
    result: dict[str, Any] = {"code": code or None}

    def outcome(status: str, message_key: str, **kwargs: Any) -> dict[str, Any]:
        result["status"] = status
        result["message"] = pick(_EQ_MESSAGES[message_key], lang).format(**kwargs)
        return result

    if not code or code in {"-", "–", "—"} or "VERBOTEN" in code:
        return outcome("no_data", "no_data")
    if code == "E0":
        return outcome("not_permitted", "not_permitted")
    caps = EXCEPTED_QUANTITY_LIMITS.get(code)
    if not caps:
        if _SPECIAL_PROVISION_REF.search(raw):
            return outcome("no_data", "special_provision", raw=raw.strip())
        return outcome("no_data", "no_data")
    inner_cap, outer_cap = caps

    # Table 3.5.1.2 counts in grams for solids and in ml for liquids and gases
    # with the same figure; mass and volume therefore share one limit here.
    if not inner:
        return outcome(
            "incomplete", "missing_inner",
            code=code, inner_cap=inner_cap, outer_cap=outer_cap,
        )
    inner_amount, inner_kind = inner[0]
    if inner_amount > inner_cap:
        return outcome(
            "not_within", "inner_exceeded",
            inner=_format_base(inner_amount, inner_kind), inner_cap=inner_cap, code=code,
        )
    if not outer:
        return outcome(
            "incomplete", "missing_outer",
            code=code, inner=_format_base(inner_amount, inner_kind),
            inner_cap=inner_cap, outer_cap=outer_cap,
        )
    outer_amount, outer_kind = outer[0]
    if outer_amount > outer_cap:
        return outcome(
            "not_within", "outer_exceeded",
            outer=_format_base(outer_amount, outer_kind), outer_cap=outer_cap, code=code,
        )
    outcome(
        "within_limits", "within_limits",
        code=code,
        inner=_format_base(inner_amount, inner_kind), inner_cap=inner_cap,
        outer=_format_base(outer_amount, outer_kind), outer_cap=outer_cap,
    )
    result["outer_cap"] = outer_cap
    result["outer_amount"] = outer_amount
    # 3.5.1.4: the smallest quantities are subject only to 3.5.2 and 3.5.3.
    if (code in _EQ_RELIEF_CODES and inner_amount <= _EQ_RELIEF_INNER
            and outer_amount <= _EQ_RELIEF_OUTER):
        result["relief_3_5_1_4"] = True
        result["message"] += " " + pick(_EQ_MESSAGES["relief_3_5_1_4"], lang)
    return result


def check_lq_eq(
    entries: list[dict[str, Any]], language: str = "nl", profiles: list[str] | None = None
) -> dict[str, Any]:
    """ADR/IMDG 3.4 and 3.5: test the entered quantities against columns 7a and 7b.

    Until now the LQ value and the E code were shown with their meaning, but
    never compared with what had actually been filled in. This check makes that
    comparison — and nothing more. Qualifying on quantity is not the same as
    being exempt: the mark, the packaging requirements and the tests of 3.4 and
    3.5 stay with the consignor. So a line that falls within the limits is
    reported and never silently taken out of the 1.1.3.6 points calculation,
    exactly as the exemption of IMDG 7.2.6.3 is reported without removing a
    warning.
    """
    lang = _lang(language)
    normalized = sorted({p.upper() for p in (profiles or [])})
    use_imdg = "IMDG" in normalized

    rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    statuses: set[str] = set()
    # ADR 3.4.13/3.4.14: above 8 tonnes gross of LQ packages per transport unit,
    # the LQ marking of 3.4.15 on the unit is required. The consignment is read
    # here as one transport unit — the app knows no more than that about the
    # vehicle.
    lq_gross_total_kg = 0.0
    lq_gross_products: list[str] = []

    for entry in entries:
        eq_packages = 0.0
        eq_products: list[str] = []
        # 3.5.1.3, per position: what is packed together in one outer packaging.
        # A position holding several substances is what the application already
        # reads as one outer packaging for the IATA "all packed in one" check;
        # the same reading is used here rather than a second, different one.
        eq_together: list[tuple[str, str, int, float]] = []
        for index, product in enumerate(entry.get("products") or []):
            un = str(product.get("un_number") or "").strip()
            lq_raw = str(product.get("limited_quantity") or "").strip()
            eq_raw = str(product.get("excepted_quantity") or "").strip()
            if not un and not lq_raw and not eq_raw:
                continue
            if product.get("transport_forbidden"):
                # No exemption route for a substance that may not be offered for
                # carriage; the prohibition is already in view.
                continue
            label = _product_label(entry, product, index)

            # The IMDG list (42-24) carries the same columns. Where the product
            # has no value, the list fills it in; where the values differ, that
            # is reported — the check computes with the entered value and does
            # not decide for itself which edition prevails.
            dgl_notes = {"limited_quantity": "", "excepted_quantity": ""}
            if use_imdg and un:
                dgl_row = dangerous_goods_list.entry_for(
                    un, str(product.get("packing_group") or "")
                )
                for column, current in (("limited_quantity", lq_raw),
                                        ("excepted_quantity", eq_raw)):
                    dgl_value = dangerous_goods_list.value(dgl_row, column)
                    if not dgl_value:
                        continue
                    if not current:
                        if column == "limited_quantity":
                            lq_raw = dgl_value
                        else:
                            eq_raw = dgl_value
                    elif dgl_value.replace(" ", "").upper() != current.replace(" ", "").upper():
                        dgl_notes[column] = " " + pick(
                            {
                                "nl": "Let op: de IMDG-lijst (42-24) vermeldt hier "
                                      "{value}; controleer welke waarde voor het "
                                      "zeetraject geldt.",
                                "en": "Note: the IMDG list (42-24) states {value} "
                                      "here; check which value applies to the sea "
                                      "leg.",
                                "de": "Hinweis: die IMDG-Liste (42-24) nennt hier "
                                      "{value}; prüfen Sie, welcher Wert für die "
                                      "Seestrecke gilt.", "fr": "Attention : la liste IMDG (42-24) indique ici {value} ; vérifiez quelle valeur s'applique au trajet maritime."},
                            lang,
                        ).format(value=dgl_value)

            inner = _parse_measures(product.get("net_per_inner_packaging"))
            outer = _parse_measures(product.get("net_mass_liters_per_package"))
            gross_measures = _parse_measures(product.get("gross_mass_per_package"))
            if gross_measures and gross_measures[0][1] == "mass":
                gross_kg: float | None = gross_measures[0][0] / 1000.0
            else:
                gross_kg = _num(product.get("gross_mass_per_package"))

            lq = _assess_lq(lq_raw, inner, gross_kg, lang)
            eq = _assess_eq(eq_raw, inner, outer, lang)
            if lq["status"] == "within_limits" and {"ADR", "RID", "ADN"} & set(normalized):
                lq["message"] += pick(_LQ_POINTS_NOTE, lang)
            if lq["status"] == "within_limits" and use_imdg:
                lq["message"] += pick(_LQ_SEA_NOTE, lang)
            lq["message"] += dgl_notes["limited_quantity"]
            eq["message"] += dgl_notes["excepted_quantity"]
            statuses.add(lq["status"])
            statuses.add(eq["status"])
            rows.append({
                "product": label,
                "position": entry.get("vehicle") or entry.get("line_id"),
                "lq": lq,
                "eq": eq,
            })

            if eq["status"] == "within_limits":
                # 3.5.1.4 takes the smallest quantities out of the whole of
                # chapter 3.5 except 3.5.2 and 3.5.3, so out of the 3.5.5 cap
                # as well. Counting them would refuse a load the text permits.
                if not eq.get("relief_3_5_1_4"):
                    count = _num(product.get("quantity_packages"))
                    if count:
                        eq_packages += count
                        eq_products.append(label)
                if eq.get("outer_cap"):
                    eq_together.append((label, eq["code"], eq["outer_cap"],
                                        eq.get("outer_amount") or 0.0))

            if lq["status"] == "within_limits" and gross_kg:
                count = _num(product.get("quantity_packages"))
                if count:
                    lq_gross_total_kg += gross_kg * count
                    lq_gross_products.append(label)

        # ADR/IMDG 3.5.1.3: where excepted quantities with different E codes are
        # packed together, the total per outer packaging is capped by the most
        # restrictive of those codes. Each line on its own can be within its own
        # code and the package still be over — which is exactly the case that
        # assessing line by line cannot see.
        codes_together = {code for _label, code, _cap, _amount in eq_together}
        if len(codes_together) > 1:
            strictest = min(eq_together, key=lambda item: item[2])
            together_total = sum(amount for _l, _c, _cap, amount in eq_together)
            if together_total > strictest[2]:
                warnings.append({
                    "rule": "ADR/IMDG 3.5.1.3",
                    "severity": "warning",
                    "message": pick(_EQ_TOGETHER_MESSAGE, lang).format(
                        codes=", ".join(sorted(codes_together)),
                        code=strictest[1],
                        cap=strictest[2],
                        total=_fmt_kg(round(together_total, 3)),
                    ),
                    "products": ", ".join(label for label, _c, _cap, _a in eq_together),
                })
                statuses.add("not_within")

        if eq_packages > _EQ_PACKAGE_CAP:
            warnings.append({
                "rule": "ADR/IMDG 3.5.5",
                "severity": "warning",
                "message": pick(
                    {
                        "nl": "Deze positie telt {count} colli die binnen de "
                              "EQ-grenzen vallen; per voertuig of container zijn ten "
                              "hoogste 1000 colli met vrijgestelde hoeveelheden "
                              "toegestaan (3.5.5).",
                        "en": "This position counts {count} packages within the EQ "
                              "limits; at most 1,000 packages of excepted quantities "
                              "are permitted per vehicle or container (3.5.5).",
                        "de": "Diese Position zählt {count} Versandstücke innerhalb "
                              "der EQ-Grenzen; je Fahrzeug oder Container sind "
                              "höchstens 1000 Versandstücke mit freigestellten Mengen "
                              "zulässig (3.5.5).", "fr": 'Cette position compte {count} colis dans les limites QE ; 1 000 colis de quantités exceptées au plus sont admis par véhicule ou conteneur (3.5.5).'},
                    lang,
                ).format(count=_fmt_kg(eq_packages)),
                "products": ", ".join(eq_products),
            })

    lq_marking_required = (lq_gross_total_kg > _LQ_MARKING_THRESHOLD_KG
                           and bool({"ADR", "RID", "ADN"} & set(normalized)))
    if lq_marking_required:
        warnings.append({
            "rule": "ADR 3.4.13/3.4.14",
            "severity": "warning",
            "message": pick(
                {
                    "nl": "De colli die binnen de LQ-grenzen vallen tellen samen "
                          "{tonnes} kg bruto, boven de 8 ton per transporteenheid: de "
                          "vrijstelling van 3.4.14 vervalt daarmee. Of de "
                          "LQ-kenmerking van 3.4.15 (250 × 250 mm) dan werkelijk "
                          "verplicht is, hangt af van twee dingen die deze zending "
                          "niet kent: 3.4.13 geldt pas boven 12 ton toegestane "
                          "maximummassa van de transporteenheid, en niet als de "
                          "eenheid al oranje borden voert voor andere gevaarlijke "
                          "goederen. Beoordeel dat op de rit.",
                    "en": "The packages within the LQ limits total {tonnes} kg gross, "
                          "above the 8 tonnes per transport unit, so the dispensation "
                          "of 3.4.14 falls away. Whether the mark of 3.4.15 "
                          "(250 × 250 mm) is then actually required depends on two "
                          "things this consignment does not know: 3.4.13 applies only "
                          "above 12 tonnes permitted maximum mass of the transport "
                          "unit, and not where the unit already carries orange plates "
                          "for other dangerous goods. Assess that on the trip.",
                    "de": "Die Versandstücke innerhalb der LQ-Grenzen wiegen zusammen "
                          "{tonnes} kg brutto, über den 8 Tonnen je "
                          "Beförderungseinheit; die Erleichterung nach 3.4.14 "
                          "entfällt damit. Ob die Kennzeichnung nach 3.4.15 "
                          "(250 × 250 mm) dann tatsächlich vorgeschrieben ist, hängt "
                          "von zwei Dingen ab, die diese Sendung nicht kennt: 3.4.13 "
                          "gilt erst über 12 Tonnen zulässiger Höchstmasse der "
                          "Beförderungseinheit, und nicht, wenn die Einheit bereits "
                          "orangefarbene Tafeln für andere gefährliche Güter führt. "
                          "Beurteilen Sie das auf der Fahrt.",
                    "fr": "Les colis situés dans les limites QL totalisent {tonnes} kg "
                          "bruts, au-delà des 8 tonnes par unité de transport : la "
                          "dispense du 3.4.14 disparaît donc. Que la marque du 3.4.15 "
                          "(250 × 250 mm) soit alors réellement exigée dépend de deux "
                          "éléments que cet envoi ignore : le 3.4.13 ne s'applique "
                          "qu'au-dessus de 12 tonnes de masse maximale admissible de "
                          "l'unité de transport, et pas lorsque l'unité porte déjà "
                          "des panneaux orange pour d'autres marchandises "
                          "dangereuses. Appréciez cela sur le trajet."},
                lang,
            ).format(tonnes=_fmt_kg(lq_gross_total_kg)),
            "products": ", ".join(lq_gross_products),
        })

    if not rows:
        status = "not_checked"
    elif "incomplete" in statuses:
        status = "incomplete"
    else:
        status = "checked"

    basis = "ADR 3.4 / 3.5 (Tabel A kolom 7a/7b)"
    if use_imdg:
        basis += " + IMDG DGL 42-24"
    return {
        "rows": rows,
        "status": status,
        "warnings": warnings,
        # Read by the tunnel check: 8.6.3.3 leaves 1.1.3 goods out of the
        # determination *except* where this marking is required.
        "lq_marking_required": lq_marking_required,
        # The measured quantity behind that boolean. A consignment cannot
        # settle 3.4.13 on its own — the trigger is the *vehicle's* maximum
        # mass — so the trip check takes this number and finishes the job.
        "lq_gross_total_kg": round(lq_gross_total_kg, 3),
        "basis": basis,
        "basis_note": basis_note(normalized, "3.4/3.5", language),
        "note": pick(
            {
                "nl": "Binnen de grenzen vallen is niet hetzelfde als vrijgesteld "
                      "zijn: het LQ- of EQ-kenmerk en de verpakkingseisen van 3.4 en "
                      "3.5 blijven voorwaarden. De puntentelling van 1.1.3.6 wordt "
                      "hier niet door aangepast.",
                "en": "Falling within the limits is not the same as being exempt: "
                      "the LQ or EQ mark and the packaging requirements of 3.4 and "
                      "3.5 remain conditions. The 1.1.3.6 points calculation is not "
                      "adjusted by this result.",
                "de": "Innerhalb der Grenzen zu liegen ist nicht dasselbe wie "
                      "freigestellt zu sein: die LQ- bzw. EQ-Kennzeichnung und die "
                      "Verpackungsvorschriften von 3.4 und 3.5 bleiben Bedingungen. "
                      "Die Punkteberechnung nach 1.1.3.6 wird durch dieses Ergebnis "
                      "nicht verändert.", "fr": "Rester dans les limites n'équivaut pas à être exempté : la marque QL ou QE et les prescriptions d'emballage des 3.4 et 3.5 demeurent des conditions. Le calcul des points du 1.1.3.6 n'est pas modifié par ce résultat."},
            lang,
        ),
    }


def check_compliance(
    entries: list[dict[str, Any]],
    profiles: list[str],
    language: str = "nl",
) -> dict[str, Any]:
    """Run every relevant check for the chosen regulatory profiles."""
    rules = get_compliance_rules()
    result: dict[str, Any] = {
        "sources": rules["sources"],
        "profiles": profiles,
        # Which regulatory editions this result used. The tables of chapter 7.2
        # are unchanged under 42-24; the substance-specific layer comes from
        # 41-22 with the 42-24 differences laid over it. What that layer does not
        # cover is in IMDG_42_24_not_covered.
        "rule_sets": {
            # Table A has come out of the book itself since v1.56.0; the 2023
            # export was reduced to the one thing the Dutch edition cannot
            # supply, which was the English and German proper shipping names.
            # This line still credited the export for the whole table — and
            # since v1.89.0 it supplies no name at all: all four languages of
            # column (2) are read from the 2025 editions, English last.
            "ADR": ("ADR 2025 — table A read from the official Dutch edition "
                    "(scripts/extract_adr_table_a.py); proper shipping names in "
                    "Dutch, English, French and German read from the 2025 "
                    "editions themselves"),
            "IMDG_class_tables": (
                "Amendment 40-20 (chapter 7.2) — unchanged in 42-24 for "
                + ", ".join(amendment_42_24.verified_unchanged_sections())
            ),
            "IMDG_dangerous_goods_list": (
                f"Amendment 42-24, chapter 3.2 — "
                f"{dangerous_goods_list.source().get('entries', 0)} entries; "
                "columns 16a and 16b come from here"
            ),
            "IMDG_per_substance": (
                "IMDG 42-24 DGL and code descriptions; missing marine pollutant "
                "or bulk assessments require a recorded independent source"
            ),
            "IMDG_current_mandatory": (
                "Amendment 42-24, mandatory since 1-1-2026 — difference layer applied; "
                "the published text remains authoritative"
            ),
            "IMDG_42_24_source": amendment_42_24.source(),
            "IMDG_42_24_not_covered": amendment_42_24.not_covered(_lang(language)),
            "EmS": "MSC.1/Circ.1588/Rev.3, supplemented with the EmS entries of 42-24",
            "IATA": "IATA DGR (lithium/sodium-ion: Guidance 2026)",
        },
    }
    normalized = {p.upper() for p in profiles}
    if "IMDG" in normalized:
        from app.services.dg.source_verification import findings
        result["imdg_source_findings"] = findings(entries, language)


    # What this result was computed with, in one id — usable in a report and in
    # the compliance annex to an export.
    result["regulatory_manifest"] = summary()

    # A rule set that has expired and has not been replaced is not a detail:
    # this check is then computing with text that no longer applies. The result
    # stands, but says for itself that it rests on expired rules.
    for stale in stale_rule_sets(sorted(normalized)):
        result.setdefault("rule_set_warnings", []).append({
            "rule": stale["name"],
            "severity": "warning",
            "message": pick(
                {
                    "nl": "{edition} is verlopen op {on}. Deze controle rekent met een "
                          "editie die niet meer geldt; werk EMCargo bij of raadpleeg de "
                          "actuele uitgave.",
                    "en": "{edition} expired on {on}. This check is computing with an "
                          "edition that no longer applies; update EMCargo or consult the "
                          "current edition.",
                    "de": "{edition} ist am {on} abgelaufen. Diese Prüfung rechnet mit einer "
                          "Ausgabe, die nicht mehr gilt; aktualisieren Sie EMCargo oder "
                          "ziehen Sie die geltende Ausgabe heran.", "fr": "{edition} a expiré le {on}. Cette vérification calcule avec une édition qui n'est plus en vigueur ; mettez EMCargo à jour ou consultez l'édition applicable."},
                language,
            ).format(edition=stale["edition"], on=stale["expired_on"]),
            "products": ", ".join(stale["profiles"]),
        })

    if "ADR" in normalized:
        # Whether the goods may travel in a tank at all. Only speaks when a
        # carriage mode says they do; a packages consignment is unchanged.
        admission = check_adr_tank_admission(entries, language)
        if admission.get("status") != "not_checked":
            result["adr_tank_admission"] = admission

        # And once admitted: may *this* tank carry it? Only speaks when the
        # consignor has said which tank is standing there.
        fit = check_adr_tank_fit(entries, language)
        if fit.get("status") != "not_checked":
            result["adr_tank_fit"] = fit
        # And how full it may be. Speaks for any tank load, because the formula
        # is the answer even where the densities to put in it are missing.
        filling = check_adr_filling_degree(entries, language)
        if filling.get("status") != "not_checked":
            result["adr_filling_degree"] = filling

    if {"ADR", "RID", "ADN"} & normalized:
        land = sorted({"ADR", "RID", "ADN"} & normalized)
        # Special provision 274 belongs to all three land regimes alike: the
        # technical name is part of the description, and its absence has to
        # speak before the document does.
        result["technical_name_findings"] = check_technical_name_required(
            entries, language)
        result["adr_points"] = check_adr_points(entries, language, land)
        # And in bulk — the same question with its own columns (7.3.1.1),
        # answered for road and rail alike and cited to the regime whose
        # document it lands on. Only speaks when a carriage mode says the
        # goods travel that way.
        bulk = check_adr_bulk_admission(entries, language, land)
        if bulk.get("status") != "not_checked":
            result["adr_bulk_admission"] = bulk
        # 7.5.2 is a road and rail chapter. ADN's mixed loading prohibitions
        # are its own — 7.1.4.2 to 7.1.4.5 and 7.1.4.10, read in the English
        # and Dutch editions — so an inland-only consignment is no longer
        # measured against a table it is not subject to, and a combined
        # selection gets both answers, each under its own regime's name.
        road_rail = sorted({"ADR", "RID"} & normalized)
        result["adr_mixed_loading"] = (
            check_adr_mixed_loading(entries, language, road_rail)
            if road_rail else [])
        if "RID" in normalized:
            # 7.5.3 has no road equivalent and therefore does not belong with
            # the borrowed tables, but it does belong in the same list: that one
            # reaches both the panel and the export, and a rail provision that
            # only appears on screen is not on the document.
            result["adr_mixed_loading"] += check_rid_protective_distance(entries, language)
            # 5.4.1.1.1 (j): what belongs on the CIM and on no other document.
            result["rid_transport_document"] = check_rid_transport_document(
                entries, language)
            # RID 5.3 — the wagons and large containers on the rail leg. Its
            # own chapter, not the road's: package wagons placard for every
            # class, and the orange plates attach only via column (20).
            rid_placarding = check_rid_placarding(entries, language)
            if rid_placarding.get("status") != "not_checked":
                result["rid_placarding"] = rid_placarding
        # ADN answers the exemption question with its own rule, so it gets its
        # own result rather than borrowing the points total.
        if "ADN" in normalized:
            # The water's own mixed loading prohibitions, in the same list the
            # road's and rail's reach so they travel to the panel and the
            # export together — each finding cited to its own ADN provision.
            result["adr_mixed_loading"] += check_adn_mixed_loading(
                entries, language)
            # Whether the goods may travel that way on the water at all. Like
            # its road counterpart it only speaks once a carriage mode says the
            # goods are not in packages, and it runs first because the answers
            # below it are chapter 7.1 — dry cargo vessels — and a cargo tank
            # load is not on one.
            admission = check_adn_carriage_admission(entries, language)
            if admission.get("status") != "not_checked":
                result["adn_carriage_admission"] = admission
            result["adn_exemption"] = check_adn_exemption(entries, language)
            # 7.1.4.3 is the inland waterway's own separation rule, and it
            # answers in metres where 7.5.2 answers yes or no.
            result["adn_hold_separation"] = check_adn_hold_separation(
                entries, language)
            # And what the vessel must show while it carries them. Column (12)
            # answers both, and this half had no answer at all before v1.61.0.
            result["adn_signals"] = check_adn_signals(entries, language)
            # What the cargo transport units on board must show — ADN 5.3,
            # the water's own chapter, per kind of unit because the kind is
            # not a thing this application can see.
            adn_placarding = check_adn_placarding(
                entries, language,
                exemption_status=result["adn_exemption"].get("status"))
            if adn_placarding.get("status") != "not_checked":
                result["adn_placarding"] = adn_placarding
            # Column (11), ST01: the one additional requirement of 7.1.6.11
            # that ends up on the transport document rather than in the hold,
            # and therefore its own result and not a separation finding.
            result["adn_stabilisation"] = check_adn_stabilisation(
                entries, language)
        note = basis_note(land, "7.5.2", language)
        if note:
            result["adr_mixed_loading_basis_note"] = note

    # LQ/EQ applies to the land modes *and* to sea transport; air has its own
    # system in the Y packing instructions, which is not claimed here.
    if {"ADR", "RID", "ADN", "IMDG"} & normalized:
        result["lq_eq"] = check_lq_eq(entries, language, sorted(normalized))
        # 7.5.2.4 needs the 3.4 assessment above it: which lines are packed in
        # limited quantities is that check's answer, not a second opinion.
        if "RID" in normalized:
            result["adr_mixed_loading"] += check_rid_limited_quantities_with_explosives(
                entries, language, (result["lq_eq"] or {}).get("rows"))

    # The tunnel code is a road provision and only a road one: RID table A has
    # no column (15) and the ADN document does not carry the code either. It
    # runs after the two checks it depends on, because 8.6.3.3 turns on whether
    # the goods travel under 1.1.3 and whether the unit needs the 3.4.13 mark.
    if "ADR" in normalized:
        # 8.1.5.1 chooses the equipment by the hazard label numbers of the goods
        # loaded, and 8.1.4.2 by whether the load stays inside 1.1.3.6.
        result["adr_equipment"] = check_adr_equipment(
            entries, language,
            points_status=(result.get("adr_points") or {}).get("status"))
        # 5.3 turns on the same exemption: 1.1.3.6.2 relieves the unit of the
        # plates and the placards together.
        result["adr_security"] = check_adr_security(entries, language)
        result["adr_placarding"] = check_adr_placarding(
            entries, language,
            points_status=(result.get("adr_points") or {}).get("status"))
        result["adr_tunnel"] = check_adr_tunnel(
            entries,
            language,
            points_status=(result.get("adr_points") or {}).get("status"),
            lq_marking_required=bool(
                (result.get("lq_eq") or {}).get("lq_marking_required")),
        )

    if "IMDG" in normalized:
        result["imdg_segregation"] = append_class8_pair_exception(
            entries,
            apply_column_16b_precedence(
                check_imdg_segregation(entries, language)
                + check_imdg_class1_compatibility(entries, language)
                + check_imdg_segregation_groups(entries, language)
                + check_imdg_segregation_provisions(entries, language)
                + check_imdg_segregation_exemptions(entries, language),
                language,
            ),
            language,
        ) + check_imdg_amendment_42_24(entries, language)
        result["imdg_note"] = pick(rules["imdg_segregation"]["note"], language)
        # IMDG 5.3 — what the cargo transport unit shows on the outside. The
        # last mode without its own chapter 5.3, and the one where borrowing
        # the road's answer would have been most wrong: four sides rather than
        # two, the proper shipping name on the unit, the marine pollutant mark,
        # and class 9 placarded as 9 where table A says 9A.
        imdg_placarding = check_imdg_placarding(entries, language)
        if imdg_placarding.get("status") != "not_checked":
            result["imdg_placarding"] = imdg_placarding
        groups = rules.get("imdg_segregation_groups")
        if groups:
            lang = _lang(language)
            result["imdg_segregation_groups"] = {
                "note": pick(groups["note"], lang),
                "class8_exception": pick(groups["class8_exception"], lang),
                "groups": [
                    {"code": item["code"], "label": pick(item, lang)} for item in groups["groups"]
                ],
            }

    if "IATA_DGR" in normalized:
        result["iata_segregation"] = (
            check_air_forbidden(entries, language)
            + check_iata_segregation(entries, language)
        )
        result["q_values"] = check_q_value(entries, language)
        # Whether the Q check actually ran belongs with the result and not with
        # one endpoint. Until v1.32.0 this was computed in the route, so the
        # panel reported "no Q check performed" while the export said nothing
        # about it — precisely the place where the document leaves the building.
        # The export check in exporter.py writes for itself that the screen must
        # never be the only place where this is enforced.
        result["q_check_status"] = q_check_status(result["q_values"], language)
        cao = [
            _product_label(entry, product, index)
            for entry, index, product in _iter_products(entries)
            if str(product.get("cargo_aircraft_only") or "").strip().upper() in {"Y", "YES", "JA", "TRUE", "1"}
        ]
        result["cargo_aircraft_only_products"] = cao

    # Chapter 5.2 — the package itself, as against chapter 5.3 above, which is
    # the outside of the vehicle, wagon, vessel or unit. It runs last and over
    # every profile at once rather than inside a per-profile block, because the
    # regimes disagree about this chapter and the answer has to show that side
    # by side: a consignment going by road and then by sea carries the proper
    # shipping name on its packages for the second leg and not for the first,
    # and a packer who sees only one of those answers packs the wrong box.
    # Air is left out on purpose: the IATA marking rules have not been read,
    # and the land answer is not the air answer.
    marking = check_package_marking(entries, sorted(normalized), language)
    if marking.get("status") != "not_checked":
        result["package_marking"] = marking

    return result
