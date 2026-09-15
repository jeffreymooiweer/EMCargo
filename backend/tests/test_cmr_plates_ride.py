"""One hundred bundled steel plates, Wezep to the port of Rotterdam — the
whole ride through the assistant, ending in the CMR, judged on paper.

The owner ran exactly this consignment and the paper failed three ways at
once: the count was swallowed (one plate of 78.5 kg instead of a hundred of
7850), the route stayed glued to the goods description, and the nature of
goods read "Onbekend 2000x1000x5 mm" — the one word a waybill must never
carry, printed with a decimal count ("100.0 ×") beside it. These tests pin
each repair at the level where it shows: the filled form.
"""
import fitz
import pytest

from app.core.database import SessionLocal
from app.services.assistant.orchestrator import step
from app.services.documents.pdf_forms import fill_pdf_document
from app.services.parser.product_detector import detect_product_type
from app.services.pipeline import build_output_description, parse_and_calculate
from app.services.parser.dimension_extractor import extract_dimensions


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_plural_goods_words_are_recognised_like_their_singulars():
    assert detect_product_type("stalen platen 2000x1000x5") == "plate"
    assert detect_product_type("steel plates 2000x1000x5") == "plate"
    assert detect_product_type("stalen buizen 60x3x6000") == "round_tube"
    assert detect_product_type("houten planken 200x20x3000") == "beam"


def test_an_unrecognised_shape_keeps_the_consignor_s_own_words():
    """Never "Onbekend" on paper: without a recognised shape the description
    is the consignor's own wording, dimensions and all."""
    dims = extract_dimensions("dranghekken 2500x1100x20")
    text = build_output_description("dranghekken 2500x1100x20", None, dims, "nl")
    assert text == "dranghekken 2500x1100x20"
    assert "Onbekend" not in text


def test_the_whole_plates_ride_produces_a_correct_cmr(db, synthetic_templates):
    state = {"modality": "road", "draft_lines": [], "dg_entries": [], "doc_values": {}}
    pending = None
    turns = [
        "100 stalen gebundelde platen 2000x1000x5mm van Kolonel D.J. Teesweg 1 "
        "Wezep naar de haven in Rotterdam",
        "Mooiweer BV", "Kolonel D.J. Teesweg 1, 8091 AV Wezep",
        "Havenbedrijf Rotterdam", "Wilhelminakade 909, 3072 AP Rotterdam",
        "Franco", "Wezep", "vandaag",
    ]
    for message in turns:
        result = step(state, message, pending, db, "nl")
        state, pending = result["state"], result["pending"]
    # The route questions were answered by the first sentence and must not
    # have been asked again on the way here.
    assert state["doc_values"]["loading_point"] == "Kolonel D.J. Teesweg 1 Wezep"
    assert state["doc_values"]["discharge_point"] == "Rotterdam (NLRTM), NL"

    lines = parse_and_calculate(
        "stalen gebundelde platen 2000x1000x5mm | 100 | pcs", db,
        output_language="nl")["lines"]
    path = fill_pdf_document("cmr", state["doc_values"], lines, [], "nl")
    try:
        with fitz.open(str(path)) as doc:
            text = doc[0].get_text()
        assert "100 × Plaat 2000x1000x5 mm" in text
        assert "7850" in text and "7850.0" not in text
        assert "100.0" not in text
        assert "Onbekend" not in text
        assert "Kolonel D.J. Teesweg 1 Wezep" in text
        assert "Rotterdam (NLRTM), NL" in text
    finally:
        path.unlink(missing_ok=True)
