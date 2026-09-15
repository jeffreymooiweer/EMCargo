"""Two documents about documents: the packing certificate and the on-board list.

**The container/vehicle packing certificate (ADR 5.4.2).** Where carriage of
dangerous goods in a container precedes a sea voyage, a certificate in
accordance with section 5.4.2 of the IMDG Code must be provided to the maritime
carrier by those responsible for packing the container. The ADR prints the
IMDG's nine declarations in its own footnote to 5.4.2 — read in the official
Dutch edition on printed pages 1002-1004 — which is what makes this document
buildable from a free official text. The application had it as a single
checkbox; a checkbox is not a document anyone can hand to a carrier.

Nothing on it is pre-ticked. Every declaration is a statement about what
happened at the ramp — that the container was clean, that damaged packages
stayed behind, that drums stand upright — and a certificate this application
had already ticked would claim knowledge it cannot have. That is the 8.6.3
pattern: the model is served, the answers belong to the people present.

**The on-board documents list (ADR 8.1.2 / ADN 8.1.2).** Both regimes list the
papers that must travel — in the driver's cab, on the vessel. Some of them this
application produces; most of them it never can, and naming those next to the
generated ones is the difference between "here are your documents" and "here is
everything the regulation asks, and this is the part you must bring yourself".
Read in the official Dutch ADR (printed page 1431) and the Dutch ADN edition
(8.1.2.1/8.1.2.2).
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.platypus import Spacer

from app.core.languages import normalise, pick
from app.services.documents import brand
from app.services.documents.frame import branded_document
from app.services.documents.pdf_render import (
    _fields_table,
    _grid_table,
    _output_path,
    _p,
    _section_header,
    _styles,
)

TEXT: dict[str, dict[str, str]] = {
    # --- the packing certificate -------------------------------------------
    "pc_title": {
        "nl": "Container-/voertuigbeladingscertificaat (ADR 5.4.2 / IMDG 5.4.2)",
        "en": "Container/vehicle packing certificate (ADR 5.4.2 / IMDG 5.4.2)",
        "de": "Container-/Fahrzeugpackzertifikat (ADR 5.4.2 / IMDG 5.4.2)",
        "fr": "Certificat d'empotage du conteneur ou du véhicule (ADR 5.4.2 / IMDG 5.4.2)",
    },
    "pc_when": {
        "nl": "Vereist wanneer vervoer van gevaarlijke goederen in een container "
              "aan een zeereis voorafgaat. Niet vereist voor transporttanks.",
        "en": "Required where carriage of dangerous goods in a container precedes "
              "a sea voyage. Not required for portable tanks.",
        "de": "Erforderlich, wenn der Beförderung gefährlicher Güter in einem "
              "Container eine Seereise folgt. Für ortsbewegliche Tanks nicht "
              "erforderlich.",
        "fr": "Exigé lorsque le transport de marchandises dangereuses en conteneur "
              "précède un parcours maritime. Non exigé pour les citernes mobiles.",
    },
    "pc_unit": {
        "nl": "Container-/voertuig-/eenheidsidentificatienummer(s)",
        "en": "Container/vehicle/unit identification number(s)",
        "de": "Container-/Fahrzeug-/Einheitsnummer(n)",
        "fr": "Numéro(s) d'identification du conteneur, du véhicule ou de l'unité",
    },
    "pc_declare": {
        "nl": "Ondergetekende, verantwoordelijk voor de belading, verklaart dat de "
              "belading is uitgevoerd in overeenstemming met de volgende "
              "voorwaarden (IMDG 5.4.2.1) — kruis elk punt pas aan nadat het is "
              "vastgesteld:",
        "en": "The undersigned, responsible for the packing, certifies that the "
              "operation was carried out in accordance with the following "
              "conditions (IMDG 5.4.2.1) — tick each item only once it has been "
              "established:",
        "de": "Der Unterzeichnete, für die Beladung verantwortlich, erklärt, dass "
              "die Beladung gemäß den folgenden Bedingungen durchgeführt wurde "
              "(IMDG 5.4.2.1) — jeden Punkt erst nach Feststellung ankreuzen:",
        "fr": "Le soussigné, responsable de l'empotage, certifie que l'opération a "
              "été effectuée conformément aux conditions suivantes "
              "(IMDG 5.4.2.1) — ne cocher chaque point qu'après constat :",
    },
    "pc_nothing_prefilled": {
        "nl": "Door {brand} niet vooraf ingevuld: elke verklaring gaat over wat "
              "bij de belading is vastgesteld, en dat kan deze applicatie niet "
              "zien.",
        "en": "Not pre-filled by {brand}: every declaration concerns what was "
              "established at packing, which this application cannot see.",
        "de": "Von {brand} nicht vorausgefüllt: jede Erklärung betrifft, was "
              "bei der Beladung festgestellt wurde, und das kann diese Anwendung "
              "nicht sehen.",
        "fr": "Non prérempli par {brand} : chaque déclaration porte sur ce qui "
              "a été constaté à l'empotage, ce que cette application ne peut pas "
              "voir.",
    },
    "pc_signature": {
        "nl": "Naam en functie van de ondertekenaar / handtekening / datum",
        "en": "Name and status of signatory / signature / date",
        "de": "Name und Stellung des Unterzeichners / Unterschrift / Datum",
        "fr": "Nom et qualité du signataire / signature / date",
    },
    "pc_single_document": {
        "nl": "5.4.2.2: de functies van vervoersdocument en beladingscertificaat "
              "mogen in één document worden verenigd; zo niet, dan worden de "
              "documenten aan elkaar gehecht.",
        "en": "5.4.2.2: the functions of the transport document and this "
              "certificate may be incorporated into a single document; if not, "
              "the documents are attached to one another.",
        "de": "5.4.2.2: Die Funktionen des Beförderungspapiers und dieses "
              "Zertifikats dürfen in einem einzigen Dokument vereinigt werden; "
              "andernfalls sind die Dokumente aneinander zu heften.",
        "fr": "5.4.2.2 : les fonctions du document de transport et du présent "
              "certificat peuvent être réunies en un seul document ; à défaut, "
              "les documents sont attachés l'un à l'autre.",
    },
    # --- the on-board list --------------------------------------------------
    "ob_title_adr": {
        "nl": "Boorddocumentenlijst — transporteenheid (ADR 8.1.2)",
        "en": "On-board documents list — transport unit (ADR 8.1.2)",
        "de": "Mitzuführende Dokumente — Beförderungseinheit (ADR 8.1.2)",
        "fr": "Documents de bord — unité de transport (ADR 8.1.2)",
    },
    "ob_title_adn": {
        "nl": "Boorddocumentenlijst — schip (ADN 8.1.2)",
        "en": "On-board documents list — vessel (ADN 8.1.2)",
        "de": "Mitzuführende Dokumente — Schiff (ADN 8.1.2)",
        "fr": "Documents de bord — bateau (ADN 8.1.2)",
    },
    "ob_from_app": {
        "nl": "Door {brand} voor deze zending opgesteld",
        "en": "Drawn up by {brand} for this consignment",
        "de": "Von {brand} für diese Sendung erstellt",
        "fr": "Établis par {brand} pour cet envoi",
    },
    "ob_bring": {
        "nl": "Wettelijk vereist en niet uit deze applicatie te verkrijgen — zelf "
              "meenemen",
        "en": "Required by law and not obtainable from this application — bring "
              "yourself",
        "de": "Gesetzlich erforderlich und nicht aus dieser Anwendung zu beziehen "
              "— selbst mitführen",
        "fr": "Exigés par la réglementation et non fournis par cette application "
              "— à apporter soi-même",
    },
    "ob_note": {
        "nl": "Deze lijst is een hulpmiddel en geen verklaring van volledigheid; "
              "andere wettelijke voorschriften kunnen meer documenten vereisen "
              "(8.1.2.1, aanhef).",
        "en": "This list is an aid and not a statement of completeness; other "
              "legal requirements may demand further documents (the opening "
              "words of 8.1.2.1).",
        "de": "Diese Liste ist ein Hilfsmittel und keine Vollständigkeitserklärung; "
              "andere Rechtsvorschriften können weitere Dokumente verlangen "
              "(8.1.2.1, Eingangssatz).",
        "fr": "Cette liste est une aide et non une attestation d'exhaustivité ; "
              "d'autres prescriptions peuvent exiger des documents "
              "supplémentaires (préambule du 8.1.2.1).",
    },
    "ob_document": {"nl": "Document", "en": "Document", "de": "Dokument",
                    "fr": "Document"},
    "ob_basis": {"nl": "Grondslag", "en": "Basis", "de": "Grundlage",
                 "fr": "Fondement"},
    "ob_present": {"nl": "Aanwezig", "en": "Present", "de": "Vorhanden",
                   "fr": "Présent"},
}

#: The nine declarations of IMDG 5.4.2.1, as the ADR's own footnote prints
#: them (official Dutch edition, printed page 1003). Facts the regulation
#: prescribes word for word are document content; the four languages here
#: render the same nine conditions.
DECLARATIONS: list[dict[str, str]] = [
    {"nl": "De container/het voertuig was schoon, droog en ogenschijnlijk geschikt voor ontvangst van de goederen.",
     "en": "The container/vehicle was clean, dry and apparently fit to receive the goods.",
     "de": "Der Container/das Fahrzeug war sauber, trocken und augenscheinlich geeignet, die Güter aufzunehmen.",
     "fr": "Le conteneur ou le véhicule était propre, sec et apparemment en état de recevoir les marchandises."},
    {"nl": "Colli die volgens de van toepassing zijnde scheidingseisen gescheiden moeten worden, zijn niet samen in of op de container/het voertuig geladen (tenzij goedgekeurd door de bevoegde autoriteit).",
     "en": "Packages which need to be segregated in accordance with applicable segregation requirements have not been packed together onto or in the container/vehicle (unless approved by the competent authority).",
     "de": "Versandstücke, die nach den geltenden Trennvorschriften zu trennen sind, wurden nicht zusammen in oder auf den Container/das Fahrzeug verladen (sofern nicht von der zuständigen Behörde genehmigt).",
     "fr": "Les colis à séparer conformément aux prescriptions de séparation applicables n'ont pas été chargés ensemble dans ou sur le conteneur ou le véhicule (sauf approbation de l'autorité compétente)."},
    {"nl": "Alle colli zijn uitwendig op schade geïnspecteerd en alleen gave colli zijn geladen.",
     "en": "All packages have been externally inspected for damage, and only sound packages have been loaded.",
     "de": "Alle Versandstücke wurden äußerlich auf Beschädigung geprüft; nur unbeschädigte Versandstücke wurden verladen.",
     "fr": "Tous les colis ont été inspectés extérieurement et seuls des colis en bon état ont été chargés."},
    {"nl": "Vaten zijn rechtop gestuwd (tenzij anders toegestaan door de bevoegde autoriteit) en alle goederen zijn deugdelijk geladen en zo nodig vastgezet met materiaal dat past bij de vervoerswijze(n).",
     "en": "Drums have been stowed in an upright position (unless otherwise authorized by the competent authority) and all goods properly loaded and, where necessary, adequately braced with securing material to suit the mode(s) of transport.",
     "de": "Fässer wurden aufrecht gestaut (sofern die zuständige Behörde nichts anderes zulässt), und alle Güter wurden ordnungsgemäß verladen und, soweit erforderlich, mit für die Beförderungsart(en) geeignetem Material gesichert.",
     "fr": "Les fûts ont été arrimés debout (sauf autorisation contraire de l'autorité compétente) et toutes les marchandises correctement chargées et, si nécessaire, convenablement calées avec un matériel adapté au(x) mode(s) de transport."},
    {"nl": "Losgestorte goederen zijn gelijkmatig over de container/het voertuig verdeeld.",
     "en": "Goods loaded in bulk have been evenly distributed within the container/vehicle.",
     "de": "In loser Schüttung verladene Güter wurden gleichmäßig im Container/Fahrzeug verteilt.",
     "fr": "Les marchandises en vrac ont été également réparties dans le conteneur ou le véhicule."},
    {"nl": "Voor zendingen met goederen van klasse 1 (behalve subklasse 1.4) is de container/het voertuig constructief geschikt overeenkomstig IMDG 7.4.6.",
     "en": "For consignments including goods of class 1 other than division 1.4, the container/vehicle is structurally serviceable in accordance with IMDG 7.4.6.",
     "de": "Bei Sendungen mit Gütern der Klasse 1 (außer Unterklasse 1.4) ist der Container/das Fahrzeug baulich geeignet gemäß IMDG 7.4.6.",
     "fr": "Pour les envois comprenant des marchandises de la classe 1 autres que la division 1.4, le conteneur ou le véhicule est structurellement adapté conformément au 7.4.6 du Code IMDG."},
    {"nl": "De container/het voertuig en de colli zijn, waar vereist, deugdelijk gemerkt en geëtiketteerd.",
     "en": "The container/vehicle and packages are properly marked, labelled and placarded, as appropriate.",
     "de": "Der Container/das Fahrzeug und die Versandstücke sind, soweit erforderlich, ordnungsgemäß gekennzeichnet und bezettelt.",
     "fr": "Le conteneur ou le véhicule et les colis sont correctement marqués, étiquetés et placardés, selon le cas."},
    {"nl": "Wanneer stoffen met verstikkingsgevaar voor koeling of conditionering worden gebruikt (zoals droogijs, UN 1845, of stikstof of argon, sterk gekoeld, vloeibaar), is de container/het voertuig uitwendig gekenmerkt overeenkomstig IMDG 5.5.3.6.",
     "en": "When substances presenting a risk of asphyxiation are used for cooling or conditioning purposes (such as dry ice, UN 1845, or nitrogen or argon, refrigerated liquid), the container/vehicle is externally marked in accordance with IMDG 5.5.3.6.",
     "de": "Werden erstickend wirkende Stoffe zu Kühl- oder Konditionierungszwecken verwendet (wie Trockeneis, UN 1845, oder Stickstoff oder Argon, tiefgekühlt, flüssig), ist der Container/das Fahrzeug außen gemäß IMDG 5.5.3.6 gekennzeichnet.",
     "fr": "Lorsque des matières présentant un risque d'asphyxie sont utilisées à des fins de réfrigération ou de conditionnement (comme la neige carbonique, UN 1845, ou l'azote ou l'argon liquides réfrigérés), le conteneur ou le véhicule porte extérieurement la marque prévue au 5.5.3.6 du Code IMDG."},
    {"nl": "Voor elke zending gevaarlijke goederen in de container/het voertuig is een vervoersdocument als bedoeld in IMDG 5.4.1 ontvangen.",
     "en": "A dangerous goods transport document, as indicated in IMDG 5.4.1, has been received for each dangerous goods consignment loaded in the container/vehicle.",
     "de": "Für jede im Container/Fahrzeug verladene Sendung gefährlicher Güter wurde ein Beförderungspapier nach IMDG 5.4.1 erhalten.",
     "fr": "Un document de transport de marchandises dangereuses, tel que prévu au 5.4.1 du Code IMDG, a été reçu pour chaque envoi chargé dans le conteneur ou le véhicule."},
]


def _lang_of(language: str) -> str:
    return normalise(language)


def _t(key: str, lang: str) -> str:
    return brand.fill(pick(TEXT[key], lang))


def render_packing_certificate(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> Path:
    """The certificate of 5.4.2, with nothing pre-ticked."""
    lang = _lang_of(language)
    styles = _styles()
    out_path = _output_path()
    doc = branded_document(out_path, _t("pc_title", lang), lang)
    width = doc.width
    story: list[Any] = [
        _p(_t("pc_title", lang), styles["title"]),
        _p(f"{_t('ob_from_app', lang)} — "
           f"{datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["meta"]),
        _p(_t("pc_when", lang), styles["meta"]),
        Spacer(1, 6),
        _fields_table([
            (_t("pc_unit", lang),
             values.get("container_number") or values.get("vehicle_registration")
             or ""),
        ], styles, width),
        Spacer(1, 6),
        _section_header(_t("pc_declare", lang), styles, width),
        _grid_table(
            ["", ""],
            # Empty brackets keep every declaration visibly unconfirmed.
            [["[   ]", pick(item, lang)] for item in DECLARATIONS],
            styles, width, col_weights=[.08, .92]),
        Spacer(1, 4),
        _p(_t("pc_nothing_prefilled", lang), styles["meta"]),
        _p(_t("pc_single_document", lang), styles["meta"]),
        Spacer(1, 10),
        _fields_table([(_t("pc_signature", lang), "")], styles, width),
    ]
    doc.build(story)
    return out_path


#: What must be on board, per regime: (basis, four-language name, made by the
#: application or to be brought). Read from ADR 8.1.2.1/8.1.2.2 (printed page
#: 1431) and ADN 8.1.2.1/8.1.2.2 of the official Dutch edition.
_ADR_ITEMS: list[tuple[str, dict[str, str], bool]] = [
    ("ADR 8.1.2.1 (a) / 5.4.1",
     {"nl": "Vervoersdocumenten voor alle vervoerde gevaarlijke goederen",
      "en": "Transport documents covering all dangerous goods carried",
      "de": "Beförderungspapiere für alle beförderten gefährlichen Güter",
      "fr": "Documents de transport couvrant toutes les marchandises dangereuses"},
     True),
    ("ADR 8.1.2.1 (b) / 5.4.3",
     {"nl": "Schriftelijke instructies (in de cabine, snel beschikbaar)",
      "en": "Instructions in writing (in the cab, readily available)",
      "de": "Schriftliche Weisungen (im Führerhaus, leicht zugänglich)",
      "fr": "Consignes écrites (dans la cabine, à portée de main)"},
     True),
    ("ADR 8.1.2.1 (d) / 1.10.1.4",
     {"nl": "Identiteitsbewijs met foto voor elk bemanningslid",
      "en": "Photo identification for each crew member",
      "de": "Lichtbildausweis für jedes Mitglied der Besatzung",
      "fr": "Pièce d'identité avec photo pour chaque membre d'équipage"},
     False),
    ("ADR 8.1.2.2 (a) / 9.1.3",
     {"nl": "Certificaat van goedkeuring van de transporteenheid, waar vereist",
      "en": "Certificate of approval of the transport unit, where required",
      "de": "Zulassungsbescheinigung der Beförderungseinheit, soweit erforderlich",
      "fr": "Certificat d'agrément de l'unité de transport, lorsqu'il est exigé"},
     False),
    ("ADR 8.1.2.2 (b) / 8.2.1",
     {"nl": "Vakbekwaamheidscertificaat (ADR-certificaat) van de bestuurder",
      "en": "Driver's training certificate (ADR certificate)",
      "de": "Schulungsbescheinigung (ADR-Bescheinigung) des Fahrzeugführers",
      "fr": "Certificat de formation du conducteur (certificat ADR)"},
     False),
    ("ADR 8.1.2.2 (c) / 5.4.1.2.1",
     {"nl": "Kopie van de goedkeuring van de bevoegde autoriteit, waar 5.4.1.2.1 (c)/(d) die voorschrijft",
      "en": "Copy of the competent authority approval, where 5.4.1.2.1 (c)/(d) prescribes one",
      "de": "Kopie der Zulassung der zuständigen Behörde, soweit 5.4.1.2.1 (c)/(d) sie vorschreibt",
      "fr": "Copie de l'agrément de l'autorité compétente, lorsque le 5.4.1.2.1 c)/d) l'exige"},
     False),
]

_ADN_ITEMS: list[tuple[str, dict[str, str], bool]] = [
    ("ADN 8.1.2.1 (b) / 5.4.1",
     {"nl": "Vervoersdocumenten voor alle als lading vervoerde gevaarlijke goederen",
      "en": "Transport documents for all dangerous goods carried as cargo",
      "de": "Beförderungspapiere für alle als Ladung beförderten gefährlichen Güter",
      "fr": "Documents de transport pour toutes les marchandises dangereuses transportées"},
     True),
    ("ADN 8.1.2.1 (c) / 5.4.3",
     {"nl": "Schriftelijke instructies",
      "en": "Instructions in writing",
      "de": "Schriftliche Weisungen",
      "fr": "Consignes écrites"},
     True),
    ("ADN 8.1.2.2 (a) / 7.1.4.11",
     {"nl": "Stuwplan (drogeladingschip)",
      "en": "Stowage plan (dry cargo vessel)",
      "de": "Stauplan (Trockengüterschiff)",
      "fr": "Plan d'arrimage (bateau à cargaison sèche)"},
     True),
    ("ADN 8.1.2.1 (a) / 1.16.1.1",
     {"nl": "Certificaat van goedkeuring van het schip (of het voorlopige van 1.16.1.3)",
      "en": "Vessel's certificate of approval (or the provisional one of 1.16.1.3)",
      "de": "Zulassungszeugnis des Schiffes (oder das vorläufige nach 1.16.1.3)",
      "fr": "Certificat d'agrément du bateau (ou le certificat provisoire du 1.16.1.3)"},
     False),
    ("ADN 8.1.2.1 (d)",
     {"nl": "Een exemplaar van het ADN met het actuele Reglement",
      "en": "A copy of the ADN with its current Regulations annexed",
      "de": "Ein Exemplar des ADN mit der aktuellen Verordnung",
      "fr": "Un exemplaire de l'ADN avec son Règlement à jour"},
     False),
    ("ADN 8.1.2.1 (e)-(g) / 8.1.6-8.1.7",
     {"nl": "Inspectieverklaringen (elektrische inrichtingen, brandblusslangen, speciale uitrusting) en het metingenboek",
      "en": "Inspection certificates (electrical installations, fire-extinguishing hoses, special equipment) and the measurements log",
      "de": "Prüfbescheinigungen (elektrische Einrichtungen, Feuerlöschschläuche, Sonderausrüstung) und das Messbuch",
      "fr": "Attestations d'inspection (installations électriques, tuyaux d'incendie, équipement spécial) et le registre des mesures"},
     False),
    ("ADN 8.1.2.1 (i) / 1.10.1.4",
     {"nl": "Identiteitsbewijs met foto voor ieder bemanningslid",
      "en": "Photo identification for each crew member",
      "de": "Lichtbildausweis für jedes Mitglied der Besatzung",
      "fr": "Pièce d'identité avec photo pour chaque membre d'équipage"},
     False),
    ("ADN 8.2.1.2",
     {"nl": "Verklaring bijzondere kennis van het ADN (ADN-deskundige)",
      "en": "Certificate of special knowledge of the ADN (ADN expert)",
      "de": "Bescheinigung über besondere Kenntnisse des ADN (Sachkundiger)",
      "fr": "Attestation de connaissances particulières de l'ADN (expert ADN)"},
     False),
]


def render_onboard_documents(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    regime: str = "ADR",
) -> Path:
    """The list of 8.1.2, split by who can produce each paper."""
    lang = _lang_of(language)
    items = _ADN_ITEMS if regime.upper() == "ADN" else _ADR_ITEMS
    title = _t("ob_title_adn" if regime.upper() == "ADN" else "ob_title_adr", lang)
    styles = _styles()
    out_path = _output_path()
    doc = branded_document(out_path, title, lang)
    width = doc.width
    header = [_t("ob_present", lang), _t("ob_document", lang),
              _t("ob_basis", lang)]
    made = [["[   ]", pick(name, lang), basis]
            for basis, name, from_app in items if from_app]
    bring = [["[   ]", pick(name, lang), basis]
             for basis, name, from_app in items if not from_app]
    story: list[Any] = [
        _p(title, styles["title"]),
        _p(f"{datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["meta"]),
        Spacer(1, 6),
        _section_header(_t("ob_from_app", lang), styles, width),
        _grid_table(header, made, styles, width, col_weights=[.13, .62, .25]),
        Spacer(1, 6),
        _section_header(_t("ob_bring", lang), styles, width),
        _grid_table(header, bring, styles, width, col_weights=[.13, .62, .25]),
        Spacer(1, 6),
        _p(_t("ob_note", lang), styles["meta"]),
    ]
    doc.build(story)
    return out_path
