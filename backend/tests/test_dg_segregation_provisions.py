"""Tests for the IMDG column 16b segregation provisions.

The class segregation table of 7.2.4 works on class. Column 16b adds provisions
per *substance* — "stow separated from acids" — which the app now knows for 840
UN numbers. The meaning of each SG code is read from the IMDG 7.2.8 source rather
than typed from memory, because a wrong segregation rule is a safety-relevant
error, not a cosmetic one.

These tests pin the parsed rules and the behaviour that follows from them.
"""

import pytest

from app.services.dg.compliance import check_imdg_segregation_provisions
from app.services.dg.enrichment import imdg_segregation_codes_for, segregation_provisions


def shipment(*products):
    return [{"line_id": 1, "products": list(products)}]


def codes(warnings):
    return sorted(w["rule"] for w in warnings)


@pytest.fixture(scope="module")
def rules():
    return segregation_provisions()


def test_provisions_include_codes_previously_absent_from_the_cards(rules):
    for code, group in (("SG51", "SGG8"), ("SG56", "SGG12"), ("SG58", "SGG13")):
        assert rules[code]["targets"] == {"groups": [group]}
    assert rules["SG67"]["manual_review"] is True


def test_a_provision_naming_a_class_is_actionable(rules):
    assert rules["SG17"]["action"] == "separated_from"
    assert rules["SG17"]["targets"] == {"classes": ["5.1"]}


def test_a_provision_naming_a_segregation_group_is_actionable(rules):
    assert rules["SG35"]["action"] == "separated_from"
    assert rules["SG35"]["targets"] == {"groups": ["SGG1"]}


def test_a_foodstuff_provision_does_not_parse_into_a_pairwise_rule(rules):
    """"as in 7.3.4.2.2" is a cross-reference; it is handled as a cargo
    requirement instead — see test_a_foodstuff_provision_is_raised_on_its_own."""
    assert rules["SG29"]["informational"] is True


def test_an_exception_is_read_as_an_exception_not_a_second_target(rules):
    """"class 1 except for division 1.4S" — 1.4S is excluded, not targeted."""
    assert rules["SG14"]["targets"] == {"classes": ["1"]}
    assert rules["SG14"]["excepted_classes"] == ["1.4S"]


def test_ammonia_next_to_an_acid_is_reported():
    """UN 1005 carries SG35: stow separated from acids. UN 1789 is one."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1005", "class": "2.3"}, {"un_number": "1789", "class": "8"}), "nl"
    )
    assert "IMDG 16b (SG35)" in codes(warnings)
    message = next(w for w in warnings if w["rule"] == "IMDG 16b (SG35)")["message"]
    # The group is named, not just coded, and the card's own wording follows.
    assert "SGG1 (Zuren)" in message
    assert "separated from" in message


def test_the_provision_is_applied_in_both_directions():
    """The acid also has to be kept away from the alkali, and says so itself."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1005", "class": "2.3"}, {"un_number": "1789", "class": "8"}), "nl"
    )
    assert codes(warnings) == ["IMDG 16b (SG35)", "IMDG 16b (SG36)"]
    pairs = {w["rule"]: w["products"] for w in warnings}
    assert pairs["IMDG 16b (SG35)"].startswith("UN 1005")
    assert pairs["IMDG 16b (SG36)"].startswith("UN 1789")


def test_a_class_target_is_matched_on_the_declared_class():
    """UN 1017 chlorine carries SG19: separated from class 7."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1017", "class": "2.3"}, {"un_number": "2912", "class": "7"}), "nl"
    )
    assert "IMDG 16b (SG19)" in codes(warnings)


def test_an_excepted_class_is_not_reported():
    """SG14 excludes division 1.4S; warning about it would be plain wrong."""
    with_11d = check_imdg_segregation_provisions(
        shipment({"un_number": "2211", "class": "9"}, {"un_number": "0004", "class": "1.1D"}), "nl"
    )
    with_14s = check_imdg_segregation_provisions(
        shipment({"un_number": "2211", "class": "9"}, {"un_number": "0012", "class": "1.4S"}), "nl"
    )
    assert "IMDG 16b (SG14)" in codes(with_11d)
    assert "IMDG 16b (SG14)" not in codes(with_14s)


def test_a_bare_class_target_covers_its_divisions():
    """"separated from class 1" applies to 1.1D as much as to 1.3G."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "2211", "class": "9"}, {"un_number": "0331", "class": "1.1D"}), "nl"
    )
    assert "IMDG 16b (SG14)" in codes(warnings)


def test_subsidiary_risks_count_towards_a_class_target():
    warnings = check_imdg_segregation_provisions(
        shipment(
            {"un_number": "1017", "class": "2.3"},
            {"un_number": "9999", "class": "8", "subsidiary_risks": "7"},
        ),
        "nl",
    )
    assert "IMDG 16b (SG19)" in codes(warnings)


def test_a_single_substance_raises_nothing():
    assert check_imdg_segregation_provisions(shipment({"un_number": "1005", "class": "2.3"}), "nl") == []


def test_two_acids_together_are_not_reported():
    """Neither nitric nor hydrochloric acid must be kept from acids."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "2031", "class": "8"}, {"un_number": "1789", "class": "8"}), "nl"
    )
    assert "IMDG 16b (SG35)" not in codes(warnings)
    assert imdg_segregation_codes_for("2031") == [
        "SG6", "SG16", "SG17", "SG19", "SG36", "SG49"
    ]


def test_english_reports_the_same_finding():
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "1005", "class": "2.3"}, {"un_number": "1789", "class": "8"}), "en"
    )
    message = next(w for w in warnings if w["rule"] == "IMDG 16b (SG35)")["message"]
    assert message.startswith("Stow separated from SGG1 (Acids)")


# --- Provisions that name a substance instead of a class or group -------------
# The wording ("separated from sulphur") is resolved to UN numbers in
# dg_compliance.json, deliberately narrowly: sulphur means elemental sulphur,
# not sulphur dioxide.

def test_a_provision_naming_a_substance_is_matched_on_its_un_number():
    """UN 2427 carries SG62: separated from sulphur. UN 1350 is sulphur."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "2427", "class": "5.1"}, {"un_number": "1350", "class": "4.1"}), "nl"
    )
    assert "IMDG 16b (SG62)" in codes(warnings)


def test_a_named_substance_provision_stays_silent_for_a_related_compound():
    """Sulphur dioxide (UN 1079) is not the sulphur SG62 means."""
    warnings = check_imdg_segregation_provisions(
        shipment({"un_number": "2427", "class": "5.1"}, {"un_number": "1079", "class": "2.3"}), "nl"
    )
    assert "IMDG 16b (SG62)" not in codes(warnings)


def test_a_provision_naming_an_explicit_un_number():
    """SG44 spells it out: separated from CARBON TETRACHLORIDE (UN 1846)."""
    from app.services.dg.compliance import get_compliance_rules

    target = get_compliance_rules()["imdg_segregation_named_targets"]["SG44"]
    assert target["un"] == ["1846"]
    assert "1846" in segregation_provisions()["SG44"]["text"]


def test_a_group_stand_in_admits_that_it_is_broader():
    """SG22 says "ammonium salts"; SGG2 is ammonium compounds — wider."""
    import json as _json
    from pathlib import Path as _Path

    entries = _json.loads(
        (_Path(__file__).resolve().parents[1] / "seed" / "dg" / "imdg_dgl.json").read_text(encoding="utf-8")
    )["entries"]
    source = next(e["un_number"] for e in entries if "SG22" in (e.get("segregation") or "").split())
    warnings = check_imdg_segregation_provisions(
        shipment(
            {"un_number": source, "class": "5.1"},
            {"un_number": "1442", "class": "5.1", "segregation_group": "SGG2"},
        ),
        "nl",
    )
    hit = next((w for w in warnings if w["rule"] == "IMDG 16b (SG22)"), None)
    assert hit is not None
    assert "ruimer is dan de tekst" in hit["message"]


# --- Provisions whose target is ordinary cargo --------------------------------
# EMCargo does not know what non-dangerous cargo travels alongside, so these
# are raised whenever the substance is present, like the ADR CV28 warning.

def test_a_foodstuff_provision_is_raised_on_its_own():
    warnings = check_imdg_segregation_provisions(shipment({"un_number": "1111", "class": "6.1"}), "nl")
    assert "IMDG 16b (SG50)" in codes(warnings)
    message = next(w for w in warnings if w["rule"] == "IMDG 16b (SG50)")["message"]
    assert "levensmiddelen" in message


def test_a_conditional_cargo_provision_needs_its_class_present():
    """SG26 only bites next to class 2.1 or 3."""
    import json as _json
    from pathlib import Path as _Path

    entries = _json.loads(
        (_Path(__file__).resolve().parents[1] / "seed" / "dg" / "imdg_dgl.json").read_text(encoding="utf-8")
    )["entries"]
    source = next(e["un_number"] for e in entries if "SG26" in (e.get("segregation") or "").split())

    alone = check_imdg_segregation_provisions(shipment({"un_number": source, "class": "5.1"}), "nl")
    beside_flammable = check_imdg_segregation_provisions(
        shipment({"un_number": source, "class": "5.1"}, {"un_number": "1203", "class": "3"}), "nl"
    )
    assert "IMDG 16b (SG26)" not in codes(alone)
    assert "IMDG 16b (SG26)" in codes(beside_flammable)


def test_segregation_as_for_a_division_without_the_word_class(rules):
    """SG74 reads "Segregation as for 1.4G" — no "class", but still a rule."""
    assert rules["SG74"]["action"] == "segregate_as_class"
    assert rules["SG74"]["as_class"] == "1.4G"


def test_only_definitions_and_table_references_remain_as_text(rules):
    """Six provisions are not rules at all and are shown, not checked."""
    from app.services.dg.compliance import get_compliance_rules

    config = get_compliance_rules()
    named = set(config["imdg_segregation_named_targets"]) - {"_comment"}
    cargo = set(config["imdg_segregation_cargo_requirements"]) - {"_comment"}
    checkable = {
        code for code, rule in rules.items()
        if rule.get("targets") or rule.get("as_class") or rule.get("manual_review")
    } | named | cargo
    assert set(rules) - checkable == {"SG48", "SG52", "SG71", "SG72"}


# --- IMDG 7.2.6.3: the exemption SG72 points at ------------------------------
# Read from chapter 7.2 of Amendment 40-20, the same edition as the class table.
# It relaxes segregation rather than tightening it, which is the opposite of
# what the bare code "See tables in 7.2.6.3" suggests.

def test_two_substances_from_the_same_table_are_reported_as_exempt():
    from app.services.dg.compliance import check_imdg_segregation_exemptions

    findings = check_imdg_segregation_exemptions(
        shipment({"un_number": "3101", "class": "5.2"}, {"un_number": "3103", "class": "5.2"}), "nl"
    )
    assert [f["rule"] for f in findings] == ["IMDG 7.2.6.3.4"]
    assert findings[0]["severity"] == "info"
    assert "geen scheiding" in findings[0]["message"]


def test_table_four_carries_the_caveat_of_7_2_6_4():
    from app.services.dg.compliance import check_imdg_segregation_exemptions

    findings = check_imdg_segregation_exemptions(
        shipment({"un_number": "3101", "class": "5.2"}, {"un_number": "3103", "class": "5.2"}), "nl"
    )
    assert "7.2.6.4" in findings[0]["message"]


def test_substances_from_different_tables_are_not_exempt():
    """The exemption is within a table, not across them."""
    from app.services.dg.compliance import check_imdg_segregation_exemptions

    assert check_imdg_segregation_exemptions(
        shipment({"un_number": "2014", "class": "5.1"}, {"un_number": "1818", "class": "8"}), "nl"
    ) == []


def test_the_exemption_never_removes_a_warning():
    """A finding and its exemption are both shown; suppressing would hide risk."""
    from app.services.dg.compliance import (
        check_imdg_segregation_exemptions,
        check_imdg_segregation_provisions,
    )

    load = shipment({"un_number": "2014", "class": "5.1"}, {"un_number": "3149", "class": "5.1"})
    exemptions = check_imdg_segregation_exemptions(load, "nl")
    # Both are in table 7.2.6.3.1, so the exemption applies …
    assert [f["rule"] for f in exemptions] == ["IMDG 7.2.6.3.1"]
    # … and whatever column 16b says is still reported, unchanged.
    provisions = check_imdg_segregation_provisions(load, "nl")
    assert all(w["severity"] == "warning" for w in provisions)


def test_the_tables_match_the_code():
    """Pinned verbatim from Amendment 40-20, chapter 7.2."""
    from app.services.dg.compliance import get_compliance_rules

    tables = get_compliance_rules()["imdg_segregation_exemptions"]["tables"]
    assert tables["7.2.6.3.1"] == ["2014", "2984", "3105", "3107", "3109", "3149"]
    assert tables["7.2.6.3.2"] == ["1295", "1818", "2189"]
    assert len(tables["7.2.6.3.3"]) == 10 and tables["7.2.6.3.3"][0] == "3391"
    assert len(tables["7.2.6.3.4"]) == 21 and tables["7.2.6.3.4"][0] == "1325"
