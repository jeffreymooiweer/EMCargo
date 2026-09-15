"""The dossier-inspired design shared by exports and the offline card builder.

This module has no dependency on settings, databases or the web application.
Regulatory artwork retains its own dimensions, colours and typefaces.
"""
from __future__ import annotations

import io
from pathlib import Path
from threading import RLock

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

ACCENT = colors.HexColor("#245BEA")
INK = colors.HexColor("#152238")
BODY = colors.HexColor("#2B384D")
MUTED = colors.HexColor("#637187")
LINE = colors.HexColor("#DCE3EE")
PALE = colors.HexColor("#F2F5FA")
WHITE = colors.white
TEXT = "EMCargoText"
BOLD = "EMCargoTextBold"
DISPLAY = "EMCargoDisplay"
ASSETS = Path(__file__).resolve().parent / "assets"
MARGIN = 51.0
_font_lock = RLock()


class SectionHeading(Paragraph):
    """Reserve a table's opening rows without keeping the entire table.

    ReportLab's keepWithNext groups a heading with the *whole* next table.
    Even a splittable table then moves to a new page, leaving large gaps.
    Reserve enough room for a normal header and first row instead.
    """

    keepWithNext = False

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        width, height = super().wrap(avail_width, avail_height)
        if height + self.getSpaceAfter() + 90 > avail_height:
            return width, avail_height + 1
        return width, height

    def split(self, avail_width: float, avail_height: float) -> list:
        return []


def register_fonts() -> None:
    """Embed local fonts in source, container and native exports alike."""
    with _font_lock:
        for name, filename in ((TEXT, "DejaVuSans.ttf"), (BOLD, "DejaVuSans-Bold.ttf"),
                               (DISPLAY, "CalSans-Regular.ttf")):
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(ASSETS / "fonts" / filename)))
        pdfmetrics.registerFontFamily(TEXT, normal=TEXT, bold=BOLD, italic=TEXT, boldItalic=BOLD)
        pdfmetrics.registerFontFamily(DISPLAY, normal=DISPLAY, bold=DISPLAY,
                                      italic=DISPLAY, boldItalic=DISPLAY)


def fit_text(text: str, font: str, size: float, width: float) -> str:
    """Fit repeating furniture; the full value stays in the document body."""
    if pdfmetrics.stringWidth(text, font, size) <= width:
        return text
    while text and pdfmetrics.stringWidth(text + "...", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "..." if text else ""


def draw_wordmark(canvas, x: float, baseline: float, name: str = "EMCargo",
                  logo: bytes | None = None, size: float = 18,
                  max_width: float = 250) -> float:
    """Align the visible mark with the capital E, retaining custom branding."""
    register_fonts()
    canvas.saveState()
    start = x
    cap = pdfmetrics.getFont(DISPLAY).face.capHeight * size / 1000
    if logo:
        try:
            with Image.open(io.BytesIO(logo)) as picture:
                rgba = picture.convert("RGBA")
                bounds = rgba.getchannel("A").getbbox()
                if bounds:
                    left, top, right, bottom = bounds
                    scale = min(cap / (bottom - top), 72 / (right - left))
                    canvas.saveState()
                    try:
                        clip = canvas.beginPath()
                        clip.rect(x, baseline, (right - left) * scale, (bottom - top) * scale)
                        canvas.clipPath(clip, stroke=0, fill=0)
                        canvas.drawImage(ImageReader(rgba), x - left * scale,
                                         baseline - (rgba.height - bottom) * scale,
                                         width=rgba.width * scale, height=rgba.height * scale,
                                         mask="auto")
                    finally:
                        canvas.restoreState()
                    x += (right - left) * scale + size * .22
        except (OSError, ValueError):
            pass
    shown = fit_text(name, DISPLAY, size, max(0, max_width - (x - start)))
    canvas.setFont(DISPLAY, size)
    if shown == "EMCargo":
        canvas.setFillColor(ACCENT)
        canvas.drawString(x, baseline, "EM")
        canvas.setFillColor(INK)
        canvas.drawString(x + pdfmetrics.stringWidth("EM", DISPLAY, size), baseline, "Cargo")
    else:
        canvas.setFillColor(INK)
        canvas.drawString(x, baseline, shown)
    canvas.restoreState()
    return x - start + pdfmetrics.stringWidth(shown, DISPLAY, size)


def paragraph_styles() -> dict[str, ParagraphStyle]:
    register_fonts()
    base = ParagraphStyle("emcargo_body", fontName=TEXT, fontSize=9.1, leading=13.2,
                          textColor=BODY, alignment=TA_LEFT, spaceAfter=0,
                          splitLongWords=True, allowWidows=0, allowOrphans=0)

    def style(name, **options):
        return ParagraphStyle("emcargo_" + name, parent=base, **options)

    return {
        "title": style("title", fontName=DISPLAY, fontSize=21, leading=25.2,
                       textColor=INK, spaceAfter=8, keepWithNext=True),
        "status": style("status", fontSize=8.6, leading=12, textColor=ACCENT,
                        spaceAfter=4, keepWithNext=True),
        "meta": style("meta", fontSize=8, leading=11.5, textColor=MUTED, spaceAfter=4),
        "section": style("section", fontName=DISPLAY, fontSize=12.5, leading=16,
                         textColor=INK, spaceBefore=10, spaceAfter=6, keepWithNext=True),
        "label": style("label", fontName=BOLD, fontSize=8.3, leading=12, textColor=MUTED),
        "value": style("value"),
        "note": style("note", fontSize=8.1, leading=11.6, textColor=MUTED, spaceAfter=4),
        "cell": style("cell", fontSize=8.2, leading=11.6),
        "cellh": style("cellh", fontName=BOLD, fontSize=8.1, leading=11.4, textColor=WHITE),
        "fixed": style("fixed", fontSize=8.6, leading=12.5, spaceAfter=4),
        "disclaimer": style("disclaimer", fontSize=7.5, leading=10.5, textColor=MUTED),
    }


def table_commands(*, header: bool = True) -> list[tuple]:
    """Quiet alternating rows, horizontal rules and a blue column heading."""
    first = 1 if header else 0
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6 if header else 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6 if header else 4),
        ("ROWBACKGROUNDS", (0, first), (-1, -1), [PALE, WHITE]),
        ("LINEBELOW", (0, first), (-1, -1), .35, LINE),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                     ("TOPPADDING", (0, 0), (-1, 0), 8),
                     ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]
    return commands
