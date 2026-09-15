"""The stowage plan of ADN 7.1.4.11.1.

Two readings of the provision, the printed Dutch edition and the English one,
say the same short thing: the boatmaster sets down in a stowage plan which
goods are placed in the individual holds or on deck, and those goods are
described there as 5.4.1.1.1 (a), (b), (c) and (d) describe them in the
transport document. 7.1.4.11.2 adds one relief and one duty: for goods in
containers the container number suffices in the plan, provided the plan carries
an annex listing every container with its number and the description of what is
in it.

So this document is not a drawing and does not pretend to be one. A vessel's
holds have a geometry EMCargo knows nothing about, and a plan that invented
one would be a picture of a ship that does not exist. What the provision asks
for is *which goods are where*, in the words the transport document already
uses — and that is exactly what the application holds.

The descriptions come from ``description_line`` and are not written again here.
That is the point of "as in the transport document": two renderings of one
consignment that drift apart are worse than one rendering used twice.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.platypus import Spacer

from app.services.dg.autofill import description_line
from app.services.documents.frame import branded_document
from app.services.documents.pdf_render import (
    _fields_table,
    _grid_table,
    _output_path,
    _p,
    _section_header,
    _styles,
)

#: What the plan says about itself. The goods' own descriptions arrive from the
#: transport document layer and are not translated here: 5.4.1.1.1 asks for the
#: description the document carries, whatever language that document is in.
TEXT: dict[str, dict[str, str]] = {
    "title": {
        "nl": "Stuwplan (ADN 7.1.4.11.1)",
        "en": "Stowage plan (ADN 7.1.4.11.1)",
        "de": "Stauplan (ADN 7.1.4.11.1)",
        "fr": "Plan d'arrimage (ADN 7.1.4.11.1)",
    },
    "generated": {
        "nl": "Opgesteld met EMCargo op", "en": "Drawn up with EMCargo on",
        "de": "Erstellt mit EMCargo am", "fr": "Établi avec EMCargo le",
    },
    "vessel": {"nl": "Schip", "en": "Vessel", "de": "Schiff", "fr": "Bateau"},
    "voyage": {"nl": "Zending", "en": "Consignment", "de": "Sendung", "fr": "Envoi"},
    "hold": {"nl": "Laadruim", "en": "Hold", "de": "Laderaum", "fr": "Cale"},
    "deck": {"nl": "Aan dek", "en": "On deck", "de": "An Deck", "fr": "Sur le pont"},
    "unassigned": {
        "nl": "Nog geen laadruim opgegeven",
        "en": "No hold given yet",
        "de": "Noch kein Laderaum angegeben",
        "fr": "Aucune cale indiquée",
    },
    "unassigned_note": {
        "nl": "7.1.4.11.1 vraagt per laadruim of dek aan te geven wat erin staat. Vul het "
              "laadruim in bij deze posities; tot dat moment is dit plan onvolledig.",
        "en": "7.1.4.11.1 asks what is in each hold or on deck. Fill in the hold for these "
              "positions; until then this plan is incomplete.",
        "de": "7.1.4.11.1 verlangt die Angabe je Laderaum oder Deck. Tragen Sie für diese "
              "Positionen den Laderaum ein; bis dahin ist dieser Plan unvollständig.",
        "fr": "Le 7.1.4.11.1 demande d'indiquer ce qui se trouve dans chaque cale ou sur le "
              "pont. Renseignez la cale pour ces positions ; d'ici là, ce plan est incomplet.",
    },
    "headers": {
        "nl": "Positie|Omschrijving volgens 5.4.1.1.1 a) t/m d)|Container",
        "en": "Position|Description under 5.4.1.1.1 (a) to (d)|Container",
        "de": "Position|Beschreibung nach 5.4.1.1.1 a) bis d)|Container",
        "fr": "Position|Description selon 5.4.1.1.1 a) à d)|Conteneur",
    },
    "containers": {
        "nl": "Bijlage: containers en hun inhoud (7.1.4.11.2)",
        "en": "Annex: containers and their contents (7.1.4.11.2)",
        "de": "Anlage: Container und ihr Inhalt (7.1.4.11.2)",
        "fr": "Annexe : conteneurs et leur contenu (7.1.4.11.2)",
    },
    "container_headers": {
        "nl": "Containernummer|Laadruim of dek|Omschrijving volgens 5.4.1.1.1 a) t/m d)",
        "en": "Container number|Hold or deck|Description under 5.4.1.1.1 (a) to (d)",
        "de": "Containernummer|Laderaum oder Deck|Beschreibung nach 5.4.1.1.1 a) bis d)",
        "fr": "Numéro du conteneur|Cale ou pont|Description selon 5.4.1.1.1 a) à d)",
    },
    "not_a_drawing": {
        "nl": "Dit plan zegt welke goederen waar staan, zoals 7.1.4.11.1 vraagt. Het is geen "
              "tekening van het schip: de indeling en afmetingen van de laadruimen kent "
              "EMCargo niet.",
        "en": "This plan says which goods are where, as 7.1.4.11.1 asks. It is not a drawing "
              "of the vessel: EMCargo does not know the layout or the dimensions of the "
              "holds.",
        "de": "Dieser Plan nennt, welche Güter wo stehen, wie 7.1.4.11.1 es verlangt. Er ist "
              "keine Zeichnung des Schiffes: Aufteilung und Maße der Laderäume kennt "
              "EMCargo nicht.",
        "fr": "Ce plan indique quelles marchandises se trouvent où, comme le demande le "
              "7.1.4.11.1. Ce n'est pas un dessin du bateau : EMCargo ne connaît ni "
              "l'agencement ni les dimensions des cales.",
    },
    "source": {
        "nl": "ADN 2025, 7.1.4.11.1 en 7.1.4.11.2, gelezen in de Nederlandse en de Engelse "
              "uitgave.",
        "en": "ADN 2025, 7.1.4.11.1 and 7.1.4.11.2, read in the Dutch and the English "
              "edition.",
        "de": "ADN 2025, 7.1.4.11.1 und 7.1.4.11.2, gelesen in der niederländischen und der "
              "englischen Ausgabe.",
        "fr": "ADN 2025, 7.1.4.11.1 et 7.1.4.11.2, lus dans l'édition néerlandaise et "
              "l'édition anglaise.",
    },
}

#: What counts as "on deck" in the four languages a user might type it in. A
#: position on deck is not hold number zero: 7.1.4.11.1 names the two side by
#: side, and the plan keeps them apart.
DECK = {"dek", "deck", "an deck", "auf deck", "pont", "sur le pont", "aan dek"}


def _t(key: str, language: str) -> str:
    block = TEXT[key]
    return block.get(language) or block["en"]


def _lang_of(language: str) -> str:
    value = str(language or "nl").strip().lower()[:2]
    return value if value in ("nl", "en", "de", "fr") else "nl"


def _place(product: dict[str, Any], language: str) -> tuple[int, str]:
    """Where this position goes on the plan, and how it sorts.

    Holds first and in their own numeric order, deck after them, and what has
    no place yet last of all — where it is impossible to miss.
    """
    raw = str(product.get("hold") or "").strip()
    if not raw:
        return (3, _t("unassigned", language))
    if raw.lower() in DECK:
        return (2, _t("deck", language))
    if raw.isdigit():
        return (int(raw) - 1_000_000, f"{_t('hold', language)} {raw}")
    return (1, f"{_t('hold', language)} {raw}")


def render_stowage_plan(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
) -> Path:
    lang = _lang_of(language)
    styles = _styles()
    out_path = _output_path()
    doc = branded_document(out_path, _t("title", lang), lang)
    width = doc.width

    places: dict[tuple[int, str], list[list[str]]] = {}
    containers: list[list[str]] = []
    for entry in dangerous_goods or []:
        for index, product in enumerate(entry.get("products") or [], start=1):
            if product.get("transport_forbidden"):
                continue
            place = _place(product, lang)
            position = f"{entry.get('line_id') or ''}.{index}".strip(".")
            described = description_line(product, "ADN")
            container = str(product.get("container_number") or "").strip()
            places.setdefault(place, []).append([position, described, container])
            if container:
                containers.append([container, place[1], described])

    story: list[Any] = [
        _p(_t("title", lang), styles["title"]),
        _p(f"{_t('generated', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}",
           styles["meta"]),
        Spacer(1, 6),
        _fields_table([
            (_t("vessel", lang), values.get("vessel_name") or ""),
            (_t("voyage", lang), values.get("reference")
             or values.get("order_reference") or ""),
        ], styles, width),
        Spacer(1, 6),
    ]

    headers = _t("headers", lang).split("|")
    for place in sorted(places):
        rows = places[place]
        block = [
            _section_header(place[1], styles, width),
            _grid_table(headers, rows, styles, width, col_weights=[.11, .64, .25]),
        ]
        if place[0] == 3:
            block.append(_p(_t("unassigned_note", lang), styles["note"]))
        block.append(Spacer(1, 6))
        story.extend(block)

    if containers:
        story.extend([
            _section_header(_t("containers", lang), styles, width),
            _grid_table(_t("container_headers", lang).split("|"), containers,
                        styles, width, col_weights=[.24, .18, .58]),
            Spacer(1, 6),
        ])

    story.append(Spacer(1, 6))
    story.append(_p(_t("not_a_drawing", lang), styles["disclaimer"]))
    story.append(_p(_t("source", lang), styles["disclaimer"]))
    doc.build(story)
    return out_path
