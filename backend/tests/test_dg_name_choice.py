"""The most applicable proper shipping name, chosen by the consignor.

Read from the official Dutch edition (page 421): 3.1.2.1 — the name is the
capital-printed part of the position; 3.1.2.2 — where a position combines
several names separated by "of", only the most applicable one goes on the
transport document. Until v1.102.0 the whole column went on paper: for UN 1202
a ~600-character line that the CMR's goods box clipped, packing group and
tunnel code first — and 5.4.1.1.2 requires the information to be legible.
"""
import fitz

from app.services.dg.autofill import _package_description, prepare_entries
from app.services.documents.pdf_forms import fill_pdf_document


LINES = [{"line_id": 1, "quantity": 1000, "unit": "jerrycan"}]


def prepare(product, profiles=("ADR",), language="nl"):
    return prepare_entries(
        [{"line_id": 1, "products": [product]}], LINES, list(profiles), language)


def questions_by_field(res):
    return {q["field"]: q
            for block in res["open_questions"] for q in block["questions"]}


def test_a_multi_name_position_asks_the_choice_with_the_printed_options():
    q = questions_by_field(prepare({"un_number": "1202", "carriage_mode": "packages",
                                    "net_mass_liters_per_package": "25 L"}))
    assert q["chosen_name"]["options"] == ["DIESELOLIE", "GASOLIE", "STOOKOLIE, LICHT"]
    assert q["chosen_name"]["reason"] == "sp3122"
    # A Dutch document pairs the names, so the English choice is asked too.
    assert q["chosen_name_en"]["options"] == ["GAS OIL", "DIESEL FUEL", "HEATING OIL, LIGHT"]


def test_a_single_name_position_asks_nothing():
    q = questions_by_field(prepare({"un_number": "1090", "carriage_mode": "packages",
                                    "net_mass_liters_per_package": "20 L"}))
    assert "chosen_name" not in q and "chosen_name_en" not in q


def test_the_chosen_names_become_the_shipping_name_and_the_line_is_short():
    res = prepare({"un_number": "1202", "carriage_mode": "packages",
                   "net_mass_liters_per_package": "25 L",
                   "chosen_name": "DIESELOLIE", "chosen_name_en": "DIESEL FUEL"})
    product = res["entries"][0]["products"][0]
    assert product["proper_shipping_name"] == "DIESELOLIE (DIESEL FUEL)"
    (line,) = res["document_lines"]["ADR"]
    assert line.startswith("UN 1202, DIESELOLIE (DIESEL FUEL), 3, III, (D/E)")
    assert len(line) < 120
    # The only question left open is the optional kind-of-jerrican one —
    # 5.4.1.1.1 (e) lets the UN code supplement the description.
    remaining = questions_by_field(res)
    assert set(remaining) == {"type_of_package"}
    assert remaining["type_of_package"]["required"] is False


def test_a_changed_choice_replaces_the_previous_one():
    """A chosen composition is this application's own writing and may be
    replaced when the consignor picks differently."""
    res = prepare({"un_number": "1202", "carriage_mode": "packages",
                   "net_mass_liters_per_package": "25 L",
                   "proper_shipping_name": "DIESELOLIE (DIESEL FUEL)",
                   "chosen_name": "GASOLIE", "chosen_name_en": "GAS OIL"})
    assert (res["entries"][0]["products"][0]["proper_shipping_name"]
            == "GASOLIE (GAS OIL)")


def test_the_consignor_s_own_wording_is_never_overwritten():
    res = prepare({"un_number": "1202", "carriage_mode": "packages",
                   "net_mass_liters_per_package": "25 L",
                   "proper_shipping_name": "DIESELOLIE (eigen toevoeging)",
                   "chosen_name": "GASOLIE", "chosen_name_en": "GAS OIL"})
    assert (res["entries"][0]["products"][0]["proper_shipping_name"]
            == "DIESELOLIE (eigen toevoeging)")


def test_an_english_only_profile_asks_the_english_choice_alone():
    q = questions_by_field(prepare({"un_number": "1202"}, profiles=("IMDG",)))
    assert "chosen_name" not in q
    assert q["chosen_name_en"]["options"] == ["GAS OIL", "DIESEL FUEL", "HEATING OIL, LIGHT"]


def test_a_german_document_asks_its_own_names_and_no_english():
    q = questions_by_field(prepare({"un_number": "1202", "carriage_mode": "packages",
                                    "net_mass_liters_per_package": "25 L"},
                                   language="de"))
    assert q["chosen_name"]["options"] == ["DIESELKRAFTSTOFF", "GASÖL", "HEIZÖL, LEICHT"]
    assert "chosen_name_en" not in q


def test_a_packaging_code_becomes_a_supplement_to_the_description():
    """5.4.1.1.1 (e): the code only as a supplement — "jerrycan (3H1)",
    never "3H1 jerrycan". A value that merely looks like a code stays."""
    assert (_package_description("3H1 Kunststof jerrycan, niet-afneembaar deksel")
            == "Kunststof jerrycan, niet-afneembaar deksel (3H1)")
    assert _package_description("25 L vaten") == "25 L vaten"
    assert _package_description("jerrycans") == "jerrycans"


def test_the_cmr_keeps_the_whole_line_legible_even_without_a_choice(synthetic_templates):
    """5.4.1.1.2: the information must be legible. Even when no name was
    chosen and the full column goes on, the goods box wraps onto following
    rows instead of clipping — the tunnel code stays on the paper."""
    res = prepare({"un_number": "1202", "carriage_mode": "packages",
                   "net_mass_liters_per_package": "25 L"})
    lines = [{"line_id": 1, "description": "dieselolie", "output_description": "dieselolie",
              "quantity": 1000, "unit": "jerrycan", "include": True,
              "weight_total_kg": 21000.0, "messages": [], "status": "ok"}]
    values = {"consignor_name": "A", "consignor_address": "B",
              "consignee_name": "C", "consignee_address": "D",
              "loading_point": "Rotterdam", "discharge_point": "Duisburg",
              "freight_payment": "Franco", "established_place": "Rotterdam",
              "established_date": "2026-08-15"}
    path = fill_pdf_document("cmr", values, lines, res["entries"], "nl")
    try:
        with fitz.open(str(path)) as doc:
            text = " ".join(page.get_text() for page in doc).replace("\n", " ")
        assert "(D/E)" in text
        assert "III" in text
        assert "25000 L" in text
    finally:
        path.unlink(missing_ok=True)
