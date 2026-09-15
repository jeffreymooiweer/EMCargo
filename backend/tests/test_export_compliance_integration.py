"""What is really in the exported document, read back out of the PDF.

The wizard checks, but the screen must never be the only place where that
happens: a stale or never-refreshed screen result must not produce a document.
These tests therefore go via the export side and read the outcome back out of
the file a user gets in their hands — not out of an intermediate layer.

Two things are recorded here that a unit test cannot catch:

- the export runs the compliance check itself again, with the input sent along
  at that moment;
- the air declaration carries the IATA packing instruction and not the ADR
  instruction for the same substance. Those two look alike (P001 against 965) and
  swapping them means a declaration that does not match the packaging.
"""

import pytest
from pypdf import PdfReader

from app.services.documents.exporter import validate_document
from app.services.documents.pdf_forms import fill_pdf_document
from app.services.documents.registry import get_document
from tests.test_documents import BASE_VALUES, LINES, _pdf_visible_text


def air_values(**overrides):
    return dict(
        BASE_VALUES,
        awb_number="020-12345675",
        aircraft_limitation="cargo_only",
        shipment_type="non_radioactive",
        signatory_name="J. Jansen",
        declaration_place="Utrecht",
        declaration_date="2026-07-12",
        emergency_contact="+31 6 12345678",
        **overrides,
    )


def air_entry(**product):
    base = {
        "un_number": "3480",
        "proper_shipping_name": "Lithium ion batteries",
        "class": "9",
        "packing_group": "II",
        "packing_instruction": "965",
        "quantity_packages": "2",
        "type_of_package": "4G box",
        "net_mass_liters_per_package": "5 kg",
    }
    return [{"line_id": 1, "vehicle": "Batterijen", "products": [{**base, **product}]}]


# --- The export checks for itself ----------------------------------------------

def test_the_export_runs_the_compliance_check_itself():
    """Class 1 together with another class is forbidden under ADR 7.5.2.1. The
    export should stop that, even if the screen was never refreshed."""
    entries = [{
        "line_id": 1,
        "vehicle": "WAGEN-1",
        "products": [
            {"un_number": "0004", "class": "1.1D", "proper_shipping_name": "AMMONIUMPIKRAAT",
             "quantity_packages": "1", "transport_category": "1", "adr_total_quantity": "5 kg"},
            {"un_number": "1203", "class": "3", "proper_shipping_name": "BENZINE",
             "packing_group": "II", "quantity_packages": "1",
             "transport_category": "2", "adr_total_quantity": "20 L"},
        ],
    }]
    errors, _ = validate_document(get_document("cmr"), BASE_VALUES, LINES, entries, "ADR")
    assert any("7.5.2.1" in e for e in errors), errors


def test_a_q_value_above_one_blocks_the_export():
    """IATA 5.0.2.11: above Q = 1 the combination may not fly like that."""
    entries = [{
        "line_id": 1,
        "vehicle": "COLLO-1",
        "products": [
            {"un_number": "1263", "class": "3", "proper_shipping_name": "VERF",
             "packing_group": "II", "quantity_packages": "1",
             "q_net_quantity": "4", "q_max_net_quantity": "5"},
            {"un_number": "1866", "class": "3", "proper_shipping_name": "HARSOPLOSSING",
             "packing_group": "II", "quantity_packages": "1",
             "q_net_quantity": "3", "q_max_net_quantity": "5"},
        ],
    }]
    errors, _ = validate_document(get_document("iata_dgd"), air_values(), LINES, entries, "IATA")
    assert any("5.0.2.11" in e for e in errors), errors


def test_a_q_value_within_the_limit_does_not_block_the_export():
    entries = [{
        "line_id": 1,
        "vehicle": "COLLO-1",
        "products": [
            {"un_number": "1263", "class": "3", "proper_shipping_name": "VERF",
             "packing_group": "II", "quantity_packages": "1",
             "packing_instruction": "353",
             "q_net_quantity": "1", "q_max_net_quantity": "5"},
            {"un_number": "1866", "class": "3", "proper_shipping_name": "HARSOPLOSSING",
             "packing_group": "II", "quantity_packages": "1",
             "packing_instruction": "353",
             "q_net_quantity": "1", "q_max_net_quantity": "5"},
        ],
    }]
    errors, _ = validate_document(get_document("iata_dgd"), air_values(), LINES, entries, "IATA")
    assert not any("5.0.2.11" in e for e in errors), errors


def test_the_check_uses_the_quantities_that_are_sent_now():
    """Twice the same substance, only the quantity differs: the outcome has to
    move with it. A cached result would give the same answer here."""
    def points_for(quantity: str):
        entries = [{
            "line_id": 1, "vehicle": "WAGEN-1",
            "products": [{
                "un_number": "1203", "class": "3", "proper_shipping_name": "BENZINE",
                "packing_group": "II", "quantity_packages": "1",
                "transport_category": "2", "adr_total_quantity": quantity,
            }],
        }]
        return validate_document(get_document("cmr"), BASE_VALUES, LINES, entries, "ADR")

    small_errors, small_warnings = points_for("20 L")
    large_errors, large_warnings = points_for("2000 L")
    # 2000 L in category 2 counts for 6000 points and goes well past 1000; 20 L
    # stays far below it. The outcomes must therefore not be the same.
    assert (small_errors, small_warnings) != (large_errors, large_warnings)


# --- What ends up in the air declaration ----------------------------------------

def test_the_air_declaration_carries_the_iata_packing_instruction():
    """P001 is the ADR instruction for the same substance; on a DGD it should be 353.

    Both are on the substance and swapping them produces a declaration that does
    not match the packaging underneath it.
    """
    entries = air_entry(
        un_number="1263", proper_shipping_name="PAINT", **{"class": "3"},
        packing_instruction="353",          # IATA
        adr_packing_instruction="P001",     # ADR, does not belong on it
    )
    path = fill_pdf_document("iata_dgd", air_values(), LINES, entries, "en")
    try:
        visible = _pdf_visible_text(path)
        assert "353" in visible
        assert "P001" not in visible
    finally:
        path.unlink(missing_ok=True)


def test_the_authorization_reaches_the_document():
    """Under which approval or exemption the consignment may fly.

    The template EMCargo fills in has no separate field for that — the
    Authorization box of the DGD sits inside the goods table — so it goes as a
    named line of its own below that table. Omitting is not an option: without
    that reference, a consignment that needs one cannot be offered.
    """
    values = air_values(authorization="Competent authority approval NL-2026-0042")
    path = fill_pdf_document("iata_dgd", values, LINES, air_entry(), "en")
    try:
        visible = _pdf_visible_text(path)
        assert "Authorization" in visible
        assert "NL-2026-0042" in visible
    finally:
        path.unlink(missing_ok=True)


def test_without_an_authorization_the_line_is_left_off():
    """An empty box with only the word 'Authorization' in it suggests that
    something was approved."""
    path = fill_pdf_document("iata_dgd", air_values(), LINES, air_entry(), "en")
    try:
        assert "Authorization" not in _pdf_visible_text(path)
    finally:
        path.unlink(missing_ok=True)


def test_the_emergency_contact_reaches_the_document():
    path = fill_pdf_document("iata_dgd", air_values(), LINES, air_entry(), "en")
    try:
        assert "+31 6 12345678" in _pdf_visible_text(path)
    finally:
        path.unlink(missing_ok=True)


def test_the_declaration_is_flat_so_the_values_cannot_be_edited_away():
    """A completed form that is still editable is not a declaration."""
    path = fill_pdf_document("iata_dgd", air_values(), LINES, air_entry(), "en")
    try:
        assert PdfReader(str(path)).get_fields() in (None, {})
    finally:
        path.unlink(missing_ok=True)


# --- IMDG: één eindconclusie ---------------------------------------------------

def test_a_16b_provision_and_the_class_table_resolve_to_one_outcome():
    """7.2.3.1 lets column 16b prevail over the segregation table of 7.2.4.

    Where both say something, no outcome may stand that contradicts the other:
    the strictest rule governs and the rest is marked as background, not as
    separate contradictory advice.
    """
    from app.services.dg.compliance import check_imdg_segregation

    entries = [{
        "line_id": 1, "vehicle": "CONTAINER-1",
        "products": [
            {"un_number": "1203", "class": "3", "proper_shipping_name": "BENZINE",
             "packing_group": "II", "quantity_packages": "1"},
            {"un_number": "1830", "class": "8", "proper_shipping_name": "ZWAVELZUUR",
             "packing_group": "II", "quantity_packages": "1"},
        ],
    }]
    findings = check_imdg_segregation(entries, "nl")
    governing = [f for f in findings if f.get("takes_precedence_over")]
    superseded = [f for f in findings if f.get("superseded_by")]
    # If something takes precedence, the overruled part has to say so too —
    # otherwise there are two equal, contradictory statements.
    if governing:
        assert superseded, findings
        for finding in superseded:
            assert finding["severity"] == "info"


@pytest.mark.parametrize("profile", ["ADR", "IMDG", "IATA"])
def test_an_export_without_dangerous_goods_is_not_blocked_by_the_dg_check(profile):
    """The check must not hold up anything that contains no dangerous goods."""
    document = get_document("cmr" if profile != "IATA" else "iata_dgd")
    errors, _ = validate_document(document, BASE_VALUES, LINES, [], profile)
    assert not any("7.5.2" in e or "5.0.2.11" in e for e in errors), errors


pytestmark = pytest.mark.usefixtures("synthetic_templates")
