"""The placarding sheet: what goes on the outside of the vehicle (ADR 5.3).

EMCargo has derived chapter 5.3 since v1.53.0 and shown the answer on
screen. On screen is where it stayed. The person who needs it is standing at
the back of a trailer with plates and placards in his hand, and a compliance
panel in a browser is not a thing you hold while doing that.

So this is that answer as a sheet: the large labels and the orange plates, each
against the provision that asked for it, in the language the documents are
drawn up in. No new regulation is read here — every line comes from
``check_adr_placarding``, which read 5.3 out of the official text. What this
file adds is paper.

Two things it deliberately does not do. It does not draw the placards: a
diamond printed on a laser printer is not a placard, and a sheet that looks
like one invites exactly that mistake. And it does not turn "check this
yourself" into an instruction — where the check could not settle a question,
because table A gives no label or no hazard number, the sheet says so in the
same words the panel does.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.platypus import Spacer

from app.services.dg.compliance import (
    check_adn_exemption,
    check_adn_placarding,
    check_adr_placarding,
    check_imdg_placarding,
    check_rid_placarding,
)
from app.services.documents.frame import branded_document
from app.services.documents.pdf_render import (
    _fields_table,
    _grid_table,
    _output_path,
    _p,
    _section_header,
    _styles,
)

#: Everything the sheet says about itself, in the four languages the interface
#: speaks. The findings themselves arrive already translated: the compliance
#: layer is asked in the document's language.
TEXT: dict[str, dict[str, str]] = {
    "title": {
        "nl": "Bebordings- en etiketteringsblad (ADR 5.3)",
        "en": "Placarding and marking sheet (ADR 5.3)",
        "de": "Bezettelungs- und Kennzeichnungsblatt (ADR 5.3)",
        "fr": "Feuille de placardage et de signalisation (ADR 5.3)",
    },
    "title_adn": {
        "nl": "Bebordings- en etiketteringsblad (ADN 5.3)",
        "en": "Placarding and marking sheet (ADN 5.3)",
        "de": "Bezettelungs- und Kennzeichnungsblatt (ADN 5.3)",
        "fr": "Feuille de placardage et de signalisation (ADN 5.3)",
    },
    "title_rid": {
        "nl": "Bebordings- en etiketteringsblad (RID 5.3)",
        "en": "Placarding and marking sheet (RID 5.3)",
        "de": "Bezettelungs- und Kennzeichnungsblatt (RID 5.3)",
        "fr": "Feuille de placardage et de signalisation (RID 5.3)",
    },
    "title_imdg": {
        "nl": "Bebordings- en kenmerkingsblad (IMDG 5.3)",
        "en": "Placarding and marking sheet (IMDG 5.3)",
        "de": "Bezettelungs- und Kennzeichnungsblatt (IMDG 5.3)",
        "fr": "Feuille de placardage et de marquage (IMDG 5.3)",
    },
    "wagon": {
        "nl": "Wagen of grote container", "en": "Wagon or large container",
        "de": "Wagen oder Großcontainer", "fr": "Wagon ou grand conteneur",
    },
    "container": {
        "nl": "Laadeenheid (container, oplegger of transporttank)",
        "en": "Cargo transport unit (container, semi-trailer or portable tank)",
        "de": "Beförderungseinheit (Container, Sattelanhänger oder Tank)",
        "fr": "Engin de transport (conteneur, semi-remorque ou citerne mobile)",
    },
    "ctu": {
        "nl": "Vervoerseenheid aan boord (container, voertuig of wagen)",
        "en": "Cargo transport unit on board (container, vehicle or wagon)",
        "de": "Beförderungseinheit an Bord (Container, Fahrzeug oder Wagen)",
        "fr": "Engin de transport à bord (conteneur, véhicule ou wagon)",
    },
    "generated": {
        "nl": "Opgesteld met EMCargo op", "en": "Drawn up with EMCargo on",
        "de": "Erstellt mit EMCargo am", "fr": "Établi avec EMCargo le",
    },
    "consignment": {
        "nl": "Zending", "en": "Consignment", "de": "Sendung", "fr": "Envoi",
    },
    "vehicle": {
        "nl": "Voertuig of transporteenheid", "en": "Vehicle or transport unit",
        "de": "Fahrzeug oder Beförderungseinheit", "fr": "Véhicule ou unité de transport",
    },
    "goods": {
        "nl": "Wat er aan boord is", "en": "What is on board",
        "de": "Was an Bord ist", "fr": "Ce qui est à bord",
    },
    "goods_headers": {
        "nl": "UN|Benaming|Klasse|Etiketten|Gevaarsnr.|Vervoerswijze",
        "en": "UN|Name|Class|Labels|Hazard no.|Mode of carriage",
        "de": "UN|Benennung|Klasse|Zettel|Gefahrnr.|Beförderungsart",
        "fr": "ONU|Désignation|Classe|Étiquettes|N° de danger|Mode de transport",
    },
    "placards": {
        "nl": "Grote etiketten (5.3.1)", "en": "Placards (5.3.1)",
        "de": "Großzettel (5.3.1)", "fr": "Plaques-étiquettes (5.3.1)",
    },
    "marks": {
        "nl": "Oranje borden en kenmerken (5.3.2 en verder)",
        "en": "Orange plates and marks (5.3.2 onwards)",
        "de": "Orangefarbene Tafeln und Kennzeichen (5.3.2 ff.)",
        "fr": "Panneaux orange et marques (5.3.2 et suivants)",
    },
    "none_required": {
        "nl": "Geen grote etiketten vereist voor deze zending.",
        "en": "No placards required for this consignment.",
        "de": "Für diese Sendung sind keine Großzettel erforderlich.",
        "fr": "Aucune plaque-étiquette n'est requise pour cet envoi.",
    },
    "scope_packages": {
        "nl": "Berekend voor vervoer in colli.",
        "en": "Computed for carriage in packages.",
        "de": "Berechnet für die Beförderung in Versandstücken.",
        "fr": "Calculé pour le transport en colis.",
    },
    "scope_tanks": {
        "nl": "Berekend voor vervoer in een tank of los gestort.",
        "en": "Computed for carriage in a tank or in bulk.",
        "de": "Berechnet für die Beförderung in einem Tank oder in loser Schüttung.",
        "fr": "Calculé pour le transport en citerne ou en vrac.",
    },
    "not_a_placard": {
        "nl": "Dit blad is een werkinstructie, geen etiket. De grote etiketten en oranje "
              "borden zelf moeten voldoen aan de afmetingen, kleuren en uitvoering van "
              "5.3.1.7 en 5.3.2.2; een uitdraai vervangt ze niet.",
        "en": "This sheet is a working instruction, not a label. The placards and orange "
              "plates themselves must meet the dimensions, colours and construction of "
              "5.3.1.7 and 5.3.2.2; a printout does not replace them.",
        "de": "Dieses Blatt ist eine Arbeitsanweisung, kein Zettel. Die Großzettel und "
              "orangefarbenen Tafeln selbst müssen den Abmessungen, Farben und der "
              "Ausführung nach 5.3.1.7 und 5.3.2.2 entsprechen; ein Ausdruck ersetzt sie "
              "nicht.",
        "fr": "Cette feuille est une instruction de travail, pas une étiquette. Les "
              "plaques-étiquettes et les panneaux orange doivent eux-mêmes respecter les "
              "dimensions, couleurs et l'exécution des 5.3.1.7 et 5.3.2.2 ; une impression "
              "ne les remplace pas.",
    },
    "exempt": {
        "nl": "Deze zending blijft onder de vrijstellingsgrens van 1.1.3.6; 5.3 vraagt dan "
              "geen bebording. Controleer of de zending werkelijk onder die grens blijft.",
        "en": "This consignment stays under the exemption threshold of 1.1.3.6, so 5.3 asks "
              "for no placarding. Check that the consignment really stays under it.",
        "de": "Diese Sendung bleibt unter der Freistellungsgrenze von 1.1.3.6; 5.3 verlangt "
              "dann keine Bezettelung. Prüfen Sie, ob die Sendung wirklich darunter bleibt.",
        "fr": "Cet envoi reste sous le seuil d'exemption du 1.1.3.6 ; le 5.3 n'exige alors "
              "aucun placardage. Vérifiez que l'envoi reste réellement sous ce seuil.",
    },
}


def _t(key: str, language: str) -> str:
    block = TEXT[key]
    return block.get(language) or block["en"]


def render_placarding_sheet(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    regime: str = "ADR",
) -> Path:
    """The sheet, from the answer the compliance layer already computes.

    ``regime`` picks whose chapter 5.3 answers: the road's
    (`check_adr_placarding`, about the vehicle), the rail's, the inland
    waterway's (`check_adn_placarding`, about the cargo transport units that
    come on board) or the sea's (`check_imdg_placarding`, about the unit that
    goes on the ship). The registry offers each under its own document key, so
    a consignment is never handed another mode's answer — which for sea would
    be a container placarded on two sides instead of four.
    """
    lang = _lang_of(language)
    entries = list(dangerous_goods or [])
    if regime == "ADN":
        exemption = check_adn_exemption(entries, lang)
        result = check_adn_placarding(
            entries, lang, exemption_status=exemption.get("status"))
        title = _t("title_adn", lang)
    elif regime == "RID":
        result = check_rid_placarding(entries, lang)
        title = _t("title_rid", lang)
    elif regime == "IMDG":
        result = check_imdg_placarding(entries, lang)
        title = _t("title_imdg", lang)
    else:
        result = check_adr_placarding(entries, lang)
        title = _t("title", lang)
    styles = _styles()
    out_path = _output_path()
    doc = branded_document(out_path, title, lang)
    width = doc.width
    story: list[Any] = [
        _p(title, styles["title"]),
        _p(f"{_t('generated', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
           styles["meta"]),
        _p(_t("scope_tanks" if result.get("scope") == "tanks_or_bulk"
              else "scope_packages", lang), styles["meta"]),
        Spacer(1, 6),
    ]
    if result.get("mode_note"):
        # A cargo tank consignment: 5.3's units are not its question, and the
        # sheet says whose question it is instead of printing an empty answer.
        story.append(_p(result["mode_note"], styles["fixed"]))

    unit_key = {"ADN": "ctu", "RID": "wagon",
                "IMDG": "container"}.get(regime, "vehicle")
    header = [(_t("consignment", lang), values.get("reference") or values.get("order_reference") or ""),
              (_t(unit_key, lang),
               values.get("vehicle_registration")
               or values.get("licence_plate") or values.get("vehicle") or "")]
    story.append(_fields_table([(label, value) for label, value in header], styles, width))
    story.append(Spacer(1, 6))

    rows = _goods_rows(entries)
    if rows:
        story.extend([
            _section_header(_t("goods", lang), styles, width),
            _grid_table(_t("goods_headers", lang).split("|"), rows, styles, width,
                        col_weights=[.10, .37, .09, .10, .13, .21]),
            Spacer(1, 6),
        ])

    story.append(_section_header(_t("placards", lang), styles, width))
    if result.get("status") == "exempt":
        story.append(_p(_t("exempt", lang), styles["fixed"]))
    placards = result.get("placards") or []
    if not placards:
        story.append(_p(_t("none_required", lang), styles["fixed"]))
    for placard in placards:
        story.append(_p(_bullet(placard), styles["fixed"]))
        story.append(Spacer(1, 3))
    story.append(Spacer(1, 4))

    story.append(_section_header(_t("marks", lang), styles, width))
    for mark in result.get("marks") or []:
        story.append(_p(_bullet(mark), styles["fixed"]))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 8))
    story.append(_p(_t("not_a_placard", lang), styles["disclaimer"]))
    if result.get("source"):
        story.append(_p(result["source"], styles["disclaimer"]))
    doc.build(story)
    return out_path


def _bullet(finding: dict[str, Any]) -> str:
    """One finding, with the provision that asked for it in front."""
    provision = str(finding.get("provision") or "").strip()
    message = str(finding.get("message") or "").strip()
    return f"{provision} — {message}" if provision else message


def _goods_rows(entries: list[dict[str, Any]]) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for entry in entries:
        for product in entry.get("products") or []:
            if product.get("transport_forbidden"):
                continue
            rows.append([
                product.get("un_number") or "",
                product.get("proper_shipping_name") or "",
                product.get("class") or "",
                product.get("labels") or "",
                product.get("hazard_number") or "",
                product.get("carriage_mode") or "packages",
            ])
    return rows


def _lang_of(language: str) -> str:
    value = str(language or "nl").strip().lower()[:2]
    return value if value in ("nl", "en", "de", "fr") else "nl"
