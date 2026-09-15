"""The dossier-inspired frame for every document EMCargo designs itself."""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate

from app.core.languages import pick
from app.pdf_style import ACCENT, LINE, MUTED, TEXT, BOLD, MARGIN, draw_wordmark, fit_text, register_fonts
from app.services.documents import brand as brand_module

PAGE = {"nl": "Pagina", "en": "Page", "de": "Seite", "fr": "Page"}


def _draw_frame(canvas, doc: BaseDocTemplate, title: str, lang: str) -> None:
    brand = brand_module.current()
    width, height = doc.pagesize
    left, right = doc.leftMargin, width - doc.rightMargin
    canvas.saveState()
    canvas.setFillColor(ACCENT)
    canvas.rect(0, height - 3, width, 3, fill=1, stroke=0)
    used = draw_wordmark(canvas, left, height - 42, name=brand.name, logo=brand.logo,
                         max_width=doc.width * .49)
    title_width = max(70, doc.width - used - 24)
    lines = simpleSplit(title, TEXT, 7.4, title_width)
    canvas.setFont(TEXT, 7.4)
    canvas.setFillColor(MUTED)
    for index, line in enumerate(lines[:2]):
        if index == 1 and len(lines) > 2:
            line = " ".join(lines[1:])
        canvas.drawRightString(right, height - 37 - index * 10,
                               fit_text(line, TEXT, 7.4, title_width))
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(.6)
    canvas.line(left, height - 60, right, height - 60)
    canvas.line(left, 40, right, 40)
    canvas.setFont(TEXT, 7.5)
    canvas.drawString(left, 25, fit_text(brand.name, TEXT, 7.5, doc.width - 90))
    canvas.setFont(BOLD, 7.5)
    canvas.setFillColor(ACCENT)
    canvas.drawRightString(right, 25, f"{pick(PAGE, lang, 'Page')} {doc.page}")
    canvas.restoreState()


def branded_document(out_path: Path | str, title: str, lang: str = "nl",
                     pagesize=A4) -> BaseDocTemplate:
    """Use an exact content frame so tables align with the page furniture."""
    register_fonts()
    doc = BaseDocTemplate(str(out_path), pagesize=pagesize,
                          leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=82, bottomMargin=54,
                          title=title, author=brand_module.current().name)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="EMCargo", frames=[frame],
                        onPage=lambda canvas, document: _draw_frame(canvas, document, title, lang)))
    return doc
