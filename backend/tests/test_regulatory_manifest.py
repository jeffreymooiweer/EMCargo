"""The manifest has to match what the app really uses.

A manifest that stands apart from the data is worse than no manifest: it inspires
confidence that rests on nothing. These tests bind it to the seeds that really
exist, and record that an expired edition becomes visible instead of quietly
being computed with.
"""

from datetime import date

import pytest

from app.services.regulatory_manifest import (
    RULE_SETS,
    build_manifest,
    expired_rule_sets,
    rule_set_status,
    summary,
)


def rule_set(key: str) -> dict:
    return next(r for r in RULE_SETS if r["key"] == key)


def test_every_rule_set_names_its_edition_and_where_it_came_from():
    for entry in RULE_SETS:
        assert entry["edition"], entry["key"]
        assert entry["source"], entry["key"]
        assert entry["valid_from"], entry["key"]
        assert entry["covers"] or entry.get("retired"), entry["key"]


def test_every_file_a_rule_set_claims_actually_exists():
    """A checksum over a file that is not there is not a check."""
    manifest = build_manifest()
    for entry, reported in zip(RULE_SETS, manifest["rule_sets"]):
        assert len(reported["datasets"]) == len(entry["files"]), entry["key"]


def test_the_checksum_covers_the_content_and_not_the_timestamp():
    """Two installations with the same data have to report the same id; a build
    timestamp would make them look different."""
    assert build_manifest()["manifest_id"] == build_manifest()["manifest_id"]


def test_the_dangerous_goods_list_is_the_edition_the_manifest_claims():
    """The manifest and the data file must not drift apart."""
    from app.services.dg import dangerous_goods_list as dgl

    assert dgl.source()["amendment"] == "42-24"
    assert "42-24" in rule_set("imdg")["edition"]


def test_the_iata_edition_matches_the_compliance_rules():
    """The rules cite their edition in the text; that has to be the same one."""
    from app.services.dg.compliance import get_compliance_rules

    sources = get_compliance_rules()["sources"]
    assert any("67" in str(v) for v in sources.values())
    assert "67" in rule_set("iata")["edition"]


# --- Geldigheid ----------------------------------------------------------------

def test_a_rule_set_is_current_between_its_dates():
    entry = {"valid_from": "2026-01-01", "valid_until": "2026-12-31"}
    assert rule_set_status(entry, date(2026, 6, 1)) == "current"


def test_a_rule_set_that_has_not_started_says_so():
    entry = {"valid_from": "2027-01-01", "valid_until": None}
    assert rule_set_status(entry, date(2026, 8, 3)) == "not_yet_in_force"


def test_an_expired_rule_set_is_reported_rather_than_used_quietly():
    """The IATA DGR is replaced annually. On 1 January 2027 this app computes
    with an expired edition; that should be visible."""
    assert rule_set_status(rule_set("iata"), date(2026, 12, 31)) == "current"
    assert rule_set_status(rule_set("iata"), date(2027, 1, 1)) == "expired"
    assert "iata" in expired_rule_sets(date(2027, 1, 1))


def test_a_circular_without_an_end_date_never_expires():
    """The EmS Guide is a circular: it applies until a Rev.4 appears, not until
    a date."""
    assert rule_set("ems")["valid_until"] is None
    assert rule_set_status(rule_set("ems"), date(2099, 1, 1)) == "current"


def test_the_un_cards_are_openly_marked_as_superseded():
    """41-22 ran out at the end of 2025 and the cards are used for only two
    things now. Keeping quiet about that would suggest everything is 42-24."""
    cards = rule_set("imdg_un_cards")
    assert rule_set_status(cards, date(2026, 8, 3)) == "expired"
    assert any("16a" in note for note in cards["errata"])
    assert any("2984" in note for note in cards["errata"])


# --- Wat de endpoints uitdragen -------------------------------------------------

def test_the_summary_is_small_enough_for_the_health_endpoint():
    compact = summary()
    assert set(compact) == {"manifest_id", "editions", "expired"}
    assert len(str(compact)) < 800


def test_the_summary_and_the_full_manifest_agree():
    today = date(2026, 8, 3)
    assert summary(today)["manifest_id"] == build_manifest(today)["manifest_id"]
    assert summary(today)["expired"] == expired_rule_sets(today)


def test_the_manifest_carries_the_application_version():
    from app.version import get_version

    assert build_manifest()["application_version"] == get_version()


def test_the_manifest_repeats_that_the_published_code_is_what_counts():
    assert "authoritative" in build_manifest()["disclaimer"]


@pytest.mark.parametrize("key", [entry["key"] for entry in RULE_SETS])
def test_no_rule_set_key_is_duplicated(key):
    assert [entry["key"] for entry in RULE_SETS].count(key) == 1


def test_the_adr_rule_set_credits_the_book_and_not_the_export():
    """Provenance the user is shown must not lag the data.

    Table A came out of an export until v1.56.0 and out of the official Dutch
    edition after it, with the export reduced to the English and German names.
    The `rule_sets` label kept crediting the export for the whole table for five
    releases — a claim about where a regulatory fact came from, and wrong.
    """
    from app.services.dg.compliance import check_compliance

    label = check_compliance(
        [{"line_id": "L1", "products": [{"un_number": "1203", "class": "3"}]}],
        ["ADR"], "nl")["rule_sets"]["ADR"]
    assert "Dutch edition" in label
    assert "extract_adr_table_a" in label
    assert "Table A via" not in label
