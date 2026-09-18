"""The IFTDGN notification: written to the D.16A segment table, and read back.

What is pinned here:

1. **The syntax.** Service characters in a value are released, trailing
   empties are dropped, and what is written parses back to what was meant.
2. **The structure.** A message built from a real shipment validates against
   the segment table; a message with a mandatory segment missing, a repeat
   exceeded or a segment out of order does not.
3. **The content.** The regulation, class, UN number, packing group, hazard
   identification number, labels, tunnel code, technical name and masses
   land in the segments and elements the directory names for them; a field
   left empty is absent; the consignee is not smuggled in.
4. **The export.** The document is offered on every modality beside the JSON
   export, refuses a shipment without dangerous goods with a sentence, and
   arrives as an ``.edi`` file through the ordinary export route.
5. **The directory.** When the D.16A files are at hand the structure in the
   config is checked against the message directory's own segment table, and
   the code values against the code list; otherwise that check is skipped.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.documents.registry import get_document, get_registry
from app.services.edifact import iftdgn
from app.services.edifact.syntax import Segment, parse, validate, write, write_segment
from tests.test_export_bundle import CONSIGNMENT, PRODUCT, client, doc, release

NOW = datetime(2026, 9, 6, 8, 30, tzinfo=timezone.utc)

VALUES = {
    **CONSIGNMENT,
    "consignor_address": "Havenweg 1\n3011 Rotterdam\nNederland",
    "carrier_name": "Transport O'Neill & Sons",
    "container_number": "MSKU1234565",
}
PETROL = {**PRODUCT, "labels": "3", "hazard_number": "33", "tunnel_code": "(D/E)",
          "flashpoint": "-40 °C", "gross_mass_per_package": "220", "quantity_packages": "4"}
ENTRIES = [{"line_id": "1", "vehicle": "UNIT-1", "products": [PETROL]}]


def message(values=VALUES, entries=ENTRIES, profiles=("ADR",), modality="road"):
    return iftdgn.build_segments(values, [], entries, profiles=list(profiles),
                                 modality=modality, now=NOW)


def by_tag(segments, tag):
    return [s for s in segments if s.tag == tag]


# --- 1. the syntax --------------------------------------------------------------


def test_service_characters_are_released_and_trailing_empties_dropped():
    text = write_segment(Segment("NAD", ["CZ", "", ["Havenweg 1", "3011 Rotterdam"], ["O'Neill + Sons: 100%?"], "", ""]))
    assert text == "NAD+CZ++Havenweg 1:3011 Rotterdam+O?'Neill ?+ Sons?: 100%??'"
    assert parse(text) == [Segment("NAD", ["CZ", "", ["Havenweg 1", "3011 Rotterdam"], "O'Neill + Sons: 100%?"])]


def test_the_interchange_starts_with_the_service_string_advice():
    text = write([Segment("UNB", [["UNOC", "3"], ["A"], ["B"], ["260906", "0830"], "1"])])
    assert text.startswith("UNA:+.? '\nUNB+UNOC:3+A+B+260906:0830+1'")


# --- 2. the structure -------------------------------------------------------------


def test_a_message_from_a_shipment_conforms_to_the_segment_table():
    segments = message()
    assert validate(segments, iftdgn.config()["structure"]) == []
    assert [s.tag for s in segments] == [
        "UNH", "BGM", "DTM", "TDT", "NAD", "EQD", "CNI", "LOC", "LOC", "NAD",
        "GID", "FTX", "DGS", "FTX", "MEA", "MEA", "SGP", "UNT"]
    assert segments[-1].elements == [str(len(segments)), "1"]


def test_the_validator_refuses_what_the_table_refuses():
    structure = iftdgn.config()["structure"]
    good = message()
    without_dgs = [s for s in good if s.tag != "DGS"]
    assert any("SG14" in e and "mandatory" in e for e in validate(without_dgs, structure))
    without_consignment = [s for s in good if s.tag not in ("CNI", "LOC", "GID", "FTX", "DGS", "MEA", "SGP")]
    without_consignment = [s for s in without_consignment if s.tag != "NAD" or s.elements[0] != "CZ"]
    assert any("SG7" in e for e in validate(without_consignment, structure))
    out_of_order = [good[1], good[0], *good[2:]]
    assert validate(out_of_order, structure)
    too_many = good[:2] + [Segment("DTM", [["137", "202609060830", "203"]])] * 10 + good[3:]
    assert any("more than 9" in e for e in validate(too_many, structure))


# --- 3. the content --------------------------------------------------------------


def test_the_header_names_the_message_and_the_shipment():
    segments = message()
    assert segments[0].elements == ["1", ["IFTDGN", "D", "16A", "UN"]]
    assert segments[1].elements == [["890"], ["CP-2026-100"], "9"]
    assert segments[2].elements == [["137", "202609060830", "203"]]
    tdt = by_tag(segments, "TDT")[0]
    assert tdt.elements[0] == "20" and tdt.elements[2] == ["3"]
    assert tdt.elements[7] == ["", "", "", "12-BXG-3"]


def test_the_parties_are_the_consignor_and_the_carrier_and_not_the_consignee():
    segments = message()
    nads = by_tag(segments, "NAD")
    assert [n.elements[0] for n in nads] == ["CA", "CZ"]
    consignor = nads[1]
    assert consignor.elements[2] == ["Havenweg 1", "3011 Rotterdam", "Nederland"]
    assert consignor.elements[3] == ["Afzender BV"]
    assert "Ontvanger GmbH" not in write(segments)


def test_the_consignment_and_its_places():
    segments = message()
    assert by_tag(segments, "CNI")[0].elements == ["1", ["CP-2026-100"]]
    locs = by_tag(segments, "LOC")
    assert locs[0].elements == ["9", ["", "", "", "Rotterdam"]]
    assert locs[1].elements == ["11", ["", "", "", "Duisburg"]]
    assert by_tag(segments, "EQD")[0].elements == ["CN", ["MSKU1234565"]]


def test_the_dangerous_goods_segment_carries_the_codes_the_directory_names():
    segments = message()
    dgs = by_tag(segments, "DGS")[0]
    assert dgs.elements[0] == "ADR"                       # 8273
    assert dgs.elements[1] == ["3", ""]                   # C205: class, no subsidiary
    assert dgs.elements[2] == ["1203"]                    # C234: UNDG
    assert dgs.elements[3] == ["-40", "CEL"]              # C223: flashpoint
    assert dgs.elements[4] == "2"                         # 8339: PG II
    assert dgs.elements[8] == ["33", "1203"]              # C235: orange placard
    assert dgs.elements[9] == ["3"]                       # C236: labels
    assert dgs.elements[13] == ["D/E"]                    # C289: tunnel code
    rendered = write_segment(dgs)
    assert rendered == "DGS+ADR+3+1203+-40:CEL+2++++33:1203+3++++D/E'"


def test_the_goods_item_its_names_and_its_masses():
    segments = message()
    gid = by_tag(segments, "GID")[0]
    assert gid.elements == ["1", ["4", "", "", "", "vaten"]]
    ftx = by_tag(segments, "FTX")
    assert ftx[0].elements[0] == "AAA" and ftx[0].elements[3] == ["Benzine"]
    assert ftx[1].elements[0] == "AAD" and ftx[1].elements[3] == ["Benzine"]
    meas = by_tag(segments, "MEA")
    assert meas[0].elements == ["AAE", ["AAB"], ["KGM", "880"]]
    assert meas[1].elements == ["AAE", ["AAF"], ["KGM", "800"]]
    assert by_tag(segments, "SGP")[0].elements == [["MSKU1234565"], "4"]


def test_what_is_empty_is_absent():
    bare = {"reference": "X-1", "consignor_name": "Afzender BV"}
    product = {"un_number": "1203", "class": "3", "adr_total_quantity": "50 L"}
    segments = message(values=bare, entries=[{"line_id": "1", "products": [product]}])
    tags = [s.tag for s in segments]
    assert "TDT" in tags and "EQD" not in tags and "LOC" not in tags and "SGP" not in tags
    assert [n.elements[0] for n in by_tag(segments, "NAD")] == ["CZ"]
    assert write_segment(by_tag(segments, "DGS")[0]) == "DGS+ADR+3+1203'"
    assert by_tag(segments, "MEA")[0].elements == ["AAE", ["AAF"], ["LTR", "50"]]
    # The technical name falls back to the UN number rather than to nothing:
    # the FTX in segment group 14 is mandatory.
    assert by_tag(segments, "FTX")[0].elements == ["AAD", "", "", ["UN 1203"]]
    assert validate(segments, iftdgn.config()["structure"]) == []


def test_a_leading_decimal_keeps_its_amount_and_ambiguous_quantities_block_export():
    """The shared reader used to find the 5 in '.5 L', multiplying the
    declared amount by ten; it also accepted the first number in formulas."""
    product = {"un_number": "1203", "class": "3", "adr_total_quantity": ".5 L"}
    segments = message(entries=[{"line_id": "1", "products": [product]}])
    assert by_tag(segments, "MEA")[0].elements == ["AAE", ["AAF"], ["LTR", "0.5"]]
    for invalid in ("10 x 20 L", "10-20 L", "999" * 150):
        problems = iftdgn.problems(VALUES, [{"line_id": "1", "products": [
            {**product, "adr_total_quantity": invalid}]}], "en")
        assert any("not a number greater than zero" in item for item in problems)


def test_the_regime_follows_the_modality_and_adn_says_so():
    sea = by_tag(message(profiles=("ADR", "IMDG"), modality="sea"), "DGS")[0]
    assert sea.elements[0] == "IMD"
    inland = message(profiles=("ADN",), modality="inland")
    assert by_tag(inland, "DGS")[0].elements[0] == "ZZZ"
    assert by_tag(inland, "FTX")[2].elements[3][0] == "ADN"


def test_the_additional_information_names_what_the_codes_cannot():
    product = {**PETROL, "marine_pollutant": "yes", "limited_quantity": "5 L", "empty_uncleaned": "ja"}
    segments = message(entries=[{"line_id": "1", "products": [product]}])
    aac = [f for f in by_tag(segments, "FTX") if f.elements[0] == "AAC"][0]
    # No LIMITED QUANTITY: the field holds column 7a of Table A, the limit
    # up to which 3.4 applies, not whether this consignment travels under it.
    assert aac.elements[3] == ["MARINE POLLUTANT", "EMPTY UNCLEANED"]


def test_the_quantities_are_read_with_their_thousands_separators():
    """"1.250,5 L" is 1250.5 litres, not 1.25 — which is what v1.189.0 wrote."""
    product = {**PETROL, "adr_total_quantity": "1.250,5 L",
               "gross_mass_per_package": "1,250.5", "quantity_packages": "2"}
    mea = by_tag(message(entries=[{"line_id": "1", "products": [product]}]), "MEA")
    assert [m.elements[2] for m in mea] == [["KGM", "2501"], ["LTR", "1250.5"]]


def test_a_net_per_package_is_multiplied_by_the_packages():
    product = {**PETROL, "adr_total_quantity": "", "net_mass_liters_per_package": "25 L",
               "quantity_packages": "4"}
    mea = by_tag(message(entries=[{"line_id": "1", "products": [product]}]), "MEA")
    assert [m.elements[2] for m in mea] == [["KGM", "880"], ["LTR", "100"]]
    # Without the number of packages a per-package figure is no total, and
    # the gross cannot be summed either: nothing is written, and the
    # validation says why.
    alone = {**product, "quantity_packages": ""}
    assert by_tag(message(entries=[{"line_id": "1", "products": [alone]}]), "MEA") == []
    assert any("has no mass or quantity" in p
               for p in iftdgn.problems(VALUES, [{"products": [alone]}], "en"))


def test_what_is_not_a_positive_number_is_named_not_guessed():
    product = {**PETROL, "adr_total_quantity": "-5 L", "gross_mass_per_package": "abc"}
    segments = message(entries=[{"line_id": "1", "products": [product]}])
    assert by_tag(segments, "MEA") == []
    found = iftdgn.problems(VALUES, [{"products": [product]}], "en")
    assert "IFTDGN: UN 1203 has a quantity that is not a number greater than zero (-5 L)." in found
    assert "IFTDGN: UN 1203 has a quantity that is not a number greater than zero (abc)." in found


def test_a_un_number_that_is_not_four_digits_is_not_padded_into_one():
    product = {**PETROL, "un_number": "abc"}
    dgs = by_tag(message(entries=[{"line_id": "1", "products": [product]}]), "DGS")[0]
    assert dgs.elements[2] == [""]
    found = iftdgn.problems(VALUES, [{"products": [product]}], "en")
    assert "IFTDGN: item #1 has a UN number that is not four digits (abc)." in found
    # A prefix is fine; a short number is not.
    assert iftdgn._un("UN 1203") == "1203" and iftdgn._un("un1203") == "1203"
    assert iftdgn._un("12") == "" and iftdgn._un("") == ""


def test_a_character_outside_the_character_set_is_replaced_before_it_is_released():
    """An emoji in a name became a bare "?" — the release character — in
    v1.189.0, because the replacement happened after the escaping."""
    from app.services.documents.iftdgn import render_iftdgn

    values = {**VALUES, "consignor_name": "Audit \U0001f69a BV", "carrier_name": "Zoë & Łukasz"}
    text = iftdgn.build_interchange(values, [], ENTRIES, profiles=["ADR"], modality="road", now=NOW)
    assert "UNB+UNOC:3+Audit ?? BV+Zoë & ??ukasz+" in text
    assert [s for s in parse(text) if s.tag == "UNB"][0].elements[1] == "Audit ? BV"
    text.encode("latin-1")  # strict: nothing outside the set is left
    path = render_iftdgn(values, [], ENTRIES, profiles=["ADR"], modality="road")
    try:
        assert "Audit ?? BV" in path.read_bytes().decode("latin-1")
    finally:
        path.unlink()


def test_several_products_are_several_goods_items():
    paint = {**PRODUCT, "un_number": "1263", "proper_shipping_name": "Verf", "labels": "3",
             "adr_total_quantity": "100 L", "quantity_packages": "2"}
    segments = message(entries=[{"line_id": "1", "products": [PETROL, paint]}])
    assert [g.elements[0] for g in by_tag(segments, "GID")] == ["1", "2"]
    assert [d.elements[2] for d in by_tag(segments, "DGS")] == [["1203"], ["1263"]]
    assert validate(segments, iftdgn.config()["structure"]) == []


def test_a_shipment_without_dangerous_goods_has_nothing_to_notify():
    with pytest.raises(iftdgn.NothingToNotify):
        message(entries=[])
    assert iftdgn.problems(VALUES, [], "nl")[0].startswith("De zending bevat geen gevaarlijke stoffen")
    missing = iftdgn.problems(VALUES, [{"products": [{"proper_shipping_name": "x"}]}], "en")
    assert any("no UN number" in m for m in missing)
    assert any("no class" in m for m in missing)
    assert any("no mass" in m for m in missing)
    assert iftdgn.problems(VALUES, ENTRIES, "de") == []


def test_the_interchange_wraps_the_message_and_names_sender_and_recipient():
    text = iftdgn.build_interchange(VALUES, [], ENTRIES, profiles=["ADR"], modality="road", now=NOW)
    segments = parse(text)
    assert segments[0].tag == "UNB"
    assert segments[0].elements[0] == ["UNOC", "3"]
    assert segments[0].elements[1] == "Afzender BV"
    assert segments[0].elements[2] == "Transport O'Neill & Sons"
    assert segments[0].elements[3] == ["260906", "0830"]
    assert segments[-1].tag == "UNZ" and segments[-1].elements == ["1", segments[0].elements[4]]
    assert segments[1].tag == "UNH" and segments[-2].tag == "UNT"
    # A shipment that names nobody gets marked placeholders, never invented names.
    bare = iftdgn.build_interchange({"reference": "X"}, [], ENTRIES, profiles=["ADR"], now=NOW)
    assert parse(bare)[0].elements[1:3] == [iftdgn.PLACEHOLDER_SENDER, iftdgn.PLACEHOLDER_RECIPIENT]


# --- 4. the export ------------------------------------------------------------------


def test_the_document_is_offered_beside_the_json_export_on_every_modality():
    document = get_document("iftdgn")
    assert document and document["exporter"] == "iftdgn" and document["category"] == "generated"
    for modality in get_registry()["modalities"]:
        docs = modality["documents"]
        assert "iftdgn" in docs, modality["key"]
        assert docs.index("iftdgn") == docs.index("shipment_export") + 1


def test_the_export_route_hands_out_an_edi_file():
    with client() as api:
        response = api.post("/api/documents/export", json={
            **doc("iftdgn"), "values": VALUES, "dangerous_goods": ENTRIES,
            "profiles": ["ADR"], "modality": "road"})
    release()
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/EDIFACT")
    assert "filename=\"DRAFT-iftdgn_" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith('.edi"')
    text = response.content.decode("latin-1")
    assert text.startswith("UNA:+.? '\nUNB+UNOC:3+Afzender BV+Transport O?'Neill & Sons+")
    assert "DGS+ADR+3+1203+-40:CEL+2++++33:1203+3++++D/E'" in text
    assert validate([s for s in parse(text) if s.tag not in ("UNB", "UNZ")],
                    iftdgn.config()["structure"]) == []


def test_the_export_route_refuses_a_shipment_without_dangerous_goods():
    with client() as api:
        response = api.post("/api/documents/export", json={
            **doc("iftdgn"), "values": VALUES, "dangerous_goods": [], "profiles": ["ADR"]})
    release()
    assert response.status_code == 422
    assert "niets te melden" in response.text


# --- 5. the directory --------------------------------------------------------------


def _directory() -> Path | None:
    for candidate in (os.environ.get("EMCARGO_EDIFACT_D16A"), "/tmp/claude-0"):
        if not candidate:
            continue
        for path in Path(candidate).rglob("IFTDGN_D.16A"):
            return path.parents[1]
    return None


@pytest.mark.skipif(_directory() is None, reason="the D.16A directory is not at hand")
def test_the_structure_is_the_directory_s_own_segment_table():
    root = _directory()
    text = (root / "edmd" / "IFTDGN_D.16A").read_text(encoding="latin-1").replace("\r", "")
    table = text[text.index("4.3.1  Segment table"):]
    rows = re.findall(r"^(\d{5})\s+(?:(?:----\s+Segment group\s+(\d+)\s+-+)|([A-Z]{3}) [^\n]*?)\s+([MC])\s+(\d+)", table, re.M)
    assert rows, "segment table not read"
    expected = [(pos, f"SG{group}" if group else tag, status, int(maximum))
                for pos, group, tag, status, maximum in rows]

    def flatten(nodes):
        for node in nodes:
            if "tag" in node:
                yield node["pos"], node["tag"], node["status"], node["max"]
            else:
                yield node["pos"], f"SG{node['group']}", node["status"], node["max"]
                yield from flatten(node["children"])

    assert list(flatten(iftdgn.config()["structure"])) == expected

    recorded = iftdgn.config()["source"]["verified_against"]
    for name, prefix in recorded.items():
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        assert digest.startswith(prefix), name


@pytest.mark.skipif(_directory() is None, reason="the D.16A directory is not at hand")
def test_the_code_values_are_in_the_directory_s_code_list():
    root = _directory()
    uncl = (root / "uncl" / "UNCL.16A").read_text(encoding="latin-1").replace("\r", "")
    for element, codes in iftdgn.config()["codes"].items():
        block = re.search(r"\n[\*+#|X ]    %s  .*?\n-{70}" % element, uncl, re.S)
        assert block, element
        for code, name in codes.items():
            m = re.search(r"\n[\*+#|X ]    %s\s{2,}(.+)" % re.escape(code), block.group(0))
            assert m, f"{element} {code}"
            assert m.group(1).strip().startswith(name[:20]), f"{element} {code}: {m.group(1)}"


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled")
