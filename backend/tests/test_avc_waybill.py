"""Tests for the AVC waybill and the ADR description on the CMR.

ADR 5.4.1 prescribes no form for the transport document: a waybill carrying the
description of 5.4.1.1.1 suffices. That is why both the CMR and the AVC waybill
carry that description, and why a separate ADR road document has been dropped.

The AVC waybill fills in the official form, just as the CMR does. That form has
no AcroForm fields, so the values go over templates/forms/avc.pdf as a text
layer; the tests therefore check both the text and the position that text ends
up at.
"""

import re

import fitz
import pytest

from app.services.dg.autofill import prepare_entries
from app.services.documents.avc_form import fill_avc_waybill, has_avc_template
from app.services.documents.pdf_forms import fill_cmr
from app.services.documents.registry import get_document, get_registry

LINES = [
    {
        "line_id": 1, "include": True, "quantity": 10, "unit": "jerrycan",
        "weight_total_kg": 165, "transport_volume_m3": 0.3, "description": "jerrycan benzine",
    },
    {
        "line_id": 2, "include": True, "quantity": 4, "unit": "pallet",
        "weight_total_kg": 820, "description": "pallets kalkzandsteen",
    },
]
ENTRIES = [{
    "line_id": 1, "vehicle": "Jerrycans",
    "products": [{"un_number": "1203", "net_mass_liters_per_package": "20 L"}],
}]
VALUES = {
    "consignor_name": "Mooiweer Logistiek BV",
    "consignor_address": "Havenweg 12\n3011 AA Rotterdam",
    "consignee_name": "Bouwbedrijf De Vries",
    "consignee_address": "Industrieplein 5\n7511 JK Enschede",
    "carrier_name": "Transport Jansen",
    "freight_payment": "franco",
    "vehicle_registration": "12-BXG-4",
    "loading_point": "Rotterdam",
    "loading_date": "2026-08-02",
}


@pytest.fixture
def prepared():
    return prepare_entries(ENTRIES, LINES, ["ADR"], "nl")["entries"]


def _render(dangerous_goods, lang="nl"):
    """Fill the form and produce (full text, words with position)."""
    path = fill_avc_waybill(VALUES, LINES, dangerous_goods, lang)
    try:
        with fitz.open(path) as document:
            page = document[0]
            return page.get_text(), page.get_text("words")
    finally:
        path.unlink(missing_ok=True)


def test_adr_road_document_is_replaced_by_the_avc_waybill():
    """The separate ADR road document has been dropped; the AVC waybill takes its place."""
    registry = get_registry()
    keys = [doc["key"] for doc in registry["documents"]]
    assert "adr_transport_doc" not in keys
    assert "avc_waybill" in keys

    road = next(m for m in registry["modalities"] if m["key"] == "road")
    assert "avc_waybill" in road["documents"]
    # Inland waterway does keep an ADN document of its own: there is no waybill there.
    assert "adn_transport_doc" in keys

    avc = get_document("avc_waybill")
    assert avc["dg_profile"] == "ADR"
    # No dg_only: the waybill is there for consignments without dangerous goods too.
    assert not avc.get("dg_only")


def test_cmr_carries_the_adr_description_and_category_totals(prepared):
    """Without the 5.4.1.1.1 line the CMR would not suffice as a transport document."""
    fields = fill_cmr({**VALUES, "sender_instructions": "Voorzichtig laden"}, LINES, prepared, "nl")

    # Both names, because this is a Dutch document. ADR 5.4.1.4.1 wants an
    # official language of the forwarding country and, since Dutch is not
    # English, French or German, one of those three in addition. "BENZINE" on
    # its own would be short of a requirement.
    # Since v1.102.0 a description longer than the goods box wraps onto the
    # following rows instead of being clipped (5.4.1.1.2: the information
    # must be legible). The whole line is on the paper, spread over rows.
    description_rows = " ".join(
        fields[f"VakRood06Regel{n:02d}Kolom06"]
        for n in range(1, 5)
        if f"VakRood06Regel{n:02d}Kolom06" in fields
    )
    full_line = ("UN 1203, BENZINE OF MOTORBRANDSTOF (MOTOR SPIRIT OR GASOLINE "
                 "OR PETROL), 3, II, (D/E), 10 jerrycan, 200 L")
    assert full_line == " ".join(description_rows.split())[:len(full_line)]
    # Lines without dangerous goods keep their ordinary description.
    assert "4 × pallets kalkzandsteen" in description_rows
    # The mass is not counted twice over the DG lines.
    assert fields["VakRood06Regel01Kolom11"] == "165"

    # Box 13: the consignor's instruction plus the total per transport category.
    assert "Voorzichtig laden" in fields["VakRood13"]
    assert "Totale hoeveelheid per vervoerscategorie: 2: 200 L" in fields["VakRood13"]


def test_cmr_without_dangerous_goods_keeps_plain_descriptions():
    fields = fill_cmr(VALUES, LINES, None, "nl")
    assert fields["VakRood06Regel01Kolom06"] == "10 × jerrycan benzine"
    assert "VakRood13" not in fields


def test_the_official_avc_template_can_be_imported():
    """The waybill fills in an existing form; that template belongs in the repo."""
    from app.services.document_templates import profiles
    assert profiles()["avc"]["pages"] == 1


def test_avc_waybill_fills_the_official_form(prepared, official_templates):
    text, _words = _render(prepared)

    # The template itself stays: both panels and the AVC reference.
    assert "VRACHTBRIEF - VERVOERDOCUMENT" in text
    assert "ONTVANGSTBEWIJS" in text
    assert "vervoercondities 2002" in text
    # Our values are in it, in both panels.
    assert text.count("Mooiweer Logistiek BV") == 2
    assert text.count("Bouwbedrijf De Vries") == 2
    assert text.count("Transport Jansen") == 2
    assert "12-BXG-4" in text
    assert "Rotterdam" in text and "2026-08-02" in text
    # Franco ticked, not-franco not: one tick per panel.
    crosses = sorted((round(w[0]), round(w[1])) for w in _words if w[4] == "X")
    assert crosses == [(38, 248), (419, 248)]
    # The dangerous substance appears as the ADR description in the 'inhoud'
    # column, wrapped inside a narrow column. Where the line breaks fall is the
    # typesetting's business and changes with the name — the 2025 volume prints
    # three alternatives for UN 1203 where the export kept one — so the check
    # collapses the whitespace and reads the sentence, instead of pinning the
    # three fragments a particular wrap happened to produce.
    flat = re.sub(r"\s+", " ", text)
    assert ("UN 1203, BENZINE OF MOTORBRANDSTOF "
            "(MOTOR SPIRIT OR GASOLINE OR PETROL), 3, II, (D/E), 10") in flat
    assert "Totale hoeveelheid per vervoerscategorie" in text
    # Totals over both lines: 10 + 4 packages, 165 + 820 kg.
    assert text.count("14") >= 2 and text.count("985") >= 2
    # The disclaimer belongs on every generated document.
    assert "CONCEPT" in text


def test_avc_values_land_inside_their_boxes(prepared, official_templates):
    """The overlay is coordinate-driven: if that shifts, the form is wrong."""
    _text, words = _render(prepared)

    def box_of(needle):
        hits = [w for w in words if w[4] == needle]
        assert hits, f"{needle} niet gevonden"
        return hits[0]

    # 'Mooiweer' sits in the consignor box: below the label (y > 52) and above
    # the dividing line at y 110.
    x0, y0, _x1, y1, *_ = box_of("Mooiweer")
    assert 33 < x0 < 121 and 52 < y0 and y1 < 110
    # 'Bouwbedrijf' sits in the delivery address box (y 110-228).
    _x0, y0, _x1, y1, *_ = box_of("Bouwbedrijf")
    assert 121 < y0 and y1 < 228
    # The carrier sits to the right of the franking column (x > 120.8).
    x0, y0, _x1, y1, *_ = box_of("Jansen")
    assert x0 > 120.8 and 243 < y0 and y1 < 275

    # The consignor box is narrower than the frame: the small-print column starts
    # at x 299.2 and must not be written over.
    for x0, _y0, x1, y1, word, *_ in words:
        if x0 < 299 and y1 < 110 and word not in {"niet", "voor", "in", "de"}:
            assert x1 <= 299.2, f"{word} loopt in de kleine-letterkolom"

    # The weights are right-aligned in the weight column.
    x0, _y0, x1, _y1, *_ = box_of("165")
    assert 350 < x1 <= 391


def test_avc_waybill_without_dangerous_goods(official_templates):
    text, _words = _render(None)
    assert "jerrycan benzine" in text
    assert "UN 1203" not in text
    assert "vervoerscategorie" not in text


def test_avc_waybill_in_english(official_templates):
    text, _words = _render(None, "en")
    # The template is Dutch; only our own text follows the language choice.
    assert "DRAFT" in text and "CONCEPT" not in text
    assert "jerrycan benzine" in text


def test_avc_long_description_wraps_inside_the_contents_column(prepared, official_templates):
    """The 'inhoud' column must not run into the 'gewicht in kg' column."""
    _text, words = _render(prepared)
    goods = [w for w in words if 283 < w[1] < 552 and 240 < w[0] < 406]
    assert goods, "geen goederenregels gevonden"
    for _x0, _y0, x1, _y1, word, *_ in goods:
        if word in {"165", "820"}:
            continue
        assert x1 <= 352, f"{word} loopt tot {x1:.1f} en botst met de gewichtskolom"
