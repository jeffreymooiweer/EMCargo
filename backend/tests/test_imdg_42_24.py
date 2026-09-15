"""IMDG Code Amendment 42-24: the differences layer and the precedence rule 7.2.3.1.

The app carries ADR 2025 as its base table and the 41-22 UN cards as its
substance-specific IMDG layer. Since 1 January 2026, 42-24 is mandatory. These
tests record what the layer does — and, just as importantly, what it does not do:
it never silently adjusts a classification and never removes a message.
"""

import json
from pathlib import Path

import pytest

from app.services.dg import amendment_42_24
from app.services.dg.compliance import apply_column_16b_precedence, check_compliance
from app.services.dg.database import offline_lookup, search_un_numbers
from app.services.dg.enrichment import segregation_groups_for

SEED = Path(__file__).resolve().parents[1] / "seed" / "dg"


def product(un: str, **overrides):
    entry = offline_lookup(un) or {}
    base = {
        "un_number": un,
        "proper_shipping_name": entry.get("proper_shipping_name"),
        "class": entry.get("class"),
        "subsidiary_risks": entry.get("subsidiary_risks"),
        "packing_group": entry.get("packing_group"),
        "quantity_packages": "1",
    }
    return {**base, **overrides}


def imdg(*uns, language="nl"):
    entries = [{"line_id": 1, "products": [product(un) for un in uns]}]
    return check_compliance(entries, ["IMDG"], language)


# --- The layer itself --------------------------------------------------------

def test_the_amendment_layer_names_its_edition_and_source():
    assert amendment_42_24.amendment() == "42-24"
    assert "Hazcheck" in amendment_42_24.source()


def test_the_class_tables_are_confirmed_unchanged_in_42_24():
    """For chapter 7.2 the source names one change: 7.2.6.1. The tables this app
    computes with are not among them and therefore apply in full."""
    sections = amendment_42_24.verified_unchanged_sections()
    assert {"7.2.4", "7.2.6.3", "7.2.7.1.4", "3.1.4.4"} <= set(sections)
    amended = {item["section"] for item in amendment_42_24.amended_sections()}
    assert "7.2.6.1" in amended
    assert not amended & set(sections)


def test_the_layer_says_what_it_does_not_cover():
    assert amendment_42_24.not_covered("nl")
    assert amendment_42_24.not_covered("en")


# --- Nieuwe UN-nummers -------------------------------------------------------

def test_the_new_42_24_un_numbers_are_findable():
    """Sodium-ion batteries are in IMDG 42-24 and not in the Table A export the
    app was built on, which is a 2023 one. ADR 2025 does know them — the Dutch
    edition lists UN 3551 as NATRIUM-ION BATTERIJEN — but their road data has
    not been read out yet, so for now they carry only what the sea code says.
    Whoever ships them has to be able to look them up either way."""
    hits = {r["un"] for r in search_un_numbers("sodium ion", 10)}
    assert {"3551", "3552", "3558"} <= hits


def test_a_new_un_number_carries_its_ems_and_says_where_it_comes_from():
    entry = offline_lookup("3553")
    # The Dutch name comes from ADR 2025 even though the rest of the entry comes
    # from the sea code: the two seeds are separate on purpose.
    assert entry["proper_shipping_name"] == "DISILAAN (DISILANE)"
    assert entry["class"] == "2.1"
    assert entry["ems_code"] == "F-D, S-U"
    assert "42-24" in entry["source"]


def test_every_new_un_number_has_a_class_and_an_ems_schedule():
    ems = amendment_42_24.ems_additions()
    for item in amendment_42_24.new_un_numbers():
        assert item.get("class"), item["un"]
        assert item["un"] in ems, item["un"]
        assert ems[item["un"]]["fire"].startswith("F-")
        assert ems[item["un"]]["spillage"].startswith("S-")


def test_the_new_entries_never_shadow_an_existing_adr_entry():
    seeded = {e["un"] for e in json.loads((SEED / "un_numbers.json").read_text("utf-8"))}
    assert not seeded & {i["un"] for i in amendment_42_24.new_un_numbers()}


# --- Gewijzigde stoffen ------------------------------------------------------

def test_isopropenylbenzene_became_a_marine_pollutant():
    """UN 2303 gets a 'P' in column 4 and SW1 added in 42-24."""
    entry = offline_lookup("2303")
    assert entry["marine_pollutant_status"] == "yes"
    assert "SW1" in entry["imdg_stowage_codes"]
    assert entry["environmentally_hazardous"] is True


def test_carbon_keeps_its_old_stowage_code_and_gains_the_new_one():
    """Adding, not replacing: SW1 was already there, SW27 is added.

    Since column 16a comes from the Dangerous Goods List itself, H2 is there too.
    That is a handling code from the same column (7.1.6) that the UN card did not
    name — not a shift but what is actually there.
    """
    codes = offline_lookup("1361")["imdg_stowage_codes"]
    assert codes == ["SW1", "SW27", "H2"]


def test_carbon_carries_the_new_document_requirement():
    requirement = offline_lookup("1361")["imdg_document_requirement"]
    assert requirement["section"] == "5.4.1.5.18"
    assert "productiedatum" in requirement["text"]
    assert "ambient_temperature_c" in requirement["fields"]


def test_a_reclassified_substance_is_reported_and_not_silently_rewritten():
    """UN 3423 became class 6.1 with subsidiary risk 8 in 42-24 — and, it turns
    out, in ADR 2025 as well.

    This test was written when the two disagreed: the sea code had moved the
    substance and the road table this app ran on, a 2023 export, still called it
    class 8. The point of it was that the app must not quietly rewrite the road
    class on the strength of the sea layer. It still must not. What changed in
    v1.56.0 is the road table, which is now the 2025 edition and says 6.1 of its
    own accord — so the two agree, and the reported change is now a statement
    about the layer rather than a contradiction of it."""
    entry = offline_lookup("3423")
    assert entry["class"] == "6.1"  # ADR 2025, read from the book
    assert any("6.1" in line for line in entry["imdg_amendment_changes"])

    findings = imdg("3423")["imdg_segregation"]
    classification = [f for f in findings if "classificatie" in f["rule"]]
    assert len(classification) == 1
    assert classification[0]["severity"] == "warning"


def test_changes_are_reported_per_packing_group_where_they_differ():
    """UN 1835 changes per packing group: only group II gets 6.1."""
    two = amendment_42_24.changes_for("1835", "II", "nl")
    three = amendment_42_24.changes_for("1835", "III", "nl")
    assert any("6.1" in line for line in two)
    assert not any("6.1" in line for line in three)
    # Without a packing group, never the stricter variant.
    assert not any("6.1" in line for line in amendment_42_24.changes_for("1835", "", "nl"))


def test_the_changes_are_available_in_english():
    assert amendment_42_24.changes_for("2303", "", "en") != amendment_42_24.changes_for("2303", "", "nl")
    assert any("marine pollutant" in line for line in amendment_42_24.changes_for("2303", "", "en"))


def test_an_unaffected_substance_gets_no_amendment_noise():
    assert amendment_42_24.changes_for("1203") == []
    assert "imdg_amendment_changes" not in offline_lookup("1203")


# --- 7.2.3.1: column 16b takes precedence ------------------------------------

def test_column_16b_takes_precedence_over_the_class_table():
    """Nitric acid × sulphur: the table says 'away from' (1), but SG16 of nitric
    acid says 'separated from' (2). 7.2.3.1 leaves no doubt which of the two
    applies."""
    findings = imdg("2031", "1350")["imdg_segregation"]
    table = next(f for f in findings if f["rule"].startswith("IMDG 7.2.4"))
    sg16 = next(f for f in findings if "SG16" in f["rule"])

    assert table["superseded_by"] == [sg16["rule"]] or sg16["rule"] in table["superseded_by"]
    assert "7.2.3.1" in table["message"]
    assert table["severity"] == "info"
    assert "7.2.3.1" in sg16["message"]
    assert table["rule"] in sg16["takes_precedence_over"]


def test_the_superseded_finding_is_annotated_and_never_removed():
    findings = imdg("2031", "1350")["imdg_segregation"]
    assert any(f["rule"].startswith("IMDG 7.2.4") for f in findings)


def test_without_a_conflicting_16b_provision_the_table_stands():
    """Hydrochloric acid carries no SG16; then the table value simply stands."""
    findings = imdg("1789", "1350")["imdg_segregation"]
    table = next(f for f in findings if f["rule"].startswith("IMDG 7.2.4"))
    assert "superseded_by" not in table
    assert table["severity"] == "warning"


def test_agreement_between_the_two_is_not_reported_as_a_conflict():
    findings = apply_column_16b_precedence([
        {"rule": "IMDG 7.2.4 (8 × 4.1)", "severity": "warning", "code": "2",
         "message": "x", "products": "A  ×  B", "source": "table", "pair": "A|B"},
        {"rule": "IMDG 16b (SG16)", "severity": "warning", "code": "2",
         "message": "y", "products": "A  ×  B", "source": "column_16b", "pair": "A|B"},
    ], "nl")
    assert "superseded_by" not in findings[0]
    assert findings[0]["message"] == "x"


def test_all_provisions_at_the_strictest_level_carry_the_precedence():
    """Two SG codes of equal weight on the same pair: both take precedence, so
    both get named."""
    findings = apply_column_16b_precedence([
        {"rule": "IMDG 7.2.4 (8 × 4.1)", "severity": "warning", "code": "1",
         "message": "x", "products": "A  ×  B", "source": "table", "pair": "A|B"},
        {"rule": "IMDG 16b (SG16)", "severity": "warning", "code": "2",
         "message": "y", "products": "A  ×  B", "source": "column_16b", "pair": "A|B"},
        {"rule": "IMDG 16b (SG17)", "severity": "warning", "code": "2",
         "message": "z", "products": "B  ×  A", "source": "column_16b", "pair": "A|B"},
    ], "nl")
    assert all("7.2.3.1" in f["message"] for f in findings[1:])
    assert set(findings[0]["superseded_by"]) == {"IMDG 16b (SG16)", "IMDG 16b (SG17)"}


def test_a_stricter_16b_provision_raises_the_severity_to_error():
    findings = apply_column_16b_precedence([
        {"rule": "IMDG 7.2.4 (3 × 5.1)", "severity": "warning", "code": "1",
         "message": "x", "products": "A  ×  B", "source": "table", "pair": "A|B"},
        {"rule": "IMDG 16b (SG9)", "severity": "warning", "code": "4",
         "message": "y", "products": "A  ×  B", "source": "column_16b", "pair": "A|B"},
    ], "nl")
    assert findings[1]["severity"] == "error"
    assert findings[0]["severity"] == "info"


# --- SGG1a no longer exists --------------------------------------------------

def test_sgg1a_is_gone_from_the_segregation_groups():
    """The separate marking for strong acids lapsed with 41-22 and 42-24 leaves
    3.1.4.4 unchanged. It must not turn up anywhere any more."""
    seed = json.loads((SEED / "segregation_groups.json").read_text("utf-8"))
    assert not any("SGG1a" in codes for codes in seed["by_un"].values())
    assert all(group.get("alt_code") is None for group in seed["groups"])
    assert segregation_groups_for("1789") == ["SGG1"]


def test_the_group_counts_match_the_entries():
    seed = json.loads((SEED / "segregation_groups.json").read_text("utf-8"))
    for group in seed["groups"]:
        actual = sum(1 for codes in seed["by_un"].values() if group["code"] in codes)
        assert group["count"] == actual, group["code"]


# --- What every outcome says about its own editions --------------------------

def test_every_result_names_the_editions_it_used():
    rule_sets = imdg("1203")["rule_sets"]
    assert "42-24" in rule_sets["IMDG_current_mandatory"]
    assert "NIET geladen" not in rule_sets["IMDG_current_mandatory"]
    assert "7.2.4" in rule_sets["IMDG_class_tables"]
    assert rule_sets["IMDG_42_24_not_covered"]
    assert "Hazcheck" in rule_sets["IMDG_42_24_source"]


@pytest.mark.parametrize("language", ["nl", "en"])
def test_the_edition_metadata_survives_both_languages(language):
    rule_sets = imdg("1203", language=language)["rule_sets"]
    assert rule_sets["IMDG_42_24_not_covered"]


# --- The code table from chapters 7.1.5, 7.1.6 and 7.2.8 ---------------------

def test_the_code_table_is_complete():
    """SW1-SW31, H1-H5 and SG1-SG78. The only real gaps are SG64, SG66 and SG73
    (reserved) and SG75, which lapsed with 41-22 — just like SGG1a."""
    table = json.loads((SEED / "imdg_codes.json").read_text("utf-8"))
    assert table["amendment"] == "42-24"

    stowage = table["stowage_codes"]["codes"]
    assert len(stowage) == 31 and "SW31" in stowage

    assert len(table["handling_codes"]["codes"]) == 5

    segregation = table["segregation_codes"]
    assert table["segregation_codes"]["reserved"] == ["SG64", "SG66", "SG73"]
    numbers = {int(c[2:]) for c in segregation["codes"]}
    assert 75 not in numbers
    assert set(range(1, 79)) - numbers - {64, 66, 73} == {75}


def test_a_reserved_code_carries_no_guidance():
    from app.services.dg.enrichment import imdg_code_text
    assert imdg_code_text("SG64") == ""
    assert imdg_code_text("SG65").startswith("Stow")


def test_the_official_wording_reaches_the_substance():
    """Nitric acid carries SG16; the user has to be able to read what that means."""
    definitions = offline_lookup("2031")["imdg_segregation_definitions"]
    by_code = {d["code"]: d["text"] for d in definitions}
    assert by_code["SG16"] == "Stow “separated from” class 4.1."


def test_official_wording_is_the_only_rule_text():
    """7.2.8 supplies the rule text after retirement of the separate card paraphrase."""
    from app.services.dg.compliance import _wording
    from app.services.dg.enrichment import segregation_provisions
    rules = segregation_provisions()
    assert _wording("SG16", rules) == "Stow “separated from” class 4.1."
    assert _wording("SG16", rules) == rules.get("SG16", {}).get("text")


def test_an_unknown_code_falls_back_instead_of_going_blank():
    from app.services.dg.compliance import _wording
    assert _wording("SG999", {"SG999": {"text": "from the card"}}) == "from the card"
    assert _wording("SG999", {}) == ""
