"""Filling in the official AVC waybill form.

The form (templates/forms/avc.pdf) is — unlike the CMR, the CIM and the IATA
air waybill — a flat PDF without AcroForm fields. The values are therefore laid
over the template as a text layer, at positions derived from the rule grid and
the field labels of the form itself.

Grid layout of the template (595 × 640 points, origin top left):

    left panel (waybill)            x  32.5 – 406.3   y  40.0 – 623.8
      consignor                     x  32.5 – 299.2   y  40.0 – 110.0
      delivery address              x  32.5 – 406.3   y 110.0 – 228.3
      franking | carrier            x  32.5 – 120.8 – 406.3   y 228.3 – 275.0
      goods table                   x  32.5 – 406.3   y 275.0 – 571.7
      place of dispatch | date      x  32.5 – 406.3   y 571.7 – 597.5

    right panel (receipt)           x 415.4 – 580.8   y  12.9 – 598.3
      consignor                                       y  39.6 – 110.0
      delivery address                                y 110.0 – 228.3
      franking | carrier            x 415.4 – 478.3 – 580.8   y 228.3 – 275.0
      signature and registration                      y 275.0 – 393.7
      contents + totals                               y 507.5 – 571.7
      date                                            y 571.7 – 598.3

The goods table has no column rules; the column positions follow from the
headings 'aantal', 'verpakking', 'inhoud' and 'gewicht in kg'.

For dangerous goods the description under ADR 5.4.1.1.1 goes in the 'inhoud'
column and the total per transport category (5.4.1.1.1.1) below the last line.
That makes the waybill the transport document as well; ADR 5.4.1 prescribes no
separate form for it.
"""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.core.languages import pick
from app.services.dg.autofill import adr_category_totals, description_line
from app.services.document_templates import resolve as resolve_template

TEMPLATE = "avc.pdf"
PAGE_W, PAGE_H = 595.0, 640.0
TEXT = HexColor("#1a1a1a")

FONT = "Helvetica"
SIZE = 7.5
LEADING = 8.6

# Boxes: (x, y_of_the_first_baseline, width). The y is counted from the top,
# just as in the grid above; _y() converts that.
BOXES: dict[str, tuple[float, float, float]] = {
    # Linkerpaneel — vrachtbrief
    "consignor": (37.0, 62.0, 258.0),
    "delivery": (37.0, 132.0, 365.0),
    "carrier": (125.0, 252.0, 277.0),
    "dispatch_place": (37.0, 594.0, 240.0),
    "dispatch_date": (283.0, 594.0, 120.0),
    "total_count": (58.0, 567.0, 60.0),
    "total_weight": (357.0, 567.0, 45.0),
    # Rechterpaneel — ontvangstbewijs
    "r_consignor": (419.0, 62.0, 158.0),
    "r_delivery": (419.0, 132.0, 158.0),
    "r_carrier": (482.0, 251.0, 96.0),
    "r_registration": (419.0, 294.0, 158.0),
    "r_contents": (419.0, 530.0, 158.0),
    "r_total_count": (450.0, 567.0, 54.0),
    "r_total_weight": (529.0, 567.0, 48.0),
    "r_date": (419.0, 594.0, 158.0),
}

# Tick boxes for the franking instruction: (x, baseline y).
# The boxes themselves sit at 36.7-43.3 and 418.3-425.0 respectively.
CHECKBOXES: dict[str, tuple[float, float]] = {
    "franco": (37.6, 255.0),
    "not_franco": (37.6, 268.3),
    "r_franco": (419.2, 255.0),
    "r_not_franco": (419.2, 268.3),
}
CHECK_SIZE = 7.0

# Goods table: column positions and the available range.
GOODS_TOP = 293.0     # first baseline, below the column headings
GOODS_BOTTOM = 551.0  # up to the labels 'totaal aantal' / 'gewicht'
COL_COUNT = 66.0            # aantal, linksuitgelijnd
COL_PACKAGING = 136.0       # verpakking, linksuitgelijnd
COL_PACKAGING_WIDTH = 100.0
COL_CONTENTS = 245.0        # inhoud, linksuitgelijnd
COL_CONTENTS_WIDTH = 105.0
COL_WEIGHT_RIGHT = 390.0    # gewicht, rechtsuitgelijnd
NOTE_WIDTH = 254.0          # width for the ADR closing line below the table


def has_avc_template() -> bool:
    """Whether the official AVC form is available to be filled in."""
    return resolve_template("avc") is not None


def _y(top: float) -> float:
    """Convert a y measured from the top to the PDF origin at bottom left."""
    return PAGE_H - top


def _wrap(text: str, width: float, size: float = SIZE, font: str = FONT) -> list[str]:
    """Breek af op werkelijke tekstbreedte in punten."""
    out: list[str] = []
    for paragraph in str(text or "").split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if stringWidth(candidate, font, size) <= width or not line:
                line = candidate
            else:
                out.append(line)
                line = word
        if line:
            out.append(line)
    return out


def _clip(text: str, width: float, size: float = SIZE, font: str = FONT) -> str:
    """Truncate so the text does not run into the next column."""
    value = str(text or "")
    if stringWidth(value, font, size) <= width:
        return value
    while value and stringWidth(value + "…", font, size) > width:
        value = value[:-1]
    return f"{value}…" if value else ""


def _draw_box(c: canvas.Canvas, key: str, value: Any, max_lines: int = 6) -> None:
    if value in (None, ""):
        return
    x, top, width = BOXES[key]
    lines = _wrap(str(value), width)[:max_lines]
    c.setFont(FONT, SIZE)
    c.setFillColor(TEXT)
    for index, line in enumerate(lines):
        c.drawString(x, _y(top + index * LEADING), _clip(line, width))


def _draw_check(c: canvas.Canvas, key: str) -> None:
    x, baseline = CHECKBOXES[key]
    c.setFont("Helvetica-Bold", CHECK_SIZE)
    c.setFillColor(TEXT)
    c.drawString(x, _y(baseline), "X")


def _party(name: Any, address: Any, contact: Any = "") -> str:
    return "\n".join(str(x).strip() for x in (name, address, contact) if str(x or "").strip())


def _goods_rows(
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
) -> tuple[list[tuple[str, str, str, str]], float, float]:
    """Rijen (aantal, verpakking, inhoud, gewicht) plus de totalen."""
    dg_by_line: dict[Any, list[str]] = {}
    for entry in dangerous_goods or []:
        for product in entry.get("products") or []:
            if str(product.get("un_number") or "").strip():
                dg_by_line.setdefault(entry.get("line_id"), []).append(
                    description_line(product, "ADR")
                )

    rows: list[tuple[str, str, str, str]] = []
    total_count = 0.0
    total_weight = 0.0
    for line in lines:
        if not line.get("include", True):
            continue
        quantity = line.get("quantity")
        weight = line.get("weight_total_kg")
        try:
            total_count += float(quantity) if quantity not in (None, "") else 0.0
        except (TypeError, ValueError):
            pass
        try:
            total_weight += float(weight) if weight not in (None, "") else 0.0
        except (TypeError, ValueError):
            pass
        contents = dg_by_line.get(line.get("line_id"))
        description = (
            "\n".join(contents)
            if contents
            else (line.get("output_description") or line.get("description") or "")
        )
        rows.append((
            "" if quantity in (None, "") else str(quantity),
            str(line.get("unit") or ""),
            description,
            "" if weight in (None, "") else str(weight),
        ))
    return rows, total_count, total_weight


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _draw_goods(
    c: canvas.Canvas,
    rows: list[tuple[str, str, str, str]],
    note: str,
    lang: str,
) -> None:
    """Fill the goods table and put the ADR closing line below the last line."""
    c.setFont(FONT, SIZE)
    c.setFillColor(TEXT)
    top = GOODS_TOP
    overflow = 0
    for index, (count, packaging, contents, weight) in enumerate(rows):
        wrapped = _wrap(contents, COL_CONTENTS_WIDTH) or [""]
        needed = len(wrapped) * LEADING
        if top + needed > GOODS_BOTTOM:
            overflow = len(rows) - index
            break
        c.drawString(COL_COUNT, _y(top), count)
        c.drawString(COL_PACKAGING, _y(top), _clip(packaging, COL_PACKAGING_WIDTH))
        for offset, piece in enumerate(wrapped):
            c.drawString(COL_CONTENTS, _y(top + offset * LEADING), piece)
        c.drawRightString(COL_WEIGHT_RIGHT, _y(top), weight)
        top += needed

    if overflow:
        text = pick(
            {
                "nl": "+{n} regels — zie bijgevoegde paklijst",
                "en": "+{n} lines — see attached packing list",
                "de": "+{n} Zeilen — siehe beigefügte Packliste", "fr": '+{n} lignes — voir la liste de colisage jointe'},
            lang,
        ).format(n=overflow)
        if top <= GOODS_BOTTOM:
            c.drawString(COL_CONTENTS, _y(top), _clip(text, NOTE_WIDTH))
            top += LEADING

    if note:
        top += LEADING / 2
        for line in _wrap(note, NOTE_WIDTH):
            if top > GOODS_BOTTOM:
                break
            c.drawString(COL_PACKAGING, _y(top), line)
            top += LEADING


def _draw_footer_note(c: canvas.Canvas, text: str) -> None:
    """Small line below the form — the frame runs to y 623.8."""
    c.setFont(FONT, 5.4)
    c.setFillColor(HexColor("#555555"))
    for index, line in enumerate(_wrap(text, 540.0, size=5.4)[:2]):
        c.drawString(33.0, _y(629.0 + index * 6.0), line)


def fill_avc_waybill(
    values: dict[str, Any],
    lines: list[dict[str, Any]],
    dangerous_goods: list[dict[str, Any]] | None,
    lang: str = "nl",
    signature_png: bytes | None = None,
) -> Path:
    """Fill in the official AVC form and produce a PDF."""
    template_path = resolve_template("avc")
    if template_path is None:
        raise FileNotFoundError("Validated AVC template not found")

    fd, overlay_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    overlay_path = Path(overlay_name)
    c = canvas.Canvas(str(overlay_path), pagesize=(PAGE_W, PAGE_H))

    consignor = _party(values.get("consignor_name"), values.get("consignor_address"),
                       values.get("consignor_contact"))
    delivery = _party(values.get("consignee_name"), values.get("consignee_address"),
                      values.get("place_of_delivery"))
    carrier = _party(values.get("carrier_name"), values.get("carrier_address"))

    _draw_box(c, "consignor", consignor, max_lines=5)
    _draw_box(c, "r_consignor", consignor, max_lines=5)
    _draw_box(c, "delivery", delivery, max_lines=11)
    _draw_box(c, "r_delivery", delivery, max_lines=11)
    _draw_box(c, "carrier", carrier, max_lines=3)
    _draw_box(c, "r_carrier", carrier, max_lines=3)
    _draw_box(c, "r_registration", values.get("vehicle_registration"), max_lines=2)

    choice = str(values.get("freight_payment") or "").strip().lower()
    if choice in {"franco", "prepaid", "vooruitbetaald"}:
        _draw_check(c, "franco")
        _draw_check(c, "r_franco")
    elif choice in {"niet franco", "not franco", "collect", "ongefrankeerd"}:
        _draw_check(c, "not_franco")
        _draw_check(c, "r_not_franco")

    rows, total_count, total_weight = _goods_rows(lines, dangerous_goods)

    # ADR 5.4.1.1.1.1: total quantity per transport category, below the table.
    statement = ""
    if dangerous_goods:
        statement = adr_category_totals(dangerous_goods, lang)["statement"] or ""
    _draw_goods(c, rows, statement, lang)

    _draw_box(c, "total_count", _fmt(total_count))
    _draw_box(c, "total_weight", _fmt(total_weight))
    _draw_box(c, "r_total_count", _fmt(total_count))
    _draw_box(c, "r_total_weight", _fmt(total_weight))
    # Receipt: short summary of the contents.
    _draw_box(c, "r_contents", "; ".join(r[2].split("\n")[0] for r in rows[:3]), max_lines=3)

    _draw_box(c, "dispatch_place", values.get("loading_point") or values.get("place_of_receipt"),
              max_lines=1)
    dispatch_date = values.get("loading_date") or values.get("established_date")
    _draw_box(c, "dispatch_date", dispatch_date, max_lines=1)
    _draw_box(c, "r_date", dispatch_date, max_lines=1)

    # Consignor's signature, between 'place of dispatch' and 'date'.
    if signature_png:
        try:
            image = ImageReader(io.BytesIO(signature_png))
            width, height = image.getSize()
            draw_w = 70.0
            draw_h = min(draw_w * height / max(width, 1), 20.0)
            c.drawImage(image, 150.0, _y(595.0), width=draw_w, height=draw_h,
                        mask="auto", preserveAspectRatio=True, anchor="sw")
        except Exception:  # pragma: no cover — beschadigde afbeelding
            pass

    from app.services.documents.notices import output_notice
    disclaimer = output_notice(lang)
    _draw_footer_note(c, disclaimer)

    c.save()

    # Overlay over de template leggen.
    reader = PdfReader(str(template_path))
    overlay = PdfReader(str(overlay_path))
    writer = PdfWriter()
    page = reader.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
    try:
        writer.add_metadata({
            "/Producer": "EMCargo",
            "/Creator": "EMCargo",
            "/Subject": disclaimer,
        })
    except Exception:  # pragma: no cover
        pass

    fd, out_name = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    out_path = Path(out_name)
    try:
        out_path.chmod(0o600)
    except OSError:
        pass
    with open(out_path, "wb") as fh:
        writer.write(fh)
    overlay_path.unlink(missing_ok=True)
    return out_path
