"""The retired card set must never silently supply safety-critical defaults."""
from pathlib import Path
from app.services.dg.enrichment import enrich_un_entry, imdg_segregation_codes_for
from app.services.dg.source_verification import findings


def test_retired_source_is_absent():
    assert not (Path(__file__).resolve().parents[1] / "seed/dg/card_data.json").exists()


def test_current_dgl_keeps_chlorine_codes_without_card_prose():
    extras = enrich_un_entry({"un": "1017", "class": "2", "labels": "2.3"}, "en")
    assert extras["imdg_stowage_codes"] == ["SW2"]
    assert extras["imdg_segregation_codes"] == ["SG6", "SG19"]
    assert extras["marine_pollutant_status"] == "yes"
    assert "imdg_stowage_text" not in extras
    assert "card_source" not in extras


def test_absent_p_mark_is_unknown_not_a_negative_assessment():
    extras = enrich_un_entry({"un": "1203", "class": "3"}, "en")
    assert extras["marine_pollutant_status"] == "unknown"
    assert extras["imdg_bulk_status"] == "unknown"
    assert "imdg_bulk_forbidden" not in extras
    assert imdg_segregation_codes_for("9999") == []


def checks(**changes):
    product = {"un_number": "1203", "packing_group": "II", **changes}
    return findings([{"line_id": 1, "products": [product]}])


def test_blank_negative_and_legacy_autofill_all_require_a_source():
    for value in ("", "N", "P"):
        assert checks(marine_pollutant=value)


def test_explicit_source_assessment_can_resolve_the_gap():
    assert checks(marine_pollutant="N", imdg_source_reference="SDS section 14, product A, 2026-09-01",
                  imdg_source_reviewed="Y") == []


def test_a_checkbox_without_a_source_cannot_resolve_a_gap():
    assert checks(marine_pollutant="N", imdg_source_reviewed="Y")


def test_no_assessment_can_override_a_missing_dgl_row():
    assert checks(un_number="9999", marine_pollutant="N", imdg_source_reference="Example",
                  imdg_source_reviewed="Y")


def test_chlorine_cannot_be_declared_non_polluting_against_the_dgl():
    assert findings([{"products": [{"un_number": "1017", "marine_pollutant": "N",
                                   "imdg_source_reference": "Example", "imdg_source_reviewed": "Y"}]}])
