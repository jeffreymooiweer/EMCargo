"""The equipment sheet: what has to be aboard the transport unit (ADR 8.1.4/8.1.5).

Derived since v1.53.0 and shown on screen since — and the person who needs it
is standing at the open door of a cab with a torch in one hand, not at a
browser. 8.1.5.1 chooses the equipment by the hazard label numbers of the goods
loaded and points at the transport document to identify them, which is exactly
what this application holds; so the list is printed, one line per item with the
provision beside it, as a checklist with nothing ticked.

Nothing here is a finding. EMCargo cannot see a vehicle, so it can never
establish that a wheel chock is in the cab — the sheet says so in the same
words the panel does, and the fire extinguisher line carries the three mass
rows of 8.1.4.1 because the maximum permissible mass of the unit is the
vehicle's property, not the consignment's.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.platypus import Spacer

from app.core.languages import normalise, pick
from app.services.documents import brand
from app.services.documents.frame import branded_document
from app.services.dg.compliance import check_adr_equipment
from app.services.documents.pdf_render import (
    _fields_table,
    _grid_table,
    _output_path,
    _p,
    _section_header,
    _styles,
)

TEXT: dict[str, dict[str, str]] = {
    "title": {
        "nl": "Uitrustingsblad (ADR 8.1.4 / 8.1.5)",
        "en": "Equipment sheet (ADR 8.1.4 / 8.1.5)",
        "de": "Ausrüstungsblatt (ADR 8.1.4 / 8.1.5)",
        "fr": "Feuille d'équipement (ADR 8.1.4 / 8.1.5)",
    },
    "generated": {
        "nl": "Opgesteld met {brand} op", "en": "Drawn up with {brand} on",
        "de": "Erstellt mit {brand} am", "fr": "Établi avec {brand} le",
    },
    "consignment": {"nl": "Zending", "en": "Consignment", "de": "Sendung",
                    "fr": "Envoi"},
    "vehicle": {
        "nl": "Voertuig of transporteenheid", "en": "Vehicle or transport unit",
        "de": "Fahrzeug oder Beförderungseinheit",
        "fr": "Véhicule ou unité de transport",
    },
    "labels": {
        "nl": "Gevaarsetiketten van de lading (grondslag, 8.1.5.1)",
        "en": "Hazard labels of the load (the basis, 8.1.5.1)",
        "de": "Gefahrzettel der Ladung (Grundlage, 8.1.5.1)",
        "fr": "Étiquettes de danger du chargement (fondement, 8.1.5.1)",
    },
    "items": {
        "nl": "Uitrusting — afvinken bij het voertuig, niet vooraf",
        "en": "Equipment — tick at the vehicle, not beforehand",
        "de": "Ausrüstung — am Fahrzeug abhaken, nicht vorab",
        "fr": "Équipement — à cocher au véhicule, pas d'avance",
    },
    "provision": {"nl": "Bepaling", "en": "Provision", "de": "Vorschrift",
                  "fr": "Disposition"},
    "no_dg": {
        "nl": "Geen gevaarlijke goederen in deze zending; 8.1.5 vraagt dan geen "
              "aanvullende uitrusting.",
        "en": "No dangerous goods in this consignment; 8.1.5 then asks no "
              "additional equipment.",
        "de": "Keine gefährlichen Güter in dieser Sendung; 8.1.5 verlangt dann "
              "keine zusätzliche Ausrüstung.",
        "fr": "Pas de marchandises dangereuses dans cet envoi ; le 8.1.5 "
              "n'exige alors aucun équipement supplémentaire.",
    },
}


def _lang_of(language: str) -> str:
    return normalise(language)


def _t(key: str, lang: str) -> str:
    return brand.fill(pick(TEXT[key], lang))


def render_equipment_sheet(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> Path:
    """The 8.1.4/8.1.5 list as paper, from the check that already derives it."""
    lang = _lang_of(language)
    result = check_adr_equipment(list(dangerous_goods or []), lang)
    styles = _styles()
    out_path = _output_path()
    doc = branded_document(out_path, _t("title", lang), lang)
    width = doc.width
    story: list[Any] = [
        _p(_t("title", lang), styles["title"]),
        _p(f"{_t('generated', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
           styles["meta"]),
        Spacer(1, 6),
        _fields_table([
            (_t("consignment", lang),
             values.get("reference") or values.get("order_reference") or ""),
            (_t("vehicle", lang), values.get("vehicle_registration") or ""),
            (_t("labels", lang), ", ".join(result.get("labels") or [])),
        ], styles, width),
        Spacer(1, 6),
    ]
    items = result.get("items") or []
    if items:
        story.append(_section_header(_t("items", lang), styles, width))
        story.append(_grid_table(
            ["", _t("provision", lang), ""],
            [["[   ]", item.get("rule", ""), item.get("text", "")]
             for item in items],
            styles, width, col_weights=[.075, .19, .735]))
    else:
        story.append(_p(_t("no_dg", lang), styles["meta"]))
    if result.get("note"):
        story.append(Spacer(1, 4))
        story.append(_p(str(result["note"]), styles["meta"]))
    doc.build(story)
    return out_path
