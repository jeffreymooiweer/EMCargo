"""The dossier style must survive operational document sizes.

The old equal-width tables broke short column headings into individual
letters. Whole-section grouping wasted pages, while the card renderer
silently dropped the fourth translation and clipped long source notes.
These cases check the produced paper, not just the chosen colour constants.
"""
from __future__ import annotations

import re
from pathlib import Path

import fitz
import pytest

from app.services.documents import brand
from app.services.documents.pdf_render import render_document_pdf
from app.services.documents.registry import get_document


def _text(pdf):
    return re.sub(r"\s+", " ", " ".join(page.get_text() for page in pdf))


def _inside_paper(pdf):
    for page in pdf:
        for x0, y0, x1, y1, *word in page.get_text("words"):
            assert x0 >= 50, (page.number, word, x0)
            assert x1 <= page.rect.width - 50, (page.number, word, x1)
            assert y0 >= 20 and y1 <= page.rect.height - 15, (page.number, word, y0, y1)


@pytest.mark.parametrize("language", ["nl", "en", "de", "fr"])
def test_long_addresses_and_repeating_goods_tables_remain_complete(language):
    tokens = [f"address-{number:03}" for number in range(420)]
    goods = [{"description": f"ITEM-{number:03} — aluminium pièces détachées",
              "quantity": 2, "unit": "pcs", "weight_total_kg": 12.5}
             for number in range(85)]
    path = render_document_pdf(get_document("packing_list"),
                               {"consignor_name": "Étoile & Söhne",
                                "consignor_address": " ".join(tokens)}, goods, [], language)
    try:
        with fitz.open(path) as pdf:
            assert len(pdf) >= 4
            text = _text(pdf)
            assert "Étoile & Söhne" in text
            assert all(token in text for token in tokens)
            assert all(f"ITEM-{number:03}" in text for number in range(85))
            for page in pdf:
                content = page.get_text()
                if "ITEM-" in content:
                    assert "(kg)" in content
            embedded = {row[3] for page in pdf for row in page.get_fonts() if row[1] == "ttf"}
            assert any("CalSans" in name for name in embedded)
            assert any("DejaVuSans" in name for name in embedded)
            assert any("DejaVuSans-Bold" in name for name in embedded)
            _inside_paper(pdf)
    finally:
        path.unlink()


def test_imdg_keeps_all_ten_fields_readable_on_portrait_paper():
    product = {
        "un_number": "1203", "proper_shipping_name": "PETROL",
        "class": "3", "packing_group": "II", "marine_pollutant": "Yes",
        "flashpoint": "-40 °C", "ems_code": "F-E, S-E", "quantity_packages": "4",
        "type_of_package": "drums", "net_mass_liters_per_package": "150 L",
        "gross_mass_per_package": "130 kg",
    }
    path = render_document_pdf(get_document("imo_dgd"), {}, [],
                               [{"products": [product]}], "en")
    try:
        with fitz.open(path) as pdf:
            text = _text(pdf)
            for value in ("UN 1203", "PETROL", "Marine pollutant", "Flashpoint", "EmS",
                          "150 L", "130 kg", "4 × drums", "F-E, S-E", "-40 °C"):
                assert value in text, value
            assert any("1203" in [word[4] for word in page.get_text("words")] for page in pdf)
            assert any("Marine" in [word[4] for word in page.get_text("words")] for page in pdf)
            _inside_paper(pdf)
    finally:
        path.unlink()


def test_a_long_installation_name_cannot_overprint_the_running_title():
    name = "International Logistics " * 12
    brand.set_current(brand.Brand(name=name, logo=None, own=True))
    path = None
    try:
        path = render_document_pdf(get_document("packing_list"), {}, [], [], "fr")
        with fitz.open(path) as pdf:
            _inside_paper(pdf)
            header = [fitz.Rect(word[:4]) for word in pdf[0].get_text("words") if word[1] < 55]
            for index, rectangle in enumerate(header):
                assert all((rectangle & other).is_empty for other in header[index + 1:])
    finally:
        brand.set_current(None)
        if path:
            path.unlink()


def test_card_names_provisions_and_provenance_flow_without_truncation(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "scripts"))
    from un_cards.render import render_card_pdf
    from un_cards.sources.base import CardPage

    tokens = [f"provision-{index:03}" for index in range(900)]
    page = CardPage(modality="ADR", un="0000", names={
        "en": "English name " * 15 + "EN-END",
        "nl": "Nederlandse naam NL-END", "de": "Deutscher Name DE-END",
        "fr": "Désignation française FR-END",
    }, klass="—", packing_group="—", classification_code="—",
        provision_rows=[("Example provision", " ".join(tokens))],
        regulation="Synthetic fixture",
        source="Provenance detail " * 140 + "SOURCE-END")
    path = tmp_path / "card.pdf"
    render_card_pdf(path, [page], "2026-09-15")
    with fitz.open(path) as pdf:
        assert len(pdf) >= 3
        text = _text(pdf)
        for ending in ("EN-END", "NL-END", "DE-END", "FR-END", "SOURCE-END"):
            assert ending in text
        assert all(token in text for token in tokens)
        assert all("UN 0000" in p.get_text() for p in pdf)
        _inside_paper(pdf)
