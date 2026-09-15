"""Enrichment of UN entries for automatic completion per transport mode.

A compilation of facts as an aid to filling in; the current edition of ADR/RID/
ADN, the IMDG Code and the IATA DGR always prevails. Sources:
- EmS per UN number: the index of IMO MSC.1/Circ.1588/Rev.3 (EmS Guide), with
  all fire schedules F-A to F-J and spillage schedules S-A to S-Z. See
  seed/dg/ems.json. For the few UN numbers not in it, an indicative class
  default applies, which is marked as such.
- Excepted quantities (E codes): ADR/IMDG/IATA 3.5.1.2.
- Air freight rules: IATA Guidance Document for Lithium Batteries and Sodium ion
  Batteries (2026) and the IATA DGR; ICAO TI for the class 2.3 prohibition.
- Environmentally hazardous/marine pollutant: UN 3077/3082 and ADR
  classification codes M6/M7 (IMDG 2.10).
- Transport prohibition: the labels column of ADR Table A.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

from app.core.languages import SUPPORTED, pick
from app.services.dg import amendment_42_24, dangerous_goods_list

# EmS (fire, spillage) per UN number — loaded from backend/seed/dg/ems.json.
_SEED_EMS = Path(__file__).resolve().parents[3] / "seed" / "dg" / "ems.json"
_ems_lock = threading.Lock()
_ems_cache: dict[str, Any] | None = None


def _load_ems() -> dict[str, Any]:
    global _ems_cache
    with _ems_lock:
        if _ems_cache is None:
            _ems_cache = json.loads(_SEED_EMS.read_text(encoding="utf-8"))
    return _ems_cache


def lookup_ems(un_number: str, packing_group: str = "") -> dict[str, Any] | None:
    """EmS entry for a UN number from the EmS Guide index.

    A few entries have their own schedule per packing group (UN 1826 and UN 2031
    for instance) or have variants with a description of their own (UN 3166,
    gas- or liquid-powered vehicles). Those are passed along here so the
    interface can show the choice.
    """
    digits = "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)
    entry = _load_ems()["entries"].get(digits)
    if not entry:
        # UN numbers added by Amendment 42-24 are not yet in the 2022 EmS Guide
        # index; their schedules come from the 42-24 source.
        entry = amendment_42_24.ems_additions().get(digits)
    if not entry:
        return None

    if "by_packing_group" in entry:
        groups = entry["by_packing_group"]
        pg = str(packing_group or "").strip().upper()
        # Exact hit, otherwise the variant without the */† marking.
        chosen = groups.get(pg) or next(
            (v for k, v in sorted(groups.items()) if k.rstrip("*†") == pg), None
        )
        if chosen:
            return {**chosen, "packing_group": pg, "packing_group_options": groups}
        return {"packing_group_options": groups}

    if "variants" in entry:
        return {"variants": entry["variants"]}

    return entry


# What "yes/no/maybe" in column 4 of the Dangerous Goods List means, in plain words.
_MARINE_POLLUTANT_TEXT = {
    "yes": {
        "nl": "Marine pollutant: ja — merken en vermelden op het vervoersdocument.",
        "en": "Marine pollutant: yes — mark and declare on the transport document.",
        "de": "Meeresschadstoff: ja — kennzeichnen und im Beförderungspapier angeben.", "fr": 'Polluant marin : oui — à marquer et à déclarer sur le document de transport.'},
    "unknown": {
        "nl": "Marine pollutant: onbekend. Leg de stofbeoordeling en bron vast (IMDG 2.10).",
        "en": "Marine pollutant: unknown. Record the substance assessment and source (IMDG 2.10).",
        "de": "Meeresschadstoff: unbekannt. Stoffbeurteilung und Quelle dokumentieren (IMDG 2.10).", "fr": 'Polluant marin : inconnu. Documentez l’évaluation de la matière et la source (IMDG 2.10).'},
    "maybe": {
        "nl": "Marine pollutant: hangt van de stof af. Beoordeel aan de criteria van "
              "IMDG 2.10 en merk zo nodig alsnog.",
        "en": "Marine pollutant: depends on the substance. Assess against the criteria "
              "of IMDG 2.10 and mark if it meets them.",
        "de": "Meeresschadstoff: hängt vom Stoff ab. Beurteilen Sie ihn anhand der Kriterien "
              "des IMDG 2.10 und kennzeichnen Sie gegebenenfalls.", "fr": "Polluant marin : dépend de la matière. Appréciez-la au regard des critères du 2.10 de l'IMDG et marquez-la si elle y répond."},
}

# Segregation groups (IMDG 3.1.4.4) — loaded from seed/dg/segregation_groups.json.
_SEED_SGG = Path(__file__).resolve().parents[3] / "seed" / "dg" / "segregation_groups.json"
_sgg_cache: dict[str, Any] | None = None


def _load_sgg() -> dict[str, Any]:
    global _sgg_cache
    with _ems_lock:
        if _sgg_cache is None:
            _sgg_cache = json.loads(_SEED_SGG.read_text(encoding="utf-8"))
    return _sgg_cache


def segregation_groups_for(un_number: str, packing_group: str = "") -> list[str]:
    """Segregation group codes of a UN number, e.g. ['SGG1', 'SGG18'].

    Two sources say the same thing here: the list of 3.1.4.4 and column 16b of
    the Dangerous Goods List, which puts a substance's groups before its SG
    codes. They are taken together — where one knows a group the other misses,
    that one counts.
    """
    digits = "".join(ch for ch in str(un_number or "") if ch.isdigit()).zfill(4)
    groups = list(_load_sgg()["by_un"].get(digits, []))
    row = dangerous_goods_list.entry_for(digits, packing_group)
    for code in dangerous_goods_list.segregation_groups(row):
        if code not in groups:
            groups.append(code)
    return groups


def imdg_segregation_codes_for(un_number: str, packing_group: str = "") -> list[str]:
    """Column 16b of the current DGL; no third-party card fallback."""
    row = dangerous_goods_list.entry_for(un_number, packing_group)
    return dangerous_goods_list.segregation_codes(row)


def segregation_provisions() -> dict[str, Any]:
    """Interpret the independently sourced IMDG 7.2.8 descriptions."""
    from app.services.dg.segregation_rules import parse_provision
    return {code: parse_provision(code, text)
            for code, text in _load_imdg_codes().get("segregation_codes", {}).get("codes", {}).items()}


# The meaning of the codes from columns 16a and 16b, read from chapters 7.1.5,
# 7.1.6 and 7.2.8 of the IMDG Code itself. The DGL says which codes a
# substance carries; this table says what they mean — previously only available
# as a fragment from the card text.
_SEED_CODES = Path(__file__).resolve().parents[3] / "seed" / "dg" / "imdg_codes.json"
_codes_cache: dict[str, Any] | None = None


def _load_imdg_codes() -> dict[str, Any]:
    global _codes_cache
    with _ems_lock:
        if _codes_cache is None:
            try:
                _codes_cache = json.loads(_SEED_CODES.read_text(encoding="utf-8"))
            except (OSError, ValueError):  # pragma: no cover - seed ontbreekt
                _codes_cache = {}
    return _codes_cache


def imdg_code_text(code: str) -> str:
    """Description of an SW, H or SG code, or empty when it is unknown.

    A reserved code deliberately yields nothing: "[Reserved]" is not a provision
    and does not belong on screen as guidance.
    """
    key = str(code or "").strip().upper()
    for section in ("stowage_codes", "handling_codes", "segregation_codes"):
        entry = _load_imdg_codes().get(section) or {}
        text = (entry.get("codes") or {}).get(key)
        if text:
            return text
    return ""


def describe_imdg_codes(codes: list[str]) -> list[dict[str, str]]:
    """Codes with their description, in the order they were given."""
    described = []
    for code in codes:
        text = imdg_code_text(code)
        if text:
            described.append({"code": str(code).strip().upper(), "text": text})
    return described


def segregation_group_label(code: str, language: str = "nl") -> str:
    for group in _load_sgg()["groups"]:
        if group["code"] == code:
            return pick(group, language, code)
    return code


def ems_schedule_label(code: str, language: str = "nl") -> str:
    """Description of a fire or spillage schedule, e.g. 'F-E' → '…'."""
    data = _load_ems()
    key = "fire_schedules" if str(code).upper().startswith("F") else "spillage_schedules"
    item = data.get(key, {}).get(str(code).strip().upper())
    if not item:
        return ""
    return pick(item, language)


def describe_ems(ems_code: str, language: str = "nl") -> str:
    """'F-E, S-E' → 'F-E (…) · S-E (…)' for display in the interface."""
    parts = []
    for code in re.split(r"[,;/]\s*", str(ems_code or "")):
        code = code.strip().upper()
        label = ems_schedule_label(code, language)
        parts.append(f"{code} ({label})" if label else code)
    return " · ".join(p for p in parts if p)


# Indicative EmS default per class (the IMDG DGL follows these patterns in most
# cases; deviations per substance occur — hence "indicative").
EMS_DEFAULT_BY_CLASS: dict[str, tuple[str, str]] = {
    "1": ("F-B", "S-X"),
    "2.1": ("F-D", "S-U"),
    "2.2": ("F-C", "S-V"),
    "2.3": ("F-C", "S-U"),
    "3": ("F-E", "S-D"),
    "4.1": ("F-A", "S-G"),
    "4.2": ("F-A", "S-J"),
    "4.3": ("F-G", "S-N"),
    "5.1": ("F-A", "S-Q"),
    "5.2": ("F-J", "S-R"),
    "6.1": ("F-A", "S-A"),
    "6.2": ("F-A", "S-T"),
    "7": ("F-I", "S-S"),
    "8": ("F-A", "S-B"),
    "9": ("F-A", "S-F"),
}

# Vrijgestelde hoeveelheden (ADR/IMDG/IATA 3.5.1.2):
# code -> (max netto per binnenverpakking, max netto per buitenverpakking), in g of ml.
EXCEPTED_QUANTITY_LIMITS: dict[str, tuple[int, int]] = {
    "E1": (30, 1000),
    "E2": (30, 500),
    "E3": (30, 300),
    "E4": (1, 500),
    "E5": (1, 300),
}

# Luchtvrachtregels per UN-nummer. Bron: IATA Guidance Document for Lithium
# Batteries and Sodium ion Batteries (editie 2026) en de IATA DGR.
AIR_RULES_BY_UN: dict[str, dict[str, Any]] = {
    "3480": {
        "cargo_aircraft_only": True,
        "iata_packing_instruction": "965",
        "note_nl": "Lithium-ionbatterijen (los verpakt): verboden als vracht op passagiersvliegtuigen, dus uitsluitend Cargo Aircraft Only met CAO-label. IATA PI 965, laadtoestand ten hoogste 30% van de nominale capaciteit; hoger uitsluitend met goedkeuring van het land van herkomst en van de exploitant (bijzondere bepaling A331).",
        "note_en": "Lithium-ion batteries (packed by themselves): forbidden as cargo on passenger aircraft, so Cargo Aircraft Only with CAO label. IATA PI 965, state of charge no more than 30% of rated capacity; higher only with approval of the State of Origin and the State of the Operator (special provision A331).",
    },
    "3090": {
        "cargo_aircraft_only": True,
        "iata_packing_instruction": "968",
        "note_nl": "Lithium-metaalbatterijen (los verpakt): verboden als vracht op passagiersvliegtuigen, uitsluitend Cargo Aircraft Only met CAO-label. IATA PI 968; vervoer op een passagiersvliegtuig alleen onder goedkeuring volgens bijzondere bepaling A201.",
        "note_en": "Lithium metal batteries (packed by themselves): forbidden as cargo on passenger aircraft, Cargo Aircraft Only with CAO label. IATA PI 968; carriage on a passenger aircraft only under an approval per special provision A201.",
    },
    "3481": {
        "iata_packing_instruction": "966/967",
        "note_nl": "Lithium-ionbatterijen met of in apparatuur: IATA PI 966 (met apparatuur) of PI 967 (in apparatuur).",
        "note_en": "Lithium-ion batteries packed with or contained in equipment: IATA PI 966 (packed with) or PI 967 (contained in).",
    },
    "3091": {
        "iata_packing_instruction": "969/970",
        "note_nl": "Lithium-metaalbatterijen met of in apparatuur: IATA PI 969 (met apparatuur) of PI 970 (in apparatuur).",
        "note_en": "Lithium metal batteries packed with or contained in equipment: IATA PI 969 (packed with) or PI 970 (contained in).",
    },
    "3551": {
        "iata_packing_instruction": "976",
        "note_nl": "Natrium-ionbatterijen met organisch elektrolyt (los verpakt): IATA PI 976. Natrium-ionbatterijen met waterig alkalisch elektrolyt vallen onder UN 2795 (accu's, nat, gevuld met alkali).",
        "note_en": "Sodium ion batteries with organic electrolyte (packed by themselves): IATA PI 976. Sodium-ion batteries with aqueous alkali electrolyte fall under UN 2795 (batteries, wet, filled with alkali).",
    },
    "3552": {
        "iata_packing_instruction": "977/978",
        "note_nl": "Natrium-ionbatterijen met of in apparatuur: IATA PI 977 (met apparatuur) of PI 978 (in apparatuur).",
        "note_en": "Sodium ion batteries packed with or contained in equipment: IATA PI 977 (packed with) or PI 978 (contained in).",
    },
    "3556": {
        "note_nl": "Voertuig aangedreven door een lithium-ionbatterij: bij een batterij van meer dan 100 Wh gelden de volledige voorschriften voor voertuigen op batterijen.",
        "note_en": "Vehicle powered by a lithium-ion battery: with a battery exceeding 100 Wh the full provisions for battery-powered vehicles apply.",
    },
    "3557": {
        "note_nl": "Voertuig aangedreven door een lithium-metaalbatterij: bij een batterij van meer dan 100 Wh gelden de volledige voorschriften voor voertuigen op batterijen.",
        "note_en": "Vehicle powered by a lithium metal battery: with a battery exceeding 100 Wh the full provisions for battery-powered vehicles apply.",
    },
    "3558": {
        "note_nl": "Voertuig aangedreven door een natrium-ionbatterij: bij een batterij van meer dan 100 Wh gelden de volledige voorschriften voor voertuigen op batterijen.",
        "note_en": "Vehicle powered by a sodium ion battery: with a battery exceeding 100 Wh the full provisions for battery-powered vehicles apply.",
    },
}

# Classes that are (almost always) forbidden in aviation.
AIR_FORBIDDEN_CLASSES = {"2.3"}

# UN numbers that are environmentally hazardous by definition; classification
# codes M6/M7 (ADR) mark environmentally hazardous substances of class 9 (IMDG:
# marine pollutant).
ENVIRONMENTALLY_HAZARDOUS_UN = {"3077", "3082"}
ENVIRONMENTALLY_HAZARDOUS_CODES = {"M6", "M7"}


# Additional document requirements that cannot be derived from Table A and that
# the user has to supply themselves (ADR/RID/ADN 5.4.1.1, IMDG 5.4.1, IATA 8.1.6).
CLASS_DOCUMENT_NOTES: dict[str, dict[str, str]] = {
    "1": {
        "nl": "Klasse 1: vermeld in het vervoersdocument de totale netto explosieve massa (NEM) per stof en, bij samenlading, de compatibiliteitsgroepen (ADR 5.4.1.2.1).",
        "en": "Class 1: state the total net explosive mass (NEM) per substance in the transport document and, when mixed, the compatibility groups (ADR 5.4.1.2.1).",
        "de": "Klasse 1: Geben Sie im Beförderungspapier die gesamte Nettoexplosivstoffmasse (NEM) je Stoff an und bei Zusammenladung die Verträglichkeitsgruppen (ADR 5.4.1.2.1).", "fr": 'Classe 1 : indiquez dans le document de transport la masse nette explosive (MNE) totale par matière et, en cas de mélange, les groupes de compatibilité (ADR 5.4.1.2.1).'},
    "2": {
        "nl": "Klasse 2: bij tankvervoer en drukhouders horen de vuldatum, beproevingsdatum en het toegestane vulgewicht bij de zending (ADR 5.4.1.2.2).",
        "en": "Class 2: for tanks and pressure receptacles the filling date, test date and permitted filling mass accompany the consignment (ADR 5.4.1.2.2).",
        "de": "Klasse 2: Bei Tankbeförderung und Druckgefäßen gehören Fülldatum, Prüfdatum und die zulässige Füllmasse zur Sendung (ADR 5.4.1.2.2).", "fr": "Classe 2 : pour les citernes et récipients à pression, la date de remplissage, la date d'épreuve et la masse de remplissage admissible accompagnent l'envoi (ADR 5.4.1.2.2)."},
    "4.1": {
        "nl": "Zelfontledende stoffen en gedesensibiliseerde explosieven: vermeld de temperatuurbeheersing (controle- en noodtemperatuur) wanneer die geldt (ADR 5.4.1.2.3.1).",
        "en": "Self-reactive substances and desensitized explosives: state the control and emergency temperature where applicable (ADR 5.4.1.2.3.1).",
        "de": "Selbstzersetzliche Stoffe und desensibilisierte explosive Stoffe: Geben Sie die Kontroll- und Notfalltemperatur an, wo sie vorgeschrieben ist (ADR 5.4.1.2.3.1).", "fr": 'Matières autoréactives et explosibles désensibilisés : indiquez le cas échéant la température de régulation et la température critique (ADR 5.4.1.2.3.1).'},
    "5.2": {
        "nl": "Organische peroxiden: vermeld de controle- en noodtemperatuur wanneer temperatuurbeheersing is voorgeschreven (ADR 5.4.1.2.3.1).",
        "en": "Organic peroxides: state the control and emergency temperature where temperature control is required (ADR 5.4.1.2.3.1).",
        "de": "Organische Peroxide: Geben Sie die Kontroll- und Notfalltemperatur an, wenn eine Temperaturkontrolle vorgeschrieben ist (ADR 5.4.1.2.3.1).", "fr": 'Peroxydes organiques : indiquez la température de régulation et la température critique lorsque la régulation de température est exigée (ADR 5.4.1.2.3.1).'},
    "6.2": {
        "nl": "Klasse 6.2: vermeld naam en telefoonnummer van een verantwoordelijke persoon in het vervoersdocument (ADR 5.4.1.2.4).",
        "en": "Class 6.2: state the name and telephone number of a responsible person in the transport document (ADR 5.4.1.2.4).",
        "de": "Klasse 6.2: Geben Sie Namen und Telefonnummer einer verantwortlichen Person im Beförderungspapier an (ADR 5.4.1.2.4).", "fr": "Classe 6.2 : indiquez dans le document de transport le nom et le numéro de téléphone d'une personne responsable (ADR 5.4.1.2.4)."},
    "7": {
        "nl": "Klasse 7: het vervoersdocument vereist aanvullend de radionucliden, fysische en chemische vorm, maximale activiteit, collo-categorie (I-WIT/II-GEEL/III-GEEL), transportindex en waar van toepassing de veiligheidsindex kritikaliteit (ADR 5.4.1.2.5.1).",
        "en": "Class 7: the transport document additionally requires the radionuclides, physical and chemical form, maximum activity, package category (I-WHITE/II-YELLOW/III-YELLOW), transport index and, where applicable, the criticality safety index (ADR 5.4.1.2.5.1).",
        "de": "Klasse 7: Das Beförderungspapier verlangt zusätzlich die Radionuklide, die physikalische und chemische Form, die höchste Aktivität, die Versandstückkategorie (I-WEISS/II-GELB/III-GELB), die Transportkennzahl und, wo zutreffend, die Kritikalitätssicherheitskennzahl (ADR 5.4.1.2.5.1).", "fr": "Classe 7 : le document de transport exige en outre les radionucléides, la forme physique et chimique, l'activité maximale, la catégorie du colis (I-BLANCHE/II-JAUNE/III-JAUNE), l'indice de transport et, le cas échéant, l'indice de sûreté-criticité (ADR 5.4.1.2.5.1)."},
}

# Aanvullende vereisten per modaliteitsprofiel.
PROFILE_DOCUMENT_NOTES: dict[str, dict[str, str]] = {
    "IMDG": {
        "nl": "Zeevervoer: het containerbeladingscertificaat (CTU-packing certificate) hoort bij de zending, en bij containers over zee geldt de geverifieerde bruto massa (VGM, SOLAS VI/2).",
        "en": "Sea transport: the container/vehicle packing certificate accompanies the consignment, and containers require a verified gross mass (VGM, SOLAS VI/2).",
        "de": "Seebeförderung: Die Container-/Fahrzeugpackbescheinigung gehört zur Sendung, und für Container gilt die verifizierte Bruttomasse (VGM, SOLAS VI/2).", "fr": "Transport maritime : le certificat d'empotage du conteneur/véhicule accompagne l'envoi et les conteneurs exigent une masse brute vérifiée (MBV, SOLAS VI/2)."},
    "IATA_DGR": {
        "nl": "Luchtvervoer: de Shipper's Declaration wordt in tweevoud ondertekend aangeleverd en de hoeveelheden per collo mogen de limieten van de gekozen verpakkingsinstructie niet overschrijden.",
        "en": "Air transport: the Shipper's Declaration is provided signed in duplicate and quantities per package must not exceed the limits of the applicable packing instruction.",
        "de": "Luftbeförderung: Die Shipper's Declaration wird in zweifacher Ausfertigung unterschrieben beigefügt, und die Mengen je Versandstück dürfen die Grenzwerte der gewählten Verpackungsanweisung nicht überschreiten.", "fr": "Transport aérien : la déclaration de l'expéditeur est fournie signée en deux exemplaires et les quantités par colis ne doivent pas dépasser les limites de l'instruction d'emballage applicable."},
}


def _norm_un(un: str) -> str:
    return "".join(ch for ch in str(un or "") if ch.isdigit()).zfill(4)


# For forbidden substances ADR Table A fills *every* column with this text; it
# must never end up as a data value in a form or a document line.
FORBIDDEN_MARKER = "VERBOTEN"


def clean_value(value: Any) -> str:
    """Empty string for columns that only repeat the transport prohibition."""
    text = str(value or "").strip()
    return "" if FORBIDDEN_MARKER in text.upper() else text


def _norm_label(token: str) -> str:
    """'9A' → '9', '2.3' → '2.3'; label model letters are not part of the class."""
    token = token.strip().upper()
    match = re.match(r"^(\d(?:\.\d)?)", token)
    return match.group(1) if match else token


#: A label model number and nothing else. The labels cell is not always one:
#: two rows of the Dutch edition spell out the word for "none" and twelve read
#: "See 5.2.2.1.12". Neither is a number to put in brackets after the class, and
#: 5.4.1.1.1 (c) says what to do instead — where column (5) gives no label
#: model, the class of column (3a) is given.
_LABEL_MODEL = re.compile(r"^\d(?:\.\d)?$")

#: The label models of class 1 that 5.4.1.1.1 (c) does *not* repeat in brackets
#: after the classification code. RID adds the shunting label model 13 and
#: model 15 to that list; the table this application holds is the ADR's, whose
#: column (5) carries neither, so those two are a guard and not a conversion.
_CLASS1_OWN_LABELS = {"1", "1.4", "1.5", "1.6"}


#: Table A separates the label models of one row with a plus in the 2023 export
#: and with a comma in the Dutch 2025 edition. Splitting on the plus alone left
#: "6.1, 3" as a single token, so every subsidiary label model was lost on its
#: way to the transport document — 718 of the 3,158 rows of the 2025 table carry
#: more than one, UN 1098 ALLYL ALCOHOL among them, which is the very substance
#: RID 5.4.1.1.1 uses for its own example: "6.1 (3), I".
_LABEL_SEPARATOR = re.compile(r"[+,]")


def parse_hazards(entry: dict[str, Any]) -> dict[str, Any]:
    """Derive primary hazard (division included) and subsidiary risks from ADR Table A.

    The 'class' column gives only '2' for gases and only '1' for explosives; the
    actual division is in the labels column and the classification code
    respectively ('1.4S' for instance). Subsidiary risks are the labels *after*
    the first — the classification code (F1, M4, C1) is not a subsidiary risk.

    For class 1 "after the first" is not the rule the text states: 5.4.1.1.1 (c)
    puts the label models *other than 1, 1.4, 1.5 and 1.6* in brackets behind
    the classification code, which is a set and not a position.
    """
    hazard_class = str(entry.get("class") or "").strip()
    classification = str(entry.get("classification_code") or "").strip().upper()
    raw_labels = clean_value(entry.get("labels"))
    tokens = [_norm_label(t) for t in _LABEL_SEPARATOR.split(raw_labels) if t.strip()]

    division = hazard_class
    if hazard_class == "1" and re.match(r"^1\.\d[A-S]$", classification):
        division = classification  # 1.4S for instance — decisive for mixed loading
    elif tokens and tokens[0].startswith(f"{hazard_class}."):
        division = tokens[0]  # bijv. gassen: klasse 2 → divisie 2.1/2.2/2.3
    elif not hazard_class and tokens:
        division = tokens[0]

    if hazard_class == "1":
        rest = [t for t in tokens if t not in _CLASS1_OWN_LABELS]
    else:
        rest = tokens[1:]
    subsidiary = [t for t in rest
                  if t and t != division and _LABEL_MODEL.match(t)]
    return {
        "division": division,
        "subsidiary_risks": subsidiary,
        "classification_code": classification,
        "labels": raw_labels,
    }


def describe_excepted_quantity(code: str, language: str = "nl") -> str | None:
    code = (code or "").strip().upper()
    if code == "E0":
        return pick(
            {
                "nl": "E0: niet toegestaan als vrijgestelde hoeveelheid",
                "en": "E0: not permitted as excepted quantity",
                "de": "E0: als freigestellte Menge nicht zugelassen", "fr": 'E0 : non admis en quantité exceptée'},
            language,
        )
    limits = EXCEPTED_QUANTITY_LIMITS.get(code)
    if not limits:
        return None
    inner, outer = limits
    return pick(
        {
            "nl": "{code}: max. {inner} g/ml per binnenverpakking, {outer} g/ml per buitenverpakking",
            "en": "{code}: max. {inner} g/ml per inner packaging, {outer} g/ml per outer packaging",
            "de": "{code}: max. {inner} g/ml je Innenverpackung, {outer} g/ml je Außenverpackung", "fr": '{code} : max. {inner} g/ml par emballage intérieur, {outer} g/ml par emballage extérieur'},
        language,
    ).format(code=code, inner=inner, outer=outer)


def enrich_un_entry(entry: dict[str, Any], language: str = "nl") -> dict[str, Any]:
    """Derivable data per transport mode for an offline UN entry.

    Returns only fields that can be derived with sufficient certainty;
    indicative values are marked explicitly so the interface can show them as a
    suggestion instead of filling them in.
    """
    un = _norm_un(entry.get("un", entry.get("un_number", "")))
    hazard_class = str(entry.get("class") or "").strip()
    classification = str(entry.get("classification_code") or "").strip().upper()
    extras: dict[str, Any] = {}

    # Transport prohibition. The 2023 export wrote "BEFÖRDERUNG VERBOTEN" across
    # the row; the Dutch 2025 table writes nothing at all, which is the same
    # signature as "not subject to ADR" and cannot be acted on. So the database
    # marks the entry from the export's own words and this reads that mark —
    # falling back on the text for the two withdrawn rows that still carry it.
    labels_raw = str(entry.get("labels") or "")
    if entry.get("transport_forbidden") or "VERBOTEN" in labels_raw.upper():
        extras["transport_forbidden"] = True
        extras["transport_forbidden_note"] = pick(
            {
                "nl": "Deze stof mag volgens ADR Tabel A niet ten vervoer worden aangeboden. "
                      "Vervoer is uitsluitend mogelijk onder een ontheffing van de bevoegde "
                      "autoriteit.",
                "en": "Per ADR Table A this substance is not permitted for carriage. "
                      "Carriage is only possible under an exemption from the competent "
                      "authority.",
                "de": "Dieser Stoff darf nach ADR Tabelle A nicht zur Beförderung aufgegeben "
                      "werden. Eine Beförderung ist nur mit einer Ausnahmegenehmigung der "
                      "zuständigen Behörde möglich.", "fr": "Selon le tableau A de l'ADR, cette matière n'est pas admise au transport. Le transport n'est possible que sous dérogation de l'autorité compétente."},
            language,
        )
    if "5.2.2.1.12" in labels_raw:
        extras["label_reference_note"] = pick(
            {
                "nl": "Etikettering volgens 5.2.2.1.12: voorwerpen die gevaarlijke goederen "
                      "bevatten krijgen de etiketten van elk aanwezig gevaar.",
                "en": "Labelling per 5.2.2.1.12: articles containing dangerous goods bear "
                      "the labels for each hazard present.",
                "de": "Bezettelung nach 5.2.2.1.12: Gegenstände, die gefährliche Güter "
                      "enthalten, tragen die Gefahrzettel jeder vorhandenen Gefahr.", "fr": 'Étiquetage selon le 5.2.2.1.12 : les objets contenant des marchandises dangereuses portent les étiquettes de chacun des dangers présents.'},
            language,
        )

    packing_group = clean_value(entry.get("packing_group"))

    # Segregation groups (IMDG 3.1.4.4): decisive for segregation on board.
    sgg = segregation_groups_for(un, packing_group)
    if sgg:
        extras["segregation_groups"] = sgg
        extras["segregation_groups_text"] = ", ".join(
            f"{code} ({segregation_group_label(code, language)})" for code in sgg
        )

    # Sea transport (IMDG): EmS from the official EmS Guide index.
    ems = lookup_ems(un, clean_value(entry.get("packing_group")))
    if ems and ems.get("fire"):
        extras["ems_code"] = f"{ems['fire']}, {ems['spillage']}"
        extras["ems_source"] = "ems_guide"
        extras["ems_description"] = describe_ems(extras["ems_code"], language)
    elif ems and ems.get("variants"):
        extras["ems_variants"] = [
            {
                "label": item["label"],
                "code": f"{item['fire']}, {item['spillage']}",
                "description": describe_ems(f"{item['fire']}, {item['spillage']}", language),
            }
            for item in ems["variants"]
        ]
        extras["ems_source"] = "ems_guide_variants"
    elif ems and ems.get("packing_group_options"):
        extras["ems_packing_group_options"] = {
            pg: f"{v['fire']}, {v['spillage']}" for pg, v in ems["packing_group_options"].items()
        }
        extras["ems_source"] = "ems_guide_packing_group"
    else:
        # Terugval op de divisie (2.1/2.3) en anders op de hoofdklasse.
        division = str(entry.get("labels") or "").split("+")[0].strip() or hazard_class
        default = EMS_DEFAULT_BY_CLASS.get(division) or EMS_DEFAULT_BY_CLASS.get(hazard_class)
        if default:
            extras["ems_class_default"] = f"{default[0]}, {default[1]}"
            extras["ems_source"] = "class_default"

    # The current DGL supplies stowage/segregation. Absence of a P mark is
    # not evidence that a particular substance or mixture is non-polluting.
    from app.services.dg.source_verification import marine_pollutant_status
    pollutant = marine_pollutant_status(un, packing_group)
    extras["marine_pollutant_status"] = pollutant
    extras["marine_pollutant_text"] = pick(_MARINE_POLLUTANT_TEXT[pollutant], language)
    extras["imdg_bulk_status"] = "unknown"
    if pollutant == "yes":
        extras["environmentally_hazardous"] = True

    row = dangerous_goods_list.entry_for(un, packing_group)
    if row:
        extras["imdg_dgl_source"] = dangerous_goods_list.source().get("source", "")
        extras["imdg_amendment"] = dangerous_goods_list.source().get("amendment", "")

        stowage = dangerous_goods_list.stowage_codes(row)
        if stowage:
            extras["imdg_stowage_codes"] = stowage
            described = describe_imdg_codes(stowage)
            if described:
                extras["imdg_stowage_definitions"] = described
        segregation = dangerous_goods_list.segregation_codes(row)
        if segregation:
            extras["imdg_segregation_codes"] = segregation
            described = describe_imdg_codes(segregation)
            if described:
                extras["imdg_segregation_definitions"] = described

        category = dangerous_goods_list.stowage_category(row)
        if category:
            extras["imdg_stowage_category"] = category

        for column, key in (
            ("subsidiary_hazards", "imdg_subsidiary_hazards"),
            ("packing_instructions", "imdg_packing_instructions"),
            ("packing_provisions", "imdg_packing_provisions"),
            ("tank_instructions", "imdg_tank_instructions"),
            ("tank_provisions", "imdg_tank_provisions"),
            ("properties_and_observations", "imdg_properties"),
        ):
            text = dangerous_goods_list.value(row, column)
            if text:
                extras[key] = text

        provisions = dangerous_goods_list.special_provisions(row)
        if provisions:
            extras["imdg_special_provisions"] = provisions

        if dangerous_goods_list.amended_in_42_24(row):
            extras["imdg_amended_in_42_24"] = True

    # What Amendment 42-24 changes about this substance. This is independent of
    # the card: substances without a card (or new in 42-24) can have changes too.
    changes = amendment_42_24.changes_for(un, packing_group, language)
    if changes:
        extras["imdg_amendment_changes"] = changes
        extras["imdg_amendment"] = amendment_42_24.amendment()
    doc_requirement = amendment_42_24.document_requirement(un, language)
    if doc_requirement:
        extras["imdg_document_requirement"] = doc_requirement

    # Environmentally hazardous / marine pollutant — the ADR side, which applies
    # with or without a card.
    if un in ENVIRONMENTALLY_HAZARDOUS_UN or classification in ENVIRONMENTALLY_HAZARDOUS_CODES:
        extras["environmentally_hazardous"] = True

    # Luchtvracht (IATA/ICAO)
    air = AIR_RULES_BY_UN.get(un)
    if air:
        if air.get("cargo_aircraft_only"):
            extras["cargo_aircraft_only"] = True
        if air.get("iata_packing_instruction"):
            extras["iata_packing_instruction"] = air["iata_packing_instruction"]
        extras["air_note"] = pick(
            {lang: air[f"note_{lang}"] for lang in SUPPORTED if air.get(f"note_{lang}")},
            language,
        )
    # The aviation prohibition hangs on the division, not on the class column:
    # gases appear in Table A as class "2" and the division (2.1/2.2/2.3) sits in
    # the labels column. Testing against the column meant that chlorine (UN 1017)
    # — forbidden on passenger *and* cargo aircraft under the ICAO TI — never got
    # a warning.
    division = parse_hazards(entry)["division"]
    if division in AIR_FORBIDDEN_CLASSES:
        extras["air_forbidden"] = True
        extras["air_note"] = pick(
            {
                "nl": "Klasse 2.3 (giftige gassen) is in de luchtvaart verboden, op enkele "
                      "uitzonderingen na.",
                "en": "Division 2.3 (toxic gases) is forbidden in air transport, with few "
                      "exceptions.",
                "de": "Unterklasse 2.3 (giftige Gase) ist in der Luftbeförderung bis auf "
                      "wenige Ausnahmen verboten.", "fr": 'La division 2.3 (gaz toxiques) est interdite au transport aérien, à de rares exceptions près.'},
            language,
        )

    # Vrijgestelde hoeveelheden uitleggen
    eq_text = describe_excepted_quantity(clean_value(entry.get("excepted_quantity")), language)
    if eq_text:
        extras["excepted_quantity_text"] = eq_text

    lq = clean_value(entry.get("limited_quantity"))
    if lq and lq != "0":
        extras["limited_quantity_text"] = pick(
            {
                "nl": "LQ: max. {lq} per binnenverpakking (ADR/IMDG 3.4)",
                "en": "LQ: max. {lq} per inner packaging (ADR/IMDG 3.4)",
                "de": "LQ: max. {lq} je Innenverpackung (ADR/IMDG 3.4)", "fr": 'QL : max. {lq} par emballage intérieur (ADR/IMDG 3.4)'},
            language,
        ).format(lq=lq)

    return extras
