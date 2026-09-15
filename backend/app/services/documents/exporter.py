import os
import math
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.services.documents.notices import OUTPUT_NOTICES
from app.core.languages import normalise, pick
from app.core.messages import detail as error_detail
from app.services.documents import brand, customs_route
from app.services.dg.autofill import adr_quantity, description_line
from app.services.dg.database import get_un_entries, is_transport_forbidden
from app.services.dg.naming import english_name_is_usable, resolve_for_profile
from app.services.documents.registry import condition_met, get_document, resolve_sections
from app.services.edifact import iftdgn

TEXTS = {
    "generated_with": {
        "nl": "Gegenereerd met {brand} op",
        "en": "Generated with {brand} on",
        "de": "Erstellt mit {brand} am", "fr": 'Généré avec {brand} le'},
    "status": {"nl": "Documentstatus", "en": "Document status", "de": "Dokumentstatus", "fr": 'Statut du document'},
    "goods": {"nl": "Goederenregels", "en": "Cargo lines", "de": "Güterzeilen", "fr": 'Lignes de marchandises'},
    "dg_table": {"nl": "Gevaarlijke stoffen", "en": "Dangerous goods", "de": "Gefahrgut", "fr": 'Marchandises dangereuses'},
    "not_prefilled": {
        "nl": "niet vooraf ingevuld — handtekening/bevestiging vereist",
        "en": "not pre-filled — signature/confirmation required",
        "de": "nicht vorausgefüllt — Unterschrift/Bestätigung erforderlich", "fr": 'non prérempli — signature ou confirmation requise'},
    "carrier_provided": {
        "nl": "in te vullen door vervoerder/expediteur",
        "en": "to be provided by carrier/forwarder",
        "de": "vom Frachtführer/Spediteur auszufüllen", "fr": 'à fournir par le transporteur ou le commissionnaire'},
    "operational": {
        "nl": "in te vullen tijdens uitvoering",
        "en": "to be filled in during execution",
        "de": "während der Durchführung auszufüllen", "fr": "à compléter lors de l'exécution"},
    "confirmed": {
        "nl": "Bevestigd in {brand}; ondertekening op het document blijft vereist",
        "en": "Confirmed in {brand}; signature on the document is still required",
        "de": "In {brand} bestätigt; die Unterschrift auf dem Dokument bleibt erforderlich", "fr": 'Confirmé dans {brand} ; la signature sur le document reste requise'},
    "not_confirmed": {
        "nl": "NIET bevestigd",
        "en": "NOT confirmed",
        "de": "NICHT bestätigt", "fr": 'NON confirmé'},
    "totals": {"nl": "Totalen", "en": "Totals", "de": "Summen", "fr": 'Totaux'},
    "line_headers": {
        "nl": ["Nr", "Omschrijving", "Aantal", "Eenheid", "Gewicht (kg)", "Volume (m³)", "L×B×H (cm)"],
        "en": ["No", "Description", "Qty", "Unit", "Weight (kg)", "Volume (m³)", "L×W×H (cm)"],
        "de": ["Nr.", "Bezeichnung", "Menge", "Einheit", "Gewicht (kg)", "Volumen (m³)", "L×B×H (cm)"],
        "fr": ["N°", "Désignation", "Quantité", "Unité", "Poids (kg)", "Volume (m³)", "L×l×h (cm)"],
    },
    "dg_headers": {
        "nl": [
            "Positie",
            "UN-nummer",
            "Proper Shipping Name",
            "Technische naam",
            "Klasse",
            "Nevengevaar",
            "Verpakkingsgroep",
            "Packing instruction",
            "Aantal colli",
            "Verpakkingstype",
            "Hoeveelheid per verpakking",
            "Bruto massa per verpakking",
            "Marine pollutant",
            "Cargo Aircraft Only",
            "Aanvullende informatie",
        ],
        "en": [
            "Position",
            "UN number",
            "Proper Shipping Name",
            "Technical name",
            "Class",
            "Subsidiary risk",
            "Packing group",
            "Packing instruction",
            "Packages",
            "Package type",
            "Quantity per package",
            "Gross mass per package",
            "Marine pollutant",
            "Cargo Aircraft Only",
            "Additional information",
        ],
        "de": [
            "Position",
            "UN-Nummer",
            "Proper Shipping Name",
            "Technische Benennung",
            "Klasse",
            "Nebengefahr",
            "Verpackungsgruppe",
            "Verpackungsanweisung",
            "Anzahl Versandstücke",
            "Verpackungsart",
            "Menge je Verpackung",
            "Bruttomasse je Verpackung",
            "Meeresschadstoff",
            "Cargo Aircraft Only",
            "Zusätzliche Angaben",
        ],
        "fr": [
            "Position",
            "Numéro ONU",
            "Désignation officielle de transport",
            "Nom technique",
            "Classe",
            "Risque subsidiaire",
            "Groupe d'emballage",
            "Instruction d'emballage",
            "Nombre de colis",
            "Type d'emballage",
            "Quantité par emballage",
            "Masse brute par emballage",
            "Polluant marin",
            "Cargo Aircraft Only",
            "Informations complémentaires",
        ],
    },
    "dg_missing": {
        "nl": "Gevaarlijke-stoffenclassificatie onvolledig voor",
        "en": "Dangerous goods classification incomplete for",
        "de": "Gefahrgutklassifizierung unvollständig für", "fr": 'Classification des marchandises dangereuses incomplète pour'},
    "dg_forbidden": {
        "nl": "Niet ten vervoer toegelaten volgens ADR Tabel A (vervoer alleen onder ontheffing van de bevoegde autoriteit)",
        "en": "Not permitted for carriage per ADR Table A (carriage only under an exemption from the competent authority)",
        "de": "Nach ADR Tabelle A zur Beförderung nicht zugelassen (Beförderung nur mit Ausnahmegenehmigung der zuständigen Behörde)", "fr": "Non admis au transport selon le tableau A de l'ADR (transport uniquement sous dérogation de l'autorité compétente)"},
    "field_required": {
        "nl": "Verplicht veld ontbreekt",
        "en": "Required field missing",
        "de": "Pflichtfeld fehlt", "fr": 'Champ obligatoire manquant'},
    # The two customs references whose condition the route decides
    # (customs_route.py). Empty while the route says the reference applies
    # is worth a word, never a refusal: the ENS is the carrier's to lodge and
    # its MRN often arrives after the papers are drawn up.
    "customs_ens_mrn_applies": {
        "nl": "ENS-referentie: op deze route komen de goederen het douanegebied van de EU "
              "(ICS2-gebied) binnen — de summiere aangifte bij binnenbrengen wordt door de "
              "vervoerder ingediend; vul het MRN in zodra het bekend is",
        "en": "ENS reference: on this route the goods enter the EU customs territory "
              "(ICS2 area) — the entry summary declaration is lodged by the carrier; "
              "fill in its MRN once known",
        "de": "ENS-Referenz: Auf dieser Route gelangen die Waren in das Zollgebiet der EU "
              "(ICS2-Gebiet) — die summarische Eingangsanmeldung gibt der Beförderer ab; "
              "tragen Sie die MRN ein, sobald sie bekannt ist",
        "fr": "Référence ENS : sur cet itinéraire, les marchandises entrent sur le territoire "
              "douanier de l'UE (zone ICS2) — la déclaration sommaire d'entrée est déposée par "
              "le transporteur ; indiquez son MRN dès qu'il est connu"},
    "customs_aes_itn_applies": {
        "nl": "AES ITN: dit is uitvoer uit de Verenigde Staten — de Electronic Export "
              "Information wordt in AES aangegeven (15 CFR 30.2); het ITN hoort op het "
              "vervoersdocument",
        "en": "AES ITN: this is an export from the United States — Electronic Export "
              "Information is filed in AES (15 CFR 30.2); the ITN belongs on the transport "
              "document",
        "de": "AES ITN: Dies ist eine Ausfuhr aus den Vereinigten Staaten — die Electronic "
              "Export Information wird in AES angemeldet (15 CFR 30.2); die ITN gehört auf "
              "das Beförderungsdokument",
        "fr": "ITN AES : il s'agit d'une exportation depuis les États-Unis — l'Electronic "
              "Export Information est déposée dans AES (15 CFR 30.2) ; l'ITN doit figurer "
              "sur le document de transport"},
    "dg_name_language": {
        "nl": "Vervoersnaam op dit document in het Engels gezet, zoals "
              "IMDG 5.4.1.4.1 / IATA DGR 8.1.2.1 voorschrijven",
        "en": "Proper shipping name set to English on this document, as "
              "IMDG 5.4.1.4.1 / IATA DGR 8.1.2.1 require",
        "de": "Offizielle Benennung auf diesem Dokument auf Englisch gesetzt, "
              "wie IMDG 5.4.1.4.1 / IATA DGR 8.1.2.1 es verlangen", "fr": "Désignation officielle de transport mise en anglais sur ce document, comme l'exigent le 5.4.1.4.1 de l'IMDG et le 8.1.2.1 de l'IATA DGR"},
    # The counterpart of not inventing a unit. EMCargo used to default a
    # unitless quantity to kilograms, so "100" silently became "100 kg" on the
    # consignment note; now the number stands bare and the omission is named.
    "quantity_without_unit": {
    # {un} arrives already prefixed ("UN 1090"), like every other UN number in
    # these texts — do not write "UN {un}" or the number reads "UN UN 1090".
        "nl": "ADR 5.4.1.1.1 (f): bij {un} staat een totale hoeveelheid zonder "
              "eenheid. Vul de eenheid in — vloeistoffen in liter, vaste stoffen "
              "in netto kg, gassen in waterinhoud (liter). Zonder eenheid staat er "
              "een getal op het document waarvan niemand weet wat het meet.",
        "en": "ADR 5.4.1.1.1 (f): {un} carries a total quantity with no unit. "
              "Enter the unit — litres for liquids, net kg for solids, water "
              "capacity in litres for gases. Without it the document shows a "
              "number and no one can tell what it measures.",
        "de": "ADR 5.4.1.1.1 (f): Bei {un} steht eine Gesamtmenge ohne Einheit. "
              "Tragen Sie die Einheit ein — Flüssigkeiten in Liter, feste Stoffe in "
              "netto kg, Gase als Fassungsraum in Liter. Ohne sie steht auf dem "
              "Dokument eine Zahl, von der niemand weiß, was sie misst.",
        "fr": "ADR 5.4.1.1.1 (f) : la quantité totale de {un} n'a pas d'unité. "
              "Indiquez-la — litres pour les liquides, kg nets pour les solides, "
              "contenance en eau en litres pour les gaz. Sans elle, le document "
              "porte un nombre dont personne ne sait ce qu'il mesure.",
    },
    "adn_remark_information": {
        "nl": "ADN 5.4.1.1.2 (h): kolom (20) van tabel C draagt voor UN {un} "
              "opmerking {remarks}. De informatie die deze opmerking vereist "
              "moet in het vervoerdocument worden opgenomen; de tekst van de "
              "opmerking staat in 3.2.3.1 van het ADN en is niet in deze "
              "applicatie opgenomen.",
        "en": "ADN 5.4.1.1.2 (h): column (20) of table C carries remark "
              "{remarks} for UN {un}. The information that remark requires must "
              "be included in the transport document; the remark's text is in "
              "3.2.3.1 of the ADN and is not held in this application.",
        "de": "ADN 5.4.1.1.2 (h): Spalte (20) der Tabelle C führt für UN {un} "
              "die Bemerkung {remarks}. Die von dieser Bemerkung verlangte "
              "Angabe muss in das Beförderungspapier aufgenommen werden; der "
              "Wortlaut steht in 3.2.3.1 des ADN und ist in dieser Anwendung "
              "nicht enthalten.",
        "fr": "ADN 5.4.1.1.2 (h) : la colonne (20) du tableau C porte "
              "l'observation {remarks} pour l'ONU {un}. L'information qu'elle "
              "exige doit figurer dans le document de transport ; son texte se "
              "trouve au 3.2.3.1 de l'ADN et n'est pas repris dans cette "
              "application.",
    },
    "no_english_name": {
        "nl": "De ADR-tabel bevat geen bruikbare Engelse vervoersnaam voor UN {un}; "
              "op dit document staat nu de Duitse. IMDG 5.4.1.4.1 en IATA DGR 8.1.2.1 "
              "eisen Engels, en ADR 5.4.1.4.1 vraagt naast het Nederlands om Engels, "
              "Frans of Duits. Vul de naam zelf in.",
        "en": "The ADR table holds no usable English proper shipping name for UN {un}; "
              "this document now carries the German one. IMDG 5.4.1.4.1 and IATA DGR "
              "8.1.2.1 require English, and ADR 5.4.1.4.1 asks for English, French or "
              "German beside the Dutch. Enter the name yourself.",
        "de": "Die ADR-Tabelle enthält für UN {un} keine brauchbare englische Benennung; "
              "auf diesem Dokument steht jetzt die deutsche. IMDG 5.4.1.4.1 und IATA DGR "
              "8.1.2.1 verlangen Englisch, und ADR 5.4.1.4.1 verlangt neben dem "
              "Niederländischen Englisch, Französisch oder Deutsch. Tragen Sie die "
              "Benennung selbst ein.",
        "fr": "Le tableau ADR ne contient pas de désignation officielle anglaise "
              "utilisable pour l'ONU {un} ; ce document porte donc l'allemande. Le "
              "5.4.1.4.1 de l'IMDG et le 8.1.2.1 de l'IATA DGR exigent l'anglais, et le "
              "5.4.1.4.1 de l'ADR demande l'anglais, le français ou l'allemand à côté du "
              "néerlandais. Indiquez la désignation vous-même.",
    },
    "field_format": {
        "nl": "Veld heeft niet de vereiste vorm",
        "en": "Field does not have the required format",
        "de": "Feld hat nicht die vorgeschriebene Form", "fr": "Le champ n'a pas le format requis"},
    "no_dg_lines": {
        "nl": "Dit document vereist gevaarlijke-stoffenregels, maar er zijn geen DG-posities.",
        "en": "This document requires dangerous goods lines, but no DG positions exist.",
        "de": "Dieses Dokument verlangt Gefahrgutzeilen, es sind aber keine Gefahrgutpositionen vorhanden.", "fr": "Ce document exige des lignes de marchandises dangereuses, mais aucune position n'a été saisie."},
    "vgm_mismatch": {
        "nl": "VGM wijkt af van de som van de componenten (methode 2)",
        "en": "VGM differs from the sum of the components (method 2)",
        "de": "VGM weicht von der Summe der Bestandteile ab (Methode 2)", "fr": 'La masse brute vérifiée diffère de la somme des composants (méthode 2)'},
    "fixed_texts": {
        "nl": "Vaste teksten en verklaringen (officieel formulier)",
        "en": "Fixed texts and declarations (official form)",
        "de": "Feste Texte und Erklärungen (amtliches Formular)", "fr": 'Textes fixes et déclarations (formulaire officiel)'},
    "legal_reference": {"nl": "Regelgeving", "en": "Regulations", "de": "Vorschriften", "fr": 'Réglementation'},
    "adr_points_incomplete": {
        "nl": "puntentelling onvolledig — controleer vervoerscategorie en hoeveelheid",
        "en": "points calculation incomplete — check transport category and quantity",
        "de": "Punkteberechnung unvollständig — Beförderungskategorie und Menge prüfen", "fr": 'calcul des points incomplet — vérifiez la catégorie de transport et la quantité'},
    "adr_exemption_lost": {
        "nl": "vrijstelling vervalt ({detail}) — de volledige ADR-eisen gelden",
        "en": "exemption does not apply ({detail}) — the full ADR requirements apply",
        "de": "Freistellung entfällt ({detail}) — es gelten die vollen ADR-Anforderungen", "fr": "l'exemption ne s'applique pas ({detail}) — l'ensemble des prescriptions de l'ADR s'applique"},
    "dg_description": {
        "nl": "Omschrijving vervoersdocument",
        "en": "Transport document description",
        "de": "Angabe im Beförderungspapier", "fr": 'Description du document de transport'},
    "card_qr": {
        "nl": "Scan voor de UN-kaarten van de stoffen op dit document, op de server "
              "van deze installatie. De code bevat alleen de UN-nummers — niets over "
              "de zending, de partijen of de hoeveelheden.",
        "en": "Scan for the UN cards of the substances on this document, on this "
              "installation's own server. The code carries the UN numbers only — "
              "nothing about the consignment, the parties or the quantities.",
        "de": "Scannen Sie für die UN-Karten der Stoffe auf diesem Dokument, auf dem "
              "Server dieser Installation. Der Code enthält nur die UN-Nummern — "
              "nichts über die Sendung, die Parteien oder die Mengen.",
        "fr": "Scannez pour les fiches UN des matières figurant sur ce document, sur "
              "le serveur de cette installation. Le code ne contient que les numéros "
              "UN — rien sur l'envoi, les parties ni les quantités.",
    },
    "disclaimer": OUTPUT_NOTICES,
    "iata_dg_headers": {
        "nl": [
            "UN- of ID-nr.",
            "Proper Shipping Name (technische naam)",
            "Klasse of divisie (nevengevaar)",
            "Verpakkingsgroep",
            "Hoeveelheid en soort verpakking",
            "Packing Inst.",
            "Authorization",
        ],
        "en": [
            "UN or ID No.",
            "Proper Shipping Name (technical name)",
            "Class or Division (Subsidiary Hazard)",
            "Packing Group",
            "Quantity and Type of Packing",
            "Packing Inst.",
            "Authorization",
        ],
        "de": [
            "UN- oder ID-Nr.",
            "Proper Shipping Name (technische Benennung)",
            "Klasse oder Unterklasse (Nebengefahr)",
            "Verpackungsgruppe",
            "Menge und Verpackungsart",
            "Packing Inst.",
            "Authorization",
        ],
        "fr": [
            "N° ONU ou ID",
            "Désignation officielle de transport (nom technique)",
            "Classe ou division (risque subsidiaire)",
            "Groupe d'emballage",
            "Quantité et type d'emballage",
            "Packing Inst.",
            "Authorization",
        ],
    },
    "adr_dg_headers": {
        "nl": [
            "Omschrijving conform 5.4.1.1.1",
            "Aantal colli",
            "Verpakkingstype",
            "Hoeveelheid per verpakking",
            "Bruto massa per verpakking",
            "Aanvullende informatie",
        ],
        "en": [
            "Description per 5.4.1.1.1",
            "Packages",
            "Package type",
            "Quantity per package",
            "Gross mass per package",
            "Additional information",
        ],
        "de": [
            "Angabe nach 5.4.1.1.1",
            "Anzahl Versandstücke",
            "Verpackungsart",
            "Menge je Verpackung",
            "Bruttomasse je Verpackung",
            "Zusätzliche Angaben",
        ],
        "fr": [
            "Description selon le 5.4.1.1.1",
            "Nombre de colis",
            "Type d'emballage",
            "Quantité par emballage",
            "Masse brute par emballage",
            "Informations complémentaires",
        ],
    },
    "imdg_dg_headers": {
        "nl": [
            "UN-nummer",
            "Proper Shipping Name (technische naam)",
            "Klasse (nevengevaar)",
            "Verpakkingsgroep",
            "Marine pollutant",
            "Vlampunt",
            "EmS",
            "Aantal en soort colli",
            "Hoeveelheid per verpakking",
            "Bruto massa per verpakking",
        ],
        "en": [
            "UN number",
            "Proper Shipping Name (technical name)",
            "Class (subsidiary risk)",
            "Packing group",
            "Marine pollutant",
            "Flashpoint",
            "EmS",
            "Number and kind of packages",
            "Quantity per package",
            "Gross mass per package",
        ],
        "fr": [
            "Numéro ONU",
            "Désignation officielle de transport (nom technique)",
            "Classe (risque subsidiaire)",
            "Groupe d'emballage",
            "Polluant marin",
            "Point d'éclair",
            "EmS",
            "Nombre et type de colis",
            "Quantité par emballage",
            "Masse brute par emballage",
        ],
        "de": [
            "UN-Nummer",
            "Proper Shipping Name (technische Benennung)",
            "Klasse (Nebengefahr)",
            "Verpackungsgruppe",
            "Meeresschadstoff",
            "Flammpunkt",
            "EmS",
            "Anzahl und Art der Versandstücke",
            "Menge je Verpackung",
            "Bruttomasse je Verpackung",
        ],
    },
}

DG_PRODUCT_FIELDS = [
    "un_number",
    "proper_shipping_name",
    "technical_name",
    "class",
    "subsidiary_risks",
    "packing_group",
    "packing_instruction",
    "quantity_packages",
    "type_of_package",
    "net_mass_liters_per_package",
    "gross_mass_per_package",
    "marine_pollutant",
    "cargo_aircraft_only",
    "additional_information",
]

DG_BASE_REQUIRED = ["un_number", "proper_shipping_name", "class"]
DG_PROFILE_REQUIRED = {
    "ADR": DG_BASE_REQUIRED,
    "RID": DG_BASE_REQUIRED,
    "ADN": DG_BASE_REQUIRED,
    "IMDG": DG_BASE_REQUIRED + ["quantity_packages", "type_of_package"],
    "IATA_DGR": DG_BASE_REQUIRED
    + ["packing_instruction", "quantity_packages", "type_of_package", "net_mass_liters_per_package"],
}


def _lang(language: str) -> str:
    return normalise(language)


def _label(item: dict[str, Any], lang: str) -> str:
    return pick(item.get("label"), lang, item.get("key", "")) or item.get("key", "")


def _localised(value: Any, lang: str) -> str:
    """A {nl, en, de} block from the registry in the requested language."""
    if isinstance(value, dict):
        return str(pick(value, lang))
    return str(value or "")


def _text(key: str, lang: str) -> Any:
    # A fallback rather than a KeyError: a language still missing a single line
    # must not bring an export down. "{brand}" is the installation's name.
    return brand.fill(pick(TEXTS[key], lang))


def _option_label(field: dict[str, Any], value: Any, lang: str) -> Any:
    for option in field.get("options", []):
        if option.get("value") == value:
            return _label(option, lang)
    return value


def validate_document(
    document: dict[str, Any],
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> tuple[list[str | dict[str, Any]], list[str]]:
    """Return (blocking errors, warnings) for a document export."""
    lang = _lang(language)
    errors: list[str | dict[str, Any]] = []
    warnings: list[str] = []
    customs_verdicts: dict[str, customs_route.Verdict] | None = None
    if document.get("key") in {"cmr", "avc_waybill"}:
        included = [line for line in lines if line.get("include", True)]
        def positive(value: Any) -> bool:
            try:
                return math.isfinite(float(value)) and float(value) > 0
            except (TypeError, ValueError):
                return False
        if not included or any(not str(line.get("description") or "").strip()
                               or not positive(line.get("quantity"))
                               or not positive(line.get("weight_total_kg")) for line in included):
            errors.append(error_detail("documents.goods_incomplete"))

    for section in resolve_sections(document):
        for field in section.get("fields", []):
            value = values.get(field["key"])
            empty = value is None or str(value).strip() == ""
            if field.get("status") == "USER_REQUIRED" and empty:
                errors.append(f"{_text('field_required', lang)}: {_label(field, lang)}")
                continue
            # A customs reference the route says applies, still empty: said
            # once, on the documents that carry the field, and never a
            # refusal — see the note on the texts.
            if field["key"] in customs_route.FIELDS and empty:
                if customs_verdicts is None:
                    customs_verdicts = customs_route.assess(values)
                if customs_verdicts[field["key"]].applies == "yes":
                    warnings.append(_text(f"customs_{field['key']}_applies", lang))
                continue
            # A field that promises a shape has to have that shape. Until now
            # only emptiness was checked, so "72" or "7208 51" simply ended up on
            # an official waybill as the NHM code.
            pattern = field.get("pattern")
            if pattern and not empty and not re.fullmatch(pattern, str(value).strip()):
                errors.append(
                    f"{_text('field_format', lang)}: {_label(field, lang)}"
                    + (f" — {_localised(field.get('format_hint'), lang)}"
                       if field.get("format_hint") else "")
                )

    profile = document.get("dg_profile")
    if profile:
        entries = dangerous_goods or []
        if document.get("dg_only") and not entries:
            errors.append(_text("no_dg_lines", lang))
        required_fields = DG_PROFILE_REQUIRED.get(profile, DG_BASE_REQUIRED)
        for entry in entries:
            for product in entry.get("products", []):
                # Substances ADR does not admit for carriage block the export.
                if is_transport_forbidden(str(product.get("un_number") or "")):
                    errors.append(
                        f"{_text('dg_forbidden', lang)}: {_un_prefixed(product.get('un_number'))}"
                    )
                # A quantity whose unit nobody wrote down. The land regimes count
                # in the unit of 1.1.3.6.3 — litres, net kilograms, or a gas's
                # water capacity — and the three are not interchangeable.
                # `adr_quantity` rather than `total_quantity` so that class 1
                # stays out of this by itself: its quantity is the net explosive
                # mass, which 5.4.1.2.1 (a) states in kilograms by definition.
                if profile in ("ADR", "RID", "ADN"):
                    amount, unit = adr_quantity(product)
                    if amount is not None and not unit:
                        warnings.append(_text("quantity_without_unit", lang).format(
                            un=_un_prefixed(product.get("un_number"))))
                # Sea and air prescribe the language of the name: IMDG 5.4.1.4.1
                # permits English, French or Spanish and IATA DGR 8.1.2.1 only
                # English. Whoever first drew up a German road document keeps the
                # German name standing in the field.
                #
                # That is no reason to refuse the export: the language belongs to
                # the document and not to the consignment, and EMCargo knows
                # which name has to be here. It puts it there itself and reports
                # it — blocking would only make the user retype what the app
                # already knew.
                english, replaced = resolve_for_profile(product, profile, lang)
                if replaced:
                    warnings.append(
                        f"{_text('dg_name_language', lang)}: "
                        f"{_un_prefixed(product.get('un_number'))} — "
                        f"{replaced} → {english}"
                    )
                missing = [f for f in required_fields if not str(product.get(f) or "").strip()]
                if missing:
                    position = entry.get("vehicle") or entry.get("line_id") or "?"
                    errors.append(
                        f"{_text('dg_missing', lang)} '{position}': {', '.join(missing)}"
                    )

        # The full compliance check runs at the export itself as well. The panel
        # in the wizard is an aid; the frontend must never be the only place
        # where this is enforced — a stale or never-refreshed screen result must
        # not produce a document.
        if entries:
            from app.services.dg.compliance import check_compliance

            outcome = check_compliance(entries, [profile], language)
            # If this export computes with a rule set that has run out and has
            # not been replaced, that belongs on the document and not only on the
            # screen — a document outlives the session it was made in.
            for finding in outcome.get("rule_set_warnings", []) or []:
                warnings.append(f"{finding['rule']}: {finding['message']}")
            # RID 5.4.1.1.1 (j) and ADN 5.4.1.1.1 (j) are provisions *about the
            # transport document*, so the one place they must never stop at is
            # the screen. Both answer with a list; the informational half — the
            # number this application has already put in the description line —
            # deliberately does not travel, or every CIM would grow a line
            # saying that nothing is outstanding.
            for finding in outcome.get("imdg_segregation", []) + outcome.get(
                "adr_mixed_loading", []
            ) + outcome.get("iata_segregation", []) + outcome.get(
                "rid_transport_document", []
            ) + outcome.get("adn_stabilisation", []) + outcome.get(
                "technical_name_findings", []) + outcome.get("imdg_source_findings", []):
                text = f"{finding.get('rule')}: {finding.get('message')}"
                if finding.get("severity") == "error":
                    errors.append(text)
                elif finding.get("severity") == "warning":
                    warnings.append(text)
            for q in outcome.get("q_values", []) or []:
                if q.get("status") == "exceeded":
                    # Q above 1 means the combination may not fly like that.
                    errors.append(
                        f"IATA 5.0.2.11: Q = {q.get('q_value')} (> 1)"
                        + (f" — {q.get('position')}" if q.get("position") else "")
                    )
                elif q.get("status") in {"incomplete", "not_checked"}:
                    warnings.append(str(q.get("note") or "Q incomplete"))
            # And if no Q was computed at all, that belongs on it too: a check
            # that did not run looked on the document like a check that passed.
            q_status = outcome.get("q_check_status")
            if q_status and q_status.get("status") in {"not_checked", "incomplete"}:
                warnings.append(f"IATA DGR 5.0.2.11: {q_status['message']}")
            adn = outcome.get("adn_exemption")
            if adn and profile == "ADN":
                if adn.get("status") == "incomplete":
                    warnings.append(
                        "ADN 1.1.3.6.1: " + _text("adr_points_incomplete", lang)
                    )
                elif adn.get("status") in {"not_exempt", "above_threshold"}:
                    over = ", ".join(
                        f"class {item['class']} {item['carried']} kg > {item['limit']} kg"
                        for item in adn.get("over_class_limit") or []
                    )
                    detail = over or (
                        f"{adn.get('total_gross_mass_kg')} kg > {adn.get('threshold')} kg"
                    )
                    warnings.append(
                        "ADN 1.1.3.6.1: " + _text("adr_exemption_lost", lang).format(detail=detail)
                    )
            points = outcome.get("adr_points")
            if points and profile in {"ADR", "RID", "ADN"}:
                status = points.get("status")
                if status == "incomplete":
                    warnings.append("ADR 1.1.3.6: " + _text("adr_points_incomplete", lang))
                elif status in {"above_threshold", "not_exempt"}:
                    # Not forbidden, but the 1.1.3.6 exemption lapses and with
                    # it the full requirements apply: training, ADR vehicle,
                    # orange plates, fire extinguishers. Whoever still saw
                    # "exemption possible" on screen has to read this here.
                    total = points.get("total_points")
                    threshold = points.get("threshold")
                    detail = (
                        f"{total} > {threshold}" if status == "above_threshold"
                        else ", ".join(points.get("category0_products") or [])
                    )
                    warnings.append(
                        "ADR 1.1.3.6: "
                        + _text("adr_exemption_lost", lang).format(detail=detail)
                    )
            # The tunnel code of column (15) is on the document per 5.4.1.1.1 (k)
            # and, until v1.50.0, evaluated nowhere. What the driver needs is the
            # code of the *whole load* (8.6.3.2), and that never appeared on the
            # sheet at all — only the per-substance codes it is derived from.
            for entry in entries:
                for product in entry.get("products", []):
                    un = str(product.get("un_number") or "").strip()
                    if not un:
                        continue
                    rows = get_un_entries(un)
                    if rows and not english_name_is_usable(rows[0]):
                        warnings.append(
                            _text("no_english_name", lang).format(un=un)
                        )
            tunnel = outcome.get("adr_tunnel")
            if tunnel and profile == "ADR" and tunnel.get("status") not in {None, "not_checked"}:
                warnings.append(f"ADR 8.6.3: {tunnel['message']}")

            # v1.66.0 works out whether the goods may travel in a tank at all and
            # showed the answer on screen only. A prohibition that reaches the
            # panel and not the paper is a prohibition the person filling in the
            # document never meets.
            # Bulk admission answers road and rail alike since v1.96.0 and the
            # provision carries its own regime name: a refusal reaches the
            # paper, and a permission travels too — the BK/VC codes and the AP
            # conditions are exactly what the loader at the ramp checks the
            # container against.
            if profile in ("ADR", "RID"):
                for item in (outcome.get("adr_bulk_admission") or {}).get("items", []):
                    warnings.append(f"{item.get('provision', 'ADR 7.3.1.1')}: "
                                    f"{item['message']}")

            if profile == "ADR":
                for item in (outcome.get("adr_tank_admission") or {}).get("items", []):
                    if not item.get("permitted"):
                        warnings.append(f"ADR {item.get('provision', '3.2.1')}: "
                                        f"{item['message']}")

                # And whether *this* tank may carry it (4.3), which since
                # v1.82.0 was answered on screen only — the same failure the
                # admission check had before it. A tank that does not fit, a
                # fit the books could not settle and a fit that carries a
                # condition all belong on the paper; a plain fit does not, or
                # every document would grow a line saying nothing happened.
                for item in (outcome.get("adr_tank_fit") or {}).get("items", []):
                    if item.get("fit") in ("does_not_fit", "cannot_be_assessed",
                                           "fits_under_condition"):
                        warnings.append(f"ADR 4.3: {item['message']}")
                    if item.get("provisions_note") and item.get("fit") != "fits":
                        warnings.append(str(item["provisions_note"]))

                # How full it may be (4.3.2.2). The formula is the answer where
                # the densities are missing, and that is exactly the kind of
                # condition the person filling in the document has to carry
                # out: table A does not hold the density, so nobody but the
                # consignor can close it.
                for item in (outcome.get("adr_filling_degree") or {}).get("items", []):
                    warnings.append(f"ADR {item.get('provision', '4.3.2.2')}: "
                                    f"{item['message']}")
                    if item.get("status") == "needs_input" and item.get("formula"):
                        warnings.append(str(item["formula"]))

            # The inland waterway answers two questions the road does not, and
            # until now it answered them into the void: the separation in the
            # holds and the signals the vessel must show were computed for every
            # ADN consignment and appeared on no document. The signals in
            # particular belong here — which cones a vessel shows is a fact
            # about the voyage that the papers travel with.
            if profile == "ADN":
                # 5.4.1.1.2 (h): six numbered remarks of column (20) put
                # information *in the transport document* — 3, 17, 22, 39 (b),
                # 42 and 47. Their text lives in 3.2.3.1 and is not held here,
                # so the document says which remark asks, rather than guessing
                # at what it asks for.
                from app.services.dg.database import adn_table_c_rows

                document_remarks = {"3", "17", "22", "39", "42", "47"}
                for entry in entries:
                    for product in entry.get("products", []):
                        if str(product.get("carriage_mode") or "") != "tank":
                            continue
                        un = str(product.get("un_number") or "").strip()
                        asked = sorted({
                            number
                            for row in adn_table_c_rows(un)
                            for number in re.findall(
                                r"\d+", str(row.get("remarks") or ""))
                            if number in document_remarks})
                        if asked:
                            warnings.append(
                                _text("adn_remark_information", lang).format(
                                    un=un, remarks=", ".join(asked)))

                # Whether the goods may travel that way at all comes first: a
                # carriage the ADN does not permit is not a remark under the cone
                # count, it is the reason there is no voyage to paper.
                admission = outcome.get("adn_carriage_admission") or {}
                for item in admission.get("items", []):
                    if not item.get("permitted"):
                        warnings.append(f"ADN {item.get('provision', '3.2.1')}: "
                                        f"{item['message']}")
                    # The vessel type of table C column (6) is a fact about the
                    # voyage the papers travel with, like the cones are.
                    if item.get("vessel_message"):
                        warnings.append(str(item["vessel_message"]))
                for key in ("single_reading_note", "conditions_note",
                            "not_assessed"):
                    if admission.get(key):
                        warnings.append(str(admission[key]))

                signals = outcome.get("adn_signals") or {}
                separation = outcome.get("adn_hold_separation") or {}
                # A cargo tank load is not on a dry cargo vessel, so chapter 7.1
                # has no answer to put here. Saying which chapter does is worth a
                # line; a cone count of nothing would be a wrong one.
                for source in (signals, separation):
                    if source.get("mode_note"):
                        warnings.append(str(source["mode_note"]))
                        break
                if signals.get("status") not in {None, "not_checked",
                                                 "not_available_for_mode"}:
                    warnings.append(
                        f"ADN {signals.get('provision', '7.1.5.0.1')}: "
                        f"{signals.get('message', '')}".strip()
                    )
                    if signals.get("highest_wins"):
                        # The ranking provision differs per vessel: 7.1.5.0.4
                        # for holds, 7.2.5.0.2 for tank vessels — and the
                        # result's own provision says which world this is.
                        ranking = ("7.2.5.0.2"
                                   if str(signals.get("provision", "")).startswith("7.2")
                                   else "7.1.5.0.4")
                        warnings.append(f"ADN {ranking}: {signals['highest_wins']}")
                for source in (signals, outcome.get("adn_hold_separation") or {}):
                    # Named per substance rather than as a blanket disclaimer:
                    # "not settled for UN 1203" is something a consignor can act
                    # on, "the cone rules were not assessed" is not.
                    if source.get("not_assessed"):
                        warnings.append(str(source["not_assessed"]))
                for finding in (outcome.get("adn_hold_separation") or {}).get("findings", []):
                    warnings.append(f"ADN {finding['provision']}: {finding['message']}")

    if document["key"] == "vgm" and str(values.get("vgm_method")) == "method2":
        components = [
            values.get("cargo_mass_kg"),
            values.get("packaging_mass_kg"),
            values.get("pallets_mass_kg"),
            values.get("securing_mass_kg"),
            values.get("container_tare_kg"),
        ]
        try:
            total = sum(float(v) for v in components if v not in (None, ""))
            vgm = float(values.get("vgm_kg") or 0)
            if vgm and abs(total - vgm) > max(0.005 * vgm, 1.0):
                warnings.append(
                    f"{_text('vgm_mismatch', lang)}: {vgm} kg ≠ {round(total, 2)} kg"
                )
        except (TypeError, ValueError):
            pass

    # The EDI notification has needs no section lists: a UN number and a
    # class per product, at least one mass, and dangerous goods at all.
    if document.get("exporter") == "iftdgn":
        errors.extend(iftdgn.problems(values, dangerous_goods, lang))

    return errors, warnings


def _un_prefixed(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return text if text.upper().startswith(("UN", "ID")) else f"UN {text}"


def _dg_description(product: dict[str, Any], profile: str, values: dict[str, Any],
                    lang: str = "") -> str:
    """The official description line of ADR/RID/ADN 5.4.1.1.1, for the form.

    This used to be a second rendering of the same provision, and it drifted
    exactly as a second rendering does: the subsidiary label models of (c) and
    the hazard identification number of RID (j) would have reached the wizard
    and the stowage plan while the CMR and the CIM went on without them. The
    one builder does the composing; what is left here is the part that is
    genuinely the form's — the manually entered tunnel code, and the fact that
    a form column holds the description alone, without the package counts the
    form has columns of its own for.
    """
    return description_line(
        {k: v for k, v in product.items()
         if k not in ("quantity_packages", "type_of_package",
                      "net_mass_liters_per_package", "adr_total_quantity",
                      "net_explosive_mass")},
        profile, lang, values)


def _dg_rows(profile: str, entry: dict[str, Any], product: dict[str, Any], values: dict[str, Any], lang: str):
    """Row values for the DG table, in the column order of the form concerned."""
    if profile == "IATA_DGR":
        quantity_parts = [
            str(product.get("quantity_packages") or "").strip(),
            str(product.get("type_of_package") or "").strip(),
        ]
        quantity = " × ".join(p for p in quantity_parts if p)
        per_package = str(product.get("net_mass_liters_per_package") or "").strip()
        if per_package:
            quantity = f"{quantity}, {per_package}" if quantity else per_package
        psn = resolve_for_profile(product, profile, lang)[0]
        technical = str(product.get("technical_name") or "").strip()
        if technical:
            psn = f"{psn} ({technical})"
        hazard = str(product.get("class") or "")
        subsidiary = str(product.get("subsidiary_risks") or "").strip()
        if subsidiary:
            hazard = f"{hazard} ({subsidiary})"
        return [
            _un_prefixed(product.get("un_number")),
            psn,
            hazard,
            product.get("packing_group", ""),
            quantity,
            product.get("packing_instruction", ""),
            product.get("authorization", "") or product.get("eq_lq_points", ""),
        ]
    if profile in {"ADR", "RID", "ADN"}:
        return [
            _dg_description(product, profile, values, lang),
            product.get("quantity_packages", ""),
            product.get("type_of_package", ""),
            product.get("net_mass_liters_per_package", ""),
            product.get("gross_mass_per_package", ""),
            product.get("additional_information", ""),
        ]
    if profile == "IMDG":
        psn = resolve_for_profile(product, profile, lang)[0]
        technical = str(product.get("technical_name") or "").strip()
        if technical:
            psn = f"{psn} ({technical})"
        hazard = str(product.get("class") or "")
        subsidiary = str(product.get("subsidiary_risks") or "").strip()
        if subsidiary:
            hazard = f"{hazard} ({subsidiary})"
        packages_parts = [
            str(product.get("quantity_packages") or "").strip(),
            str(product.get("type_of_package") or "").strip(),
        ]
        return [
            _un_prefixed(product.get("un_number")),
            psn,
            hazard,
            product.get("packing_group", ""),
            product.get("marine_pollutant", ""),
            product.get("flashpoint", ""),
            product.get("ems_code", ""),
            " × ".join(p for p in packages_parts if p),
            product.get("net_mass_liters_per_package", ""),
            product.get("gross_mass_per_package", ""),
        ]
    return [entry.get("vehicle") or entry.get("line_id")] + [
        product.get(field, "") for field in DG_PRODUCT_FIELDS
    ]


def _dg_headers(profile: str, lang: str) -> list[str]:
    if profile == "IATA_DGR":
        return _text("iata_dg_headers", lang)
    if profile in {"ADR", "RID", "ADN"}:
        return _text("adr_dg_headers", lang)
    if profile == "IMDG":
        return _text("imdg_dg_headers", lang)
    return _text("dg_headers", lang)


def _dims(line: dict[str, Any]) -> str:
    parts = [line.get("length_cm"), line.get("width_cm"), line.get("height_cm")]
    if all(p in (None, "") for p in parts):
        return ""
    return " × ".join(str(p) if p not in (None, "") else "—" for p in parts)


def export_document(
    document_key: str,
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> Path:
    document = get_document(document_key)
    if document is None:
        raise ValueError(f"Unknown document: {document_key}")
    lang = _lang(language)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = document.get("short_label", {}).get(lang, document_key)[:31]

    title_font = Font(bold=True, size=15)
    section_font = Font(bold=True, size=11, color="FFFFFF")
    section_fill = PatternFill("solid", fgColor="1E3A5F")
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill("solid", fgColor="D9E2EC")
    note_font = Font(italic=True, size=9, color="666666")
    status_font = Font(italic=True, size=10, color="1E3A5F")
    thin = Side(style="thin", color="B0BEC5")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")

    ws.column_dimensions["A"].width = 42
    for col in range(2, 16):
        ws.column_dimensions[get_column_letter(col)].width = 22

    row = 1
    ws.cell(row, 1, _label(document, lang)).font = title_font
    row += 1
    issue = pick(document.get("issue_status"), lang)
    if issue:
        cell = ws.cell(row, 1, f"{_text('status', lang)}: {issue}")
        cell.font = status_font
        row += 1
    ws.cell(row, 1, f"{_text('generated_with', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}").font = note_font
    row += 2

    for section in resolve_sections(document):
        fields = section.get("fields", [])
        visible = [
            f
            for f in fields
            if f.get("status") != "CONDITIONAL"
            or not f.get("condition")
            or condition_met(f.get("condition"), values)
            or str(values.get(f["key"], "")).strip() != ""
        ]
        filled_or_relevant = [
            f
            for f in visible
            if str(values.get(f["key"], "")).strip() != ""
            or f.get("status") in {"USER_REQUIRED", "CARRIER_PROVIDED", "OPERATIONAL", "SIGNATURE_REQUIRED"}
        ]
        if not filled_or_relevant:
            continue
        cell = ws.cell(row, 1, _label(section, lang))
        cell.font = section_font
        cell.fill = section_fill
        ws.cell(row, 2).fill = section_fill
        row += 1
        for field in filled_or_relevant:
            value = values.get(field["key"], "")
            status = field.get("status")
            if field.get("type") == "select" and value not in (None, ""):
                value = _option_label(field, value, lang)
            if status == "SIGNATURE_REQUIRED":
                if field.get("type") == "checkbox":
                    value = (
                        _text("confirmed", lang)
                        if str(value).lower() in {"true", "1", "yes", "ja"}
                        else _text("not_confirmed", lang)
                    )
                else:
                    value = f"[{_text('not_prefilled', lang)}]"
            elif str(value).strip() == "":
                if status == "CARRIER_PROVIDED":
                    value = f"[{_text('carrier_provided', lang)}]"
                elif status == "OPERATIONAL":
                    value = f"[{_text('operational', lang)}]"
                else:
                    value = ""
            label_cell = ws.cell(row, 1, _label(field, lang))
            label_cell.alignment = wrap
            label_cell.border = border
            value_cell = ws.cell(row, 2, value if value != "" else None)
            value_cell.alignment = wrap
            value_cell.border = border
            if isinstance(value, str) and value.startswith("["):
                value_cell.font = note_font
            row += 1
        row += 1

    included = [ln for ln in lines if ln.get("include", True)]
    if included:
        cell = ws.cell(row, 1, _text("goods", lang))
        cell.font = section_font
        cell.fill = section_fill
        row += 1
        headers = _text("line_headers", lang)
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row, col, header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
        row += 1
        total_weight = 0.0
        total_volume = 0.0
        for i, line in enumerate(included, start=1):
            weight = line.get("weight_total_kg")
            volume = line.get("transport_volume_m3")
            total_weight += weight or 0
            total_volume += volume or 0
            cells = [
                i,
                line.get("output_description") or line.get("description"),
                line.get("quantity"),
                line.get("unit"),
                weight,
                volume,
                _dims(line),
            ]
            for col, value in enumerate(cells, start=1):
                cell = ws.cell(row, col, value)
                cell.border = border
                if col == 2:
                    cell.alignment = wrap
            row += 1
        cell = ws.cell(row, 1, _text("totals", lang))
        cell.font = header_font
        ws.cell(row, 5, round(total_weight, 2)).font = header_font
        ws.cell(row, 6, round(total_volume, 3)).font = header_font
        row += 2

    if document.get("dg_profile") and dangerous_goods:
        profile = document["dg_profile"]
        cell = ws.cell(row, 1, f"{_text('dg_table', lang)} ({profile})")
        cell.font = section_font
        cell.fill = section_fill
        row += 1
        headers = _dg_headers(profile, lang)
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row, col, header)
            cell.font = header_font
            cell.fill = header_fill
            cell.border = border
            cell.alignment = wrap
        row += 1
        for entry in dangerous_goods:
            for product in entry.get("products", []):
                for col, value in enumerate(_dg_rows(profile, entry, product, values, lang), start=1):
                    cell = ws.cell(row, col, value)
                    cell.border = border
                    cell.alignment = wrap
                row += 1
        row += 1

    fixed_texts = document.get("fixed_texts") or []
    if fixed_texts:
        cell = ws.cell(row, 1, _text("fixed_texts", lang))
        cell.font = section_font
        cell.fill = section_fill
        row += 1
        for item in fixed_texts:
            text = pick(item, lang)
            cell = ws.cell(row, 1, text)
            cell.alignment = wrap
            cell.border = border
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
            ws.row_dimensions[row].height = max(28, 13 * (len(text) // 110 + 1))
            row += 1
        row += 1

    legal = pick(document.get("legal_reference"), lang)
    if legal:
        cell = ws.cell(row, 1, f"{_text('legal_reference', lang)}: {legal}")
        cell.font = note_font
        cell.alignment = wrap
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
        row += 1

    note = pick(document.get("signature_note"), lang)
    if note:
        cell = ws.cell(row, 1, note)
        cell.font = note_font
        cell.alignment = wrap
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
        row += 1

    row += 1
    cell = ws.cell(row, 1, _text("disclaimer", lang))
    cell.font = note_font
    cell.alignment = wrap
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=7)
    ws.row_dimensions[row].height = 40

    fd, temp_name = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    out_path = Path(temp_name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    wb.save(out_path)
    return out_path
