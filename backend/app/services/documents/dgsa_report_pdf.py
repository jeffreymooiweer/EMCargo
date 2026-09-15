"""The safety adviser's annual report as paper.

Drawn in EMCargo's own style on the installation's page frame, in the
order the DVSA template gives the report: company and adviser, risk rating,
summary, activities, incidents, training, high consequence goods, the
transport table, practices and procedures, the class 7 block where class 7
was carried, the additional points, comments, who prepared it — with the
adviser's saved signature — then the figures the history counted as an
appendix, and the DGSA1 to DGSA21 checklist last, each line naming the
section of the report that answers it.

Unanswered stays visibly unanswered. A blank cell is the adviser's to fill;
the application never fills it for them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from app.core.languages import pick
from app.pdf_style import table_commands
from app.services.dgsa_form import checklist_rows
from app.services.documents.frame import branded_document
from app.services.documents.pdf_render import (
    BRAND,
    _fields_table,
    _grid_table,
    _output_path,
    _p,
    _section_header,
    _signature_block,
    _styles,
)

TEXT = {
    "title": {"nl": "Jaarverslag veiligheidsadviseur", "en": "DGSA Annual Report", "de": "Jahresbericht des Gefahrgutbeauftragten", "fr": "Rapport annuel du conseiller à la sécurité"},
    "subtitle": {"nl": "voor het vervoer van gevaarlijke goederen — ADR 1.8.3.3", "en": "for the Carriage of Dangerous Goods — as required by ADR 1.8.3.3", "de": "für die Beförderung gefährlicher Güter — nach ADR 1.8.3.3", "fr": "pour le transport de marchandises dangereuses — au titre du 1.8.3.3 de l'ADR"},
    "year": {"nl": "Verslagjaar", "en": "Reporting period (year)", "de": "Berichtsjahr", "fr": "Période (année)"},
    "scope": {"nl": "Bereik", "en": "Scope", "de": "Umfang", "fr": "Portée"},
    "question": {"nl": "Vraag", "en": "Question", "de": "Frage", "fr": "Question"},
    "answer": {"nl": "Antwoord", "en": "Answer", "de": "Antwort", "fr": "Réponse"},
    "not_answered": {"nl": "— niet ingevuld —", "en": "— not answered —", "de": "— nicht ausgefüllt —", "fr": "— non renseigné —"},
    "class": {"nl": "Klasse", "en": "Class", "de": "Klasse", "fr": "Classe"},
    "operations": {"nl": "Handelingen", "en": "Type of transport operations", "de": "Vorgänge", "fr": "Opérations"},
    "band": {"nl": "Hoeveelheid (band)", "en": "Quantity (band)", "de": "Menge (Stufe)", "fr": "Quantité (tranche)"},
    "counted": {"nl": "Geteld uit de historie", "en": "Counted from the history", "de": "Aus der Historie gezählt", "fr": "Compté depuis l'historique"},
    "packages": {"nl": "colli", "en": "packages", "de": "Versandstücke", "fr": "colis"},
    "designs": {"nl": "Verpakkingsontwerpen (klasse 7)", "en": "Package designs (Class 7)", "de": "Bauarten (Klasse 7)", "fr": "Modèles de colis (classe 7)"},
    "signature": {"nl": "Handtekening van de adviseur", "en": "Advisor's signature", "de": "Unterschrift des Beauftragten", "fr": "Signature du conseiller"},
    "responsible_signature": {"nl": "Handtekening verantwoordelijke persoon (bevestiging van ontvangst)", "en": "Signature of responsible person (acknowledgement of receipt)", "de": "Unterschrift der verantwortlichen Person (Empfangsbestätigung)", "fr": "Signature de la personne responsable (accusé de réception)"},
    "appendix": {"nl": "Bijlage — de cijfers uit de historie", "en": "Appendix — the figures from the history", "de": "Anhang — die Zahlen aus der Historie", "fr": "Annexe — les chiffres de l'historique"},
    "generated": {"nl": "Cijfers geteld door {brand} op", "en": "Figures counted by {brand} on", "de": "Zahlen gezählt von {brand} am", "fr": "Chiffres comptés par {brand} le"},
    "no_class": {"nl": "Geen gevaarlijke goederen bewaard in dit jaar.", "en": "No dangerous goods kept in this year.", "de": "Keine gefährlichen Güter in diesem Jahr aufbewahrt.", "fr": "Aucune marchandise dangereuse conservée cette année."},
}



def _t(key: str, lang: str) -> str:
    return pick(TEXT[key], lang)


def _answer_text(value: Any, labels: dict[str, str], lang: str) -> tuple[str, str]:
    """(answer, details) for a yes/no question, blank stays blank."""
    if not isinstance(value, dict):
        return _t("not_answered", lang), ""
    answer = str(value.get("answer") or "")
    return (labels.get(answer) or _t("not_answered", lang)), str(value.get("details") or "")


def _yes_no_table(questions: list[dict[str, Any]], answers: dict[str, Any], labels: dict[str, str],
                  styles: dict, width: float, lang: str) -> Table:
    rows = []
    for question in questions:
        answer, details = _answer_text(answers.get(question["key"]), labels, lang)
        rows.append([question["text"], answer, details])
    header = [_t("question", lang), _t("answer", lang), labels.get("details", "")]
    return _grid_table(header, rows, styles, width, col_weights=[.50, .14, .36])


def _text_rows(questions: list[dict[str, Any]], answers: dict[str, Any], lang: str) -> list[tuple[str, Any]]:
    rows: list[tuple[str, Any]] = []
    for question in questions:
        value = answers.get(question["key"])
        kind = question["kind"]
        if kind in ("text", "textarea", "date"):
            rows.append((question["text"], value or _t("not_answered", lang)))
        elif kind == "choice":
            label = question.get("option_labels", {}).get(value or "", "")
            rows.append((question["text"], label or _t("not_answered", lang)))
        elif kind == "multi":
            chosen = [question.get("option_labels", {}).get(v, v) for v in (value or [])]
            rows.append((question["text"], ", ".join(chosen) or _t("not_answered", lang)))
    return rows


def _transport_table(question: dict[str, Any], value: dict[str, Any], styles: dict, width: float, lang: str) -> Table:
    op_labels = question.get("operation_labels", {})
    design_labels = question.get("package_design_labels", {})
    header = [_t("class", lang), _t("operations", lang), _t("band", lang), _t("counted", lang)]
    rows = []
    for cls in question.get("classes", []):
        row = (value or {}).get(cls) or {}
        ops = ", ".join(op_labels.get(o, o) for o in row.get("operations") or [])
        if row.get("other"):
            ops = f"{ops} ({row['other']})" if ops else row["other"]
        counted = []
        if row.get("quantity_kg"):
            counted.append(f"{float(row['quantity_kg']):,.1f} kg")
        if row.get("quantity_l"):
            counted.append(f"{float(row['quantity_l']):,.1f} L")
        if row.get("packages"):
            counted.append(f"{int(row['packages'])} {_t('packages', lang)}")
        if row.get("shipments"):
            counted.append(f"{int(row['shipments'])}×")
        band = row.get("band") or ""
        if cls == "7" and row.get("designs"):
            band = f"{band} · " + ", ".join(design_labels.get(d, d) for d in row["designs"])
        rows.append([cls, ops, band, "; ".join(counted)])
    return _grid_table(header, rows, styles, width, col_weights=[.10, .42, .22, .26])


def _incidents_table(question: dict[str, Any], rows: list[dict[str, Any]], styles: dict, width: float, lang: str):
    columns = question.get("columns", {})
    header = [columns.get("date", "Date"), columns.get("place", "Place"), columns.get("description", "Description")]
    body = [[r.get("date", ""), r.get("place", ""), r.get("description", "")] for r in rows or []]
    if not body:
        body = [["", "", _t("not_answered", lang)]]
    return _grid_table(header, body, styles, width, col_weights=[.16, .26, .58])


def render_dgsa_report(report: dict[str, Any], definition: dict[str, Any], answers: dict[str, Any],
                       signature_png: bytes | None = None, brand_name: str = "EMCargo") -> Path:
    lang = report.get("language", "nl")
    styles = _styles()
    out_path = _output_path()
    title = _t("title", lang)
    doc = branded_document(out_path, f"{title} {report['year']}", lang)
    width = doc.width
    labels = definition.get("answer_labels", {})
    by_section: dict[str, list[dict[str, Any]]] = {}
    for question in definition["questions"]:
        by_section.setdefault(question["section"], []).append(question)
    classes_present = {str(c["class"]).split(".")[0] for c in report.get("by_class") or []}

    story: list[Any] = [
        _p(title, styles["title"]),
        _p(_t("subtitle", lang), styles["status"]),
        Spacer(1, 4),
        _fields_table([
            (_t("year", lang), report["year"]),
            (_t("scope", lang), report.get("scope", "")),
        ], styles, width),
        Spacer(1, 8),
    ]

    for section in definition["sections"]:
        key = section["key"]
        only = section.get("only_with_class")
        questions = by_section.get(key, [])
        answered_here = any(isinstance(answers.get(q["key"]), dict) and answers[q["key"]].get("answer")
                            for q in questions)
        if only and only not in classes_present and not answered_here:
            continue
        block: list[Any] = [_section_header(section["title"], styles, width)]
        if section.get("intro"):
            block.append(_p(section["intro"], styles["note"]))
        yes_no = [q for q in questions if q["kind"] in ("yesno", "yesnona")]
        plain = [q for q in questions if q["kind"] in ("text", "textarea", "date", "choice", "multi")]
        if plain:
            block.append(_fields_table(_text_rows(plain, answers, lang), styles, width))
        if yes_no:
            block.append(_yes_no_table(yes_no, answers, labels, styles, width, lang))
        for question in questions:
            if question["kind"] == "incidents":
                block.append(_p(question["text"], styles["label"]))
                block.append(_incidents_table(question, answers.get(question["key"]) or [], styles, width, lang))
            elif question["kind"] == "transport_table":
                block.append(_p(question["text"], styles["label"]))
                block.append(_p(question.get("band_note", ""), styles["note"]))
                block.append(_transport_table(question, answers.get(question["key"]) or {}, styles, width, lang))
        if key == "prepared":
            if signature_png:
                block.extend(_signature_block(signature_png, styles, lang))
            else:
                block.append(Spacer(1, 18))
                block.append(_p(_t("signature", lang) + ": ______________________________", styles["note"]))
            block.append(Spacer(1, 18))
            block.append(_p(_t("responsible_signature", lang) + ": ______________________________", styles["note"]))
        block.append(Spacer(1, 8))
        story.extend(block)

    # Appendix: what the history counted.
    story.append(PageBreak())
    story.append(_section_header(_t("appendix", lang), styles, width))
    story.append(_p(f"{pick(TEXT['generated'], lang).replace('{brand}', brand_name)} "
                    f"{report.get('generated_at', '')[:10]}", styles["meta"]))
    story.append(_p(report.get("counted_note", ""), styles["note"]))
    totals = report.get("totals", {})
    story.append(_fields_table([
        (pick({"nl": "Zendingen", "en": "Shipments", "de": "Sendungen", "fr": "Expéditions"}, lang), totals.get("shipments", 0)),
        (pick({"nl": "Met gevaarlijke goederen", "en": "With dangerous goods", "de": "Mit gefährlichen Gütern", "fr": "Avec marchandises dangereuses"}, lang), totals.get("with_dangerous_goods", 0)),
        (pick({"nl": "Hoeveelheid (kg) / (L)", "en": "Quantity (kg) / (L)", "de": "Menge (kg) / (L)", "fr": "Quantité (kg) / (L)"}, lang),
         f"{totals.get('quantity_kg', 0):,.1f} kg / {totals.get('quantity_l', 0):,.1f} L"),
    ], styles, width))
    story.append(Spacer(1, 6))
    if report.get("by_class"):
        header = [_t("class", lang),
                  pick({"nl": "Zendingen", "en": "Shipments", "de": "Sendungen", "fr": "Expéditions"}, lang),
                  pick({"nl": "Stoffen", "en": "Substances", "de": "Stoffe", "fr": "Matières"}, lang), "kg", "L"]
        story.append(_grid_table(header, [[c["class"], c["shipments"], c["products"], c["quantity_kg"], c["quantity_l"]]
                                          for c in report["by_class"]], styles, width))
        story.append(Spacer(1, 6))
        header = ["UN", pick({"nl": "Juiste vervoersnaam", "en": "Proper shipping name", "de": "Offizielle Benennung", "fr": "Désignation officielle"}, lang),
                  _t("class", lang), "PG",
                  pick({"nl": "Zendingen", "en": "Shipments", "de": "Sendungen", "fr": "Expéditions"}, lang), "kg", "L"]
        story.append(_grid_table(header, [[u["un_number"], u["name"], u["class"], u["packing_group"], u["shipments"],
                                           u["quantity_kg"], u["quantity_l"]] for u in report["by_un_number"]], styles, width))
    else:
        story.append(_p(_t("no_class", lang), styles["note"]))
    if report.get("adr_points"):
        story.append(Spacer(1, 6))
        story.append(_fields_table([(row["label"], row["shipments"]) for row in report["adr_points"]], styles, width))

    # The checklist, last.
    story.append(PageBreak())
    checklist = definition["checklist"]
    story.append(_section_header(checklist["title"], styles, width))
    story.append(_p(definition.get("source", ""), styles["disclaimer"]))
    story.append(_p(report.get("source", ""), styles["disclaimer"]))
    story.append(Spacer(1, 4))
    rows = checklist_rows(report, answers, lang)
    header = ["", checklist["columns"]["item"], checklist["columns"]["answer"], checklist["columns"]["section"]]
    data = [[_p(h, styles["cellh"]) for h in header]]
    additional_started = False
    for row in rows:
        if row["additional"] and not additional_started:
            data.append([_p(checklist["additional_heading"], styles["cellh"]), "", "", ""])
            additional_started = True
        data.append([_p(row["code"], styles["cell"]), _p(row["text"], styles["cell"]),
                     _p(row["answer"], styles["cell"]), _p(row["section"], styles["cell"])])
    t = Table(data, colWidths=[width * .12, width * .50, width * .16, width * .22],
              repeatRows=1, splitByRow=1, splitInRow=1, hAlign="LEFT")
    style = table_commands()
    for index, row in enumerate(data):
        if index and row[1] == "":
            style += [("BACKGROUND", (0, index), (-1, index), BRAND), ("SPAN", (0, index), (-1, index))]
    t.setStyle(TableStyle(style))
    story.append(t)

    doc.build(story)
    return out_path
