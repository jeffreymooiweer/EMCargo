"""Generate clean PDFs for self-designed EMCargo documents with reportlab.

Used for documents without an official fillable form (packing list, delivery
note, IMO MMDGF, VGM, shipping instructions, ADR/ADN). Official fillable forms
(CMR, IATA, CIM) are filled in elsewhere with pypdf and not rebuilt.
"""

import io
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.core.languages import pick
from app.pdf_style import ACCENT, LINE, PALE, BOLD, paragraph_styles, table_commands
from app.services.documents import brand
from app.services.documents.frame import branded_document
from app.services.dg.autofill import adr_category_totals
from app.services.documents.exporter import (
    _dg_headers,
    _dg_rows,
    _dims,
    _label,
    _lang,
    _option_label,
    _text,
    condition_met,
    resolve_sections,
)

BRAND = ACCENT
LIGHT = LINE
GRID = LINE


def _styles() -> dict[str, ParagraphStyle]:
    return paragraph_styles()


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    s = "" if text is None else str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return Paragraph(s, style)


def _section_header(title: str, styles: dict, width: float) -> Paragraph:
    # keepWithNext prevents an isolated heading, without forcing a long table
    # onto a new page or retaining an entire section in one unbreakable block.
    return _p(title, styles["section"])


def _fields_table(rows: list[tuple[str, Any]], styles: dict, width: float) -> Table:
    data = [[_p(label, styles["label"]), _p(value, styles["value"])] for label, value in rows]
    table = Table(data, colWidths=[width * .32, width * .68],
                  splitByRow=1, splitInRow=1, hAlign="LEFT")
    table.setStyle(TableStyle(table_commands(header=False)))
    return table


def _grid_table(header: list[str], rows: list[list[Any]], styles: dict, width: float,
                *, col_weights: list[float] | None = None,
                numeric_columns: tuple[int, ...] = (), summary_last: bool = False) -> Table:
    # Descriptions need more room than counts. Explicit proportions take
    # precedence; other tables use bounded content lengths, never equal-width
    # columns that make a three-character position as wide as its description.
    if col_weights is None:
        col_weights = [max(5, min(45, max(len(str(row[index] or ""))
                       for row in [header, *rows]))) ** .6 for index in range(len(header))]
    if len(col_weights) != len(header) or any(weight <= 0 for weight in col_weights):
        raise ValueError("Each table column needs a positive width weight")
    widths = [width * weight / sum(col_weights) for weight in col_weights]
    right = ParagraphStyle("emcargo_numeric_cell", parent=styles["cell"], alignment=TA_RIGHT)
    total = ParagraphStyle("emcargo_total_cell", parent=styles["cell"], fontName=BOLD)
    total_right = ParagraphStyle("emcargo_total_number", parent=total, alignment=TA_RIGHT)
    has_header = any(header)
    data = [[_p(h, styles["cellh"]) for h in header]] if has_header else []
    for index, row in enumerate(rows):
        last = summary_last and index == len(rows) - 1
        data.append([_p(value, (total_right if last else right) if column in numeric_columns
                        else total if last else styles["cell"]) for column, value in enumerate(row)])
    table = Table(data, colWidths=widths, repeatRows=int(has_header),
                  splitByRow=1, splitInRow=1, hAlign="LEFT")
    commands = table_commands(header=has_header)
    if summary_last and rows:
        commands += [("BACKGROUND", (0, -1), (-1, -1), PALE),
                     ("LINEABOVE", (0, -1), (-1, -1), .8, ACCENT)]
    table.setStyle(TableStyle(commands))
    return table


def _imdg_item(header: list[str], row: list[Any], styles: dict, width: float) -> Table:
    """Keep every IMDG field readable instead of squeezing ten columns on A4.

    The first row identifies the substance and repeats if its details span
    pages. The remaining eight values are paired with their original labels
    in two rows, so a quantity can never lose its column's meaning.
    """
    data = [[[_p(header[0], styles["cellh"]), _p(row[0], styles["cellh"])],
             [_p(header[1], styles["cellh"]), _p(row[1], styles["cellh"])], "", ""]]
    for offset in (2, 6):
        data.append([[_p(label, styles["label"]), _p(value, styles["cell"])]
                     for label, value in zip(header[offset:offset + 4], row[offset:offset + 4])])
    table = Table(data, colWidths=[width / 4] * 4, repeatRows=1,
                  splitByRow=1, splitInRow=1, hAlign="LEFT")
    table.setStyle(TableStyle(table_commands() + [("SPAN", (1, 0), (3, 0))]))
    return table


def _visible_fields(section: dict, values: dict) -> list[dict]:
    out = []
    for field in section.get("fields", []):
        if (
            field.get("status") == "CONDITIONAL"
            and field.get("condition")
            and not condition_met(field.get("condition"), values)
            and str(values.get(field["key"], "")).strip() == ""
        ):
            continue
        keep = str(values.get(field["key"], "")).strip() != "" or field.get("status") in {
            "USER_REQUIRED",
            "CARRIER_PROVIDED",
            "OPERATIONAL",
            "SIGNATURE_REQUIRED",
        }
        if keep:
            out.append(field)
    return out


def _field_display(field: dict, values: dict, lang: str) -> Any:
    value = values.get(field["key"], "")
    status = field.get("status")
    if field.get("type") == "select" and value not in (None, ""):
        value = _option_label(field, value, lang)
    if status == "SIGNATURE_REQUIRED":
        if field.get("type") == "checkbox":
            return _text("confirmed", lang) if str(value).lower() in {"true", "1", "yes", "ja"} else _text("not_confirmed", lang)
        return f"[{_text('not_prefilled', lang)}]"
    if str(value).strip() == "":
        if status == "CARRIER_PROVIDED":
            return f"[{_text('carrier_provided', lang)}]"
        if status == "OPERATIONAL":
            return f"[{_text('operational', lang)}]"
        return ""
    return value


def _output_path() -> Path:
    fd, temp_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    out_path = Path(temp_name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    return out_path


def _signature_block(signature_png: bytes, styles: dict, lang: str) -> list:
    """The consignor's signature as an image above a signature line."""
    with PILImage.open(io.BytesIO(signature_png)) as img:
        ratio = img.height / max(img.width, 1)
    sig_width = min(60 * mm, (22 * mm) / max(ratio, 0.01))
    sig_height = sig_width * ratio
    flowable = Image(io.BytesIO(signature_png), width=sig_width, height=sig_height)
    flowable.hAlign = "LEFT"
    caption = pick(
        {
            "nl": "Handtekening afzender / verantwoordelijke persoon — digitaal geplaatst "
                  "via {brand} op ",
            "en": "Signature of consignor / responsible person — digitally placed via "
                  "{brand} on ",
            "de": "Unterschrift des Absenders / der verantwortlichen Person — digital "
                  "eingefügt über {brand} am ", "fr": "Signature de l'expéditeur ou de la personne responsable — apposée numériquement via {brand} le "},
        lang,
    )
    caption = brand.fill(caption) + datetime.now().strftime("%Y-%m-%d")
    caption_table = Table(
        [[_p(caption, styles["note"])]],
        colWidths=[90 * mm],
        style=TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.black),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
        ]),
    )
    caption_table.hAlign = "LEFT"
    return [Spacer(1, 8), flowable, caption_table]


def render_document_pdf(
    document: dict[str, Any],
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    language: str = "nl",
    signature_png: bytes | None = None,
    card_link_base: str | None = None,
) -> Path:
    lang = _lang(language)
    styles = _styles()
    out_path = _output_path()
    doc = branded_document(out_path, _label(document, lang), lang)
    width = doc.width
    story: list = []

    story.append(_p(_label(document, lang), styles["title"]))
    issue = pick(document.get("issue_status"), lang)
    if issue:
        story.append(_p(f"{_text('status', lang)}: {issue}", styles["status"]))
    story.append(_p(f"{_text('generated_with', lang)} {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["meta"]))
    story.append(Spacer(1, 6))

    for section in resolve_sections(document):
        fields = _visible_fields(section, values)
        if not fields:
            continue
        rows = [(_label(f, lang), _field_display(f, values, lang)) for f in fields]
        story.extend([
            _section_header(_label(section, lang), styles, width),
            _fields_table(rows, styles, width),
            Spacer(1, 6),
        ])

    included = [ln for ln in lines if ln.get("include", True)]
    if included:
        header = _text("line_headers", lang)
        rows = []
        tw = tv = 0.0
        for i, line in enumerate(included, start=1):
            w = line.get("weight_total_kg") or 0
            v = line.get("transport_volume_m3") or 0
            tw += w
            tv += v
            rows.append([
                i, line.get("output_description") or line.get("description"),
                line.get("quantity"), line.get("unit"),
                line.get("weight_total_kg"), line.get("transport_volume_m3"), _dims(line),
            ])
        rows.append(["", _text("totals", lang), "", "", round(tw, 2), round(tv, 3), ""])
        story.append(_section_header(_text("goods", lang), styles, width))
        story.append(_grid_table(header, rows, styles, width,
                                 col_weights=[.065, .28, .11, .105, .14, .13, .17],
                                 numeric_columns=(0, 2, 4, 5), summary_last=True))
        story.append(Spacer(1, 6))

    profile = document.get("dg_profile")
    if profile and dangerous_goods:
        header = _dg_headers(profile, lang)
        rows = []
        for entry in dangerous_goods:
            for product in entry.get("products", []):
                rows.append(_dg_rows(profile, entry, product, values, lang))
        story.append(_section_header(f"{_text('dg_table', lang)} ({profile})", styles, width))
        if profile == "IMDG":
            for row in rows:
                story.extend([_imdg_item(header, row, styles, width), Spacer(1, 8)])
        else:
            story.append(_grid_table(header, rows, styles, width))
        story.append(Spacer(1, 6))

        # ADR 5.4.1.1.1.1: the total quantity per transport category belongs in
        # the transport document when the 1.1.3.6 exemption is relied upon.
        if profile in {"ADR", "RID", "ADN"}:
            totals = adr_category_totals(dangerous_goods, lang)
            if totals["statement"]:
                story.append(_p(totals["statement"], styles["fixed"]))
                story.append(Spacer(1, 6))

    for item in document.get("fixed_texts") or []:
        story.append(_p(pick(item, lang), styles["fixed"]))
        story.append(Spacer(1, 3))

    legal = pick(document.get("legal_reference"), lang)
    if legal:
        story.append(_p(f"{_text('legal_reference', lang)}: {legal}", styles["note"]))
    note = pick(document.get("signature_note"), lang)
    if note:
        story.append(_p(note, styles["note"]))

    if signature_png:
        story.append(KeepTogether(_signature_block(signature_png, styles, lang)))

    story.append(Spacer(1, 8))
    block = _card_qr_block(card_link_base, dangerous_goods, styles, lang,
                           document.get("dg_profile"))
    if block:
        story.append(KeepTogether(block))
        story.append(Spacer(1, 6))
    story.append(_p(_text("disclaimer", lang), styles["disclaimer"]))

    doc.build(story)
    return out_path


# How large the code is printed, which is not a decision about the page — it is
# a decision about whether a phone reads it.
#
# A QR is read by its *module*, the single square, and what a scanner needs is a
# module wide enough to survive the print, the paper and the light. So the
# module size is what is fixed here, and the printed size follows from it.
#
# It has to, because the amount of data is not fixed. One UN number encodes to a
# version 4 symbol, 33 modules across; a document carrying a dozen substances
# needs a bigger symbol for the same 24 mm, and every extra number makes the
# squares smaller. A fixed printed size therefore means the code stops working
# on exactly the documents that carry the most — which is the wrong way round.
#
#: The module size the printed code is built to hold. This is a chosen number
#: and not a measured one: the published minimums for printed symbols sit
#: behind paywalled or unreachable specifications, so rather than cite a figure
#: from memory this is set where a 600 dpi laser puts roughly fifteen dots
#: across a module and a phone camera has something to work with in a badly lit
#: cab. If a real specification is ever read, this is the one line to correct.
CARD_QR_MODULE_MM = 0.62

#: The smallest the code is printed even when the data would allow less, and
#: the largest it may grow to before it starts competing with the document it
#: sits under. At the ceiling the modules fall below the size above; the
#: alternative is a code that takes a quarter of the page.
CARD_QR_MIN_MM = 24.0
CARD_QR_MAX_MM = 40.0


def _card_qr_block(base: str | None, dangerous_goods, styles, lang,
                   profile: str | None = None) -> list:
    """A code that opens this installation's cards for these UN numbers.

    Absent unless the caller passed a base address, which the export route only
    does when an administrator turned the public card links on. The renderer
    itself reads no settings and touches no database: it is handed the address
    or it is not, and a document rendered anywhere else is unchanged.

    What the code carries is the UN numbers and nothing else — no consignment,
    no party, no quantity, no reference. The document already prints those
    numbers in plain text and larger, so the code discloses nothing the paper
    does not. It is also why there is no link to expire: it addresses the
    regulation, not a stored job.

    The regime travels with them. A card is per UN number *and* modality
    because the regimes print different obligations, so a code on a sea
    document that opened the road card would be answering the wrong question
    quietly — which is the one failure mode worse than answering none.

    Drawn as vector with reportlab's own widget rather than through the SVG
    library the second factor uses. A QR that goes through an image loses the
    crispness that decides whether a phone reads it at the roadside.

    Error correction is at level M, not the library's default L. A code on a
    transport document spends its life in a cab and a warehouse, and M recovers
    a symbol that is fifteen per cent damaged where L manages seven.
    """
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing

    from app.services.documents.un_cards import PROFILE_TO_MODALITY, un_numbers_in

    if not base:
        return []
    numbers = un_numbers_in(dangerous_goods)
    if not numbers:
        return []

    modality = PROFILE_TO_MODALITY.get(str(profile or "").strip().upper())
    url = f"{base.rstrip('/')}/cards?un={','.join(numbers)}"
    if modality:
        url += f"&m={modality}"
    widget = qr.QrCodeWidget(url, barLevel="M")
    bounds = widget.getBounds()

    # The bounds cover the symbol *and* the four-module quiet zone the widget
    # draws inside them, so this is the full count the printed square holds.
    across = widget.qr.getModuleCount() + 2 * widget.barBorder
    side = min(max(across * CARD_QR_MODULE_MM, CARD_QR_MIN_MM),
               CARD_QR_MAX_MM) * mm

    drawing = Drawing(side, side, transform=[
        side / (bounds[2] - bounds[0]), 0, 0,
        side / (bounds[3] - bounds[1]), 0, 0])
    drawing.add(widget)
    return [
        Table(
            [[drawing, _p(_text("card_qr", lang), styles["disclaimer"])]],
            colWidths=[side + 4 * mm, None],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]),
        )
    ]
