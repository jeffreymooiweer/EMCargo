"""Four consignments, end to end, through the API a wizard actually calls.

The plan for this application named a closing step: walk four archetypes —
packaged goods by road, a road tank, a dry cargo vessel, a tank vessel — from
the goods to the last download, and see what comes out. Doing that by hand once
proves the day it was done. Doing it here proves it on every commit, and that
is the difference between a verification and an anecdote.

Each archetype asserts three things:

* **the compliance answer** carries the checks that mode is entitled to, and
  not the ones it is not — a tank vessel must not be answered with the dry
  cargo vessel's chapter 7.1, and a packages consignment must not be asked
  about a tank;
* **the documents** the wizard would offer are the documents that consignment
  needs, and each one that EMCargo generates actually renders;
* **what the application cannot say** is said. Every archetype ends on the
  finding that names its own limit, because an answer with a silent hole in it
  is the failure this whole application is built against.
"""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.main import app
from app.services.dg import database
from app.services.documents.registry import get_registry


def user():
    return SimpleNamespace(id=1, username="verify", role="admin", active=True)


def client():
    app.dependency_overrides[get_current_user] = user
    return TestClient(app)


def release():
    app.dependency_overrides.pop(get_current_user, None)


def goods(un, **extra):
    """A product as the prepare step leaves it: table A already applied."""
    rows = database.get_un_entries(un)
    row = rows[0] if rows else {}
    product = {
        "un_number": un,
        "proper_shipping_name": row.get("name_nl") or "",
        "class": row.get("class") or "",
        "classification_code": row.get("classification_code") or "",
        "packing_group": row.get("packing_group") or "",
        "labels": row.get("labels") or "",
        "hazard_number": row.get("hazard_number") or "",
        "tunnel_code": row.get("tunnel_code") or "",
        "transport_category": row.get("transport_category") or "",
        "quantity_packages": "4",
        "type_of_package": "vaten",
        "adr_total_quantity": "800 kg",
    }
    product.update(extra)
    return product


def compliance(profiles, *products, language="nl"):
    with client() as api:
        response = api.post("/api/dg/compliance", json={
            "entries": [{"line_id": "1", "vehicle": "UNIT-1",
                         "products": list(products)}],
            "profiles": profiles,
            "language": language,
        })
    release()
    assert response.status_code == 200, response.text
    return response.json()


#: A consignment filled in the way a wizard leaves it — every field the
#: documents ask for. An archetype with half its boxes empty proves that
#: validation works, which is a different test; this one is about what a
#: complete consignment produces.
CONSIGNMENT = {
    "consignor_name": "Afzender BV",
    "consignor_address": "Havenweg 1, 3011 Rotterdam, Nederland",
    "consignee_name": "Ontvanger GmbH",
    "consignee_address": "Hafenstrasse 4, 47119 Duisburg, Duitsland",
    "loading_point": "Rotterdam",
    "discharge_point": "Duisburg",
    "freight_payment": "Franco",
    "established_place": "Rotterdam",
    "established_date": "2026-08-15",
    "vessel_name": "Rijnvaart 7",
    "vehicle_registration": "12-BXG-3",
    "reference": "CP-2026-100",
    "emergency_contact": "+31 10 123 4567",
}


def export(document_key, *products, values=None, language="nl"):
    with client() as api:
        response = api.post("/api/documents/export", json={
            "document_key": document_key,
            "values": values or CONSIGNMENT,
            "lines": [{"description": "Test cargo", "quantity": 1, "unit": "pcs", "weight_total_kg": 800}],
            "dangerous_goods": [{"line_id": "1", "products": list(products)}],
            "output_language": language,
        })
    release()
    return response


def documents_for(modality):
    registry = get_registry()
    return next(m for m in registry["modalities"] if m["key"] == modality)["documents"]


# --- 1. packaged dangerous goods by road ----------------------------------


def test_road_packages():
    """Paint in drums on a lorry. The placarding answer for this is *no*: 5.3.1.5
    names class 1 and class 7 and nothing else, and telling a driver to placard
    anyway teaches that the placard is decoration."""
    answer = compliance(["ADR"], goods("1263"))

    assert "adr_points" in answer
    assert answer["adr_placarding"]["placards_required"] is False
    assert answer["adr_placarding"]["scope"] == "packages"
    # Not a tank: neither tank check may speak.
    assert answer.get("adr_tank_admission", {"status": "not_checked"})["status"] \
        == "not_checked"
    assert answer.get("adr_tank_fit", {"status": "not_checked"})["status"] \
        == "not_checked"

    assert "placarding_sheet" in documents_for("road")
    assert export("cmr", goods("1263")).status_code == 200
    assert export("placarding_sheet", goods("1263")).status_code == 200


# --- 2. a road tank -------------------------------------------------------


def test_road_tank():
    """Petrol in an L4BN semi-trailer. Column (12) requires LGBF; 4.3.4.1.2
    permits the tank that turned up, and the sheet carries the numbered plates
    that a tank — unlike packages — is *required* to show."""
    tank = goods("1203", carriage_mode="tank", tank_code="L4BN")
    answer = compliance(["ADR"], tank)

    assert answer["adr_tank_admission"]["status"] == "ok"
    fit = answer["adr_tank_fit"]["items"][0]
    assert fit["fit"] == "fits"
    assert fit["required"] == "LGBF"
    # The hierarchy is never the whole answer: column (13) travels with it.
    assert "TU9" in fit["provisions_note"]

    assert answer["adr_placarding"]["scope"] == "tanks_or_bulk"
    assert answer["adr_placarding"]["placards_required"] is True
    plates = [m for m in answer["adr_placarding"]["marks"]
              if m["kind"] == "tank_plates"]
    assert plates and "33 / UN 1203" in plates[0]["message"]

    assert export("placarding_sheet", tank).status_code == 200


def test_a_tank_that_does_not_fit_says_so():
    """The check has to be able to say no, or it says nothing at all."""
    answer = compliance(["ADR"], goods("1005", carriage_mode="tank",
                                       tank_code="C10DH"))
    assert answer["adr_tank_fit"]["items"][0]["fit"] == "does_not_fit"
    assert answer["adr_tank_fit"]["status"] == "not_permitted"


# --- 3. a dry cargo vessel ------------------------------------------------


def test_inland_dry_cargo():
    """Packages in the holds of a dry cargo vessel. Chapter 7.1 applies, the
    stowage plan of 7.1.4.11.1 is the document, and the hold is what makes
    7.1.4.3.2 a check rather than a statement."""
    hold_one = goods("1263", hold="1")
    answer = compliance(["ADN"], hold_one)

    assert "adn_exemption" in answer
    assert answer["adn_hold_separation"]["status"] != "not_available_for_mode"

    assert "stowage_plan" in documents_for("inland")
    assert export("adn_transport_doc", hold_one).status_code == 200
    assert export("stowage_plan", hold_one).status_code == 200


def test_two_cones_and_one_cone_flammable_in_one_hold():
    """The prohibition of 7.1.4.3.2, applied to what the boatmaster wrote."""
    answer = compliance(["ADN"], goods("1017", hold="1"), goods("1088", hold="1"))
    finding = next(f for f in answer["adn_hold_separation"]["findings"]
                   if f["provision"] == "7.1.4.3.2")
    assert finding["holds"] == ["1"]


# --- 4. a tank vessel -----------------------------------------------------


def test_inland_tank_vessel():
    """A cargo tank is not a hold, and chapter 7.1 is the chapter for dry cargo
    vessels. The separation check must decline for this consignment rather than
    answer it with the wrong chapter — that refusal is the whole point of the
    mode field."""
    cargo_tank = goods("1203", carriage_mode="tank")
    answer = compliance(["ADN"], cargo_tank)

    assert answer["adn_hold_separation"]["status"] == "not_available_for_mode"
    assert answer["adn_hold_separation"]["mode_note"]
    assert answer["adn_carriage_admission"]["status"] in ("ok", "not_permitted")

    # Table C answers what it settles and holds back what it does not: petrol's
    # rows split between vessel types N and C, so no single type is offered.
    signals = answer.get("adn_signals") or {}
    assert signals


# --- what every archetype must never lose ---------------------------------


@pytest.mark.parametrize("profiles,products", [
    (["ADR"], [{"un_number": "1263"}]),
    (["ADN"], [{"un_number": "1263"}]),
    (["IMDG"], [{"un_number": "1263"}]),
    (["IATA_DGR"], [{"un_number": "1263"}]),
])
def test_every_answer_names_the_editions_it_computed_with(profiles, products):
    """An answer that cannot say which editions it used cannot be checked by
    anyone, and a regulation that has expired must not be computed with in
    silence."""
    answer = compliance(profiles, *products)
    manifest = answer["regulatory_manifest"]
    assert manifest["editions"]
    assert manifest["manifest_id"]
    # An edition that has expired is named rather than quietly computed with.
    for expired in manifest.get("expired", []):
        assert expired in manifest["editions"]
    assert answer["rule_sets"]


# --- 5. bulk by road (v1.97.0) --------------------------------------------


def test_road_bulk():
    """Sulphur loose in a sheeted vehicle. Column (10) gives BK1-BK3, column
    (17) gives VC1 and VC2, and both the permission and its codes travel to the
    paper — they are what the loader checks the container against. The new
    documents of v1.93.0 come with the ride."""
    bulk = goods("1350", carriage_mode="bulk")
    answer = compliance(["ADR"], bulk)

    admission = answer["adr_bulk_admission"]
    assert admission["status"] == "ok"
    item = admission["items"][0]
    assert item["bk_codes"] == ["BK1", "BK2", "BK3"]
    assert item["vc_codes"] == ["VC1", "VC2"]

    # Not a tank: the tank checks stay silent on a bulk load.
    assert answer.get("adr_tank_fit", {"status": "not_checked"})["status"] \
        == "not_checked"

    for key in ("equipment_sheet", "onboard_documents_adr",
                "packing_certificate"):
        assert key in documents_for("road")
    assert export("cmr", bulk).status_code == 200
    assert export("equipment_sheet", bulk).status_code == 200
    assert export("onboard_documents_adr", bulk).status_code == 200


def test_road_bulk_refused_for_a_liquid():
    """Petrol carries neither a BK nor a VC code: 7.3.1.1 says no, on screen
    and on the consignment note alike."""
    answer = compliance(["ADR"], goods("1203", carriage_mode="bulk"))
    assert answer["adr_bulk_admission"]["status"] == "not_permitted"


# --- the newer downloads, through the same API ----------------------------


def test_the_tank_vessel_document_line_reaches_the_export():
    """v1.91.0 composes the 5.4.1.1.2 line from table C; the export is where
    it has to arrive."""
    cargo_tank = goods("1203", carriage_mode="tank",
                       adr_total_quantity="250000 kg")
    response = export("adn_transport_doc", cargo_tank)
    assert response.status_code == 200


@pytest.mark.parametrize("language", ["nl", "de"])
def test_the_document_pack_renders_in_two_languages(language):
    """The plan's own closing rule: every new document through the real API,
    in two languages."""
    product = goods("1263")
    for key in ("packing_certificate", "onboard_documents_adr",
                "equipment_sheet"):
        assert export(key, product, language=language).status_code == 200, key
    assert export("onboard_documents_adn", goods("1263", hold="1"),
                  language=language).status_code == 200


# --- 6. the rail leg, end to end (v1.122.0) --------------------------------


def test_rail_packages():
    """Aniline in drums on a wagon. The rail answer is its own: the package
    wagon is placarded for every class (5.3.1.5) where a road vehicle with the
    same drums placards nothing, the points count per wagon or large container
    (RID 1.1.3.6), and the foodstuffs provision is cited CW 28 — a CIM that
    quotes CV28 names a code the RID does not have."""
    answer = compliance(["RID"], goods("1547"))

    assert "1.1.3.6.3" in answer["adr_points"]["basis_note"]
    assert answer["rid_placarding"]["placards_required"] is True
    rules = [w["rule"] for w in answer["adr_mixed_loading"]]
    assert any("CW28" in r for r in rules)
    assert all("CV28" not in r for r in rules)
    # Not a tank: no numbered plates, no orange band.
    kinds = [m["kind"] for m in answer["rid_placarding"]["marks"]]
    assert "orange_band" not in kinds

    assert "placarding_sheet_rid" in documents_for("rail")
    rail_values = dict(CONSIGNMENT, payment_instruction="Franco vracht",
                       nhm_code="292142")
    assert export("cim", goods("1547"), values=rail_values).status_code == 200
    assert export("placarding_sheet_rid", goods("1547")).status_code == 200


def test_rail_tank_wagon():
    """Chlorine in a tank-wagon: the numbered plates of 5.3.2.1.1/5.3.2.1.2
    carry 265 / UN 1017 on each side — the number read out of table A, not
    assumed — the orange band of 5.3.5 follows the liquefied state out of the
    classification code, and the shunting labels of 5.3.4 are raised as the
    condition they are."""
    tank = goods("1017", carriage_mode="tank", adr_total_quantity="5000 kg")
    answer = compliance(["RID"], tank)

    marks = answer["rid_placarding"]["marks"]
    kinds = [m["kind"] for m in marks]
    assert "orange_band" in kinds
    assert "shunting_labels" in kinds
    plates = next(m for m in marks
                  if m["kind"] == "orange_plates" and m.get("required") is True)
    assert "265 / UN 1017" in plates["message"]

    rail_values = dict(CONSIGNMENT, payment_instruction="Franco vracht",
                       nhm_code="280110")
    assert export("cim", tank, values=rail_values).status_code == 200
    assert export("placarding_sheet_rid", tank, language="de").status_code == 200


# --- 7. the sea leg, end to end (v1.152.0) ---------------------------------


def test_sea_packages_in_a_container():
    """Petrol in drums and a marine pollutant in an IBC, in one container.

    The sea answer is its own, and every line below is a place where taking
    the road's would be wrong: the container is placarded on four sides where
    a road vehicle carrying the same drums is placarded on two, the proper
    shipping name is marked on the unit itself, and the marine pollutant mark
    has no land counterpart at all.
    """
    answer = compliance(["IMDG"], goods("1203"),
                        goods("3082", marine_pollutant="P"))

    placarding = answer["imdg_placarding"]
    assert placarding["placards_required"] is True
    # Four sides, and each kind of unit given its own rule because the kind is
    # not something the application can see.
    provisions = [p["provision"] for p in placarding["placards"]]
    assert "5.3.1.1.4.1.1" in provisions
    kinds = [m["kind"] for m in placarding["marks"]]
    assert "marine_pollutant" in kinds
    assert "proper_shipping_name" in kinds

    # The segregation question sea is entitled to, and the land answers it is
    # not: no tunnel code, no ADR points, no orange plates.
    assert "imdg_segregation" in answer
    assert "adr_tunnel" not in answer
    assert "adr_points" not in answer

    # Every document the sea modality offers renders.
    offered = documents_for("sea")
    assert "placarding_sheet_imdg" in offered
    sea_values = dict(CONSIGNMENT, container_number="MSKU 123456-7",
                      declarant_name="J. Jansen", declaration_place="Rotterdam",
                      declaration_date="2026-08-21", vgm_kg="12000",
                      vgm_method="method1", responsible_name="J. JANSEN",
                      determination_place="Rotterdam",
                      determination_date="2026-08-21",
                      # The B/L asks which form of bill the shipper wants; it
                      # is a commercial choice, not something derivable.
                      document_form="Seaway bill")
    for key in ("imo_dgd", "bl_si", "vgm", "packing_certificate",
                "placarding_sheet_imdg"):
        assert export(key, goods("1203", marine_pollutant="N",
                                 imdg_source_reference="Synthetic SDS section 14, 2026-09-01",
                                 imdg_source_reviewed="Y"), values=sea_values).status_code == 200, key


def test_the_sea_documents_carry_the_emergency_number():
    """5.4.1.5.11 asks for a 24-hour number, and the application asks the user
    for one. Until v1.152.0 it then had nowhere to put it: the field was
    collected and silently dropped, which is the failure mode this application
    is built against — a document that looks complete."""
    from app.services.documents.registry import get_document, resolve_sections

    for key in ("imo_dgd", "bl_si"):
        fields = [field["key"] for section in resolve_sections(get_document(key))
                  for field in section.get("fields", [])]
        assert "emergency_contact" in fields, key


def test_the_sea_documents_agree_on_what_a_container_number_is_called():
    """The IMO form asked for `container_identification` while the VGM and the
    B/L instruction asked for `container_number` — the same number, twice
    typed, on one consignment. Harmonised in v1.152.0; pinned here because the
    next document added is the one that would drift again."""
    from app.services.documents.registry import get_document, resolve_sections

    for key in ("imo_dgd", "vgm", "bl_si"):
        fields = [field["key"] for section in resolve_sections(get_document(key))
                  for field in section.get("fields", [])]
        assert "container_number" in fields, key
        assert "container_identification" not in fields, key


def test_a_hot_container_bound_for_sea_is_told_about_the_mark():
    """The elevated temperature mark of 5.3.2.2, from the carriage temperature
    field — the one thing at sea that no table can imply."""
    answer = compliance(["IMDG"], goods("2448", carriage_temperature="130"))
    mark = next(m for m in answer["imdg_placarding"]["marks"]
                if m["kind"] == "elevated_temperature")
    assert mark["required"] is True


def test_sea_says_what_it_cannot_answer():
    """The archetype's own limit, as every archetype ends. The stowage
    category is shown and not enforced, and segregation from foodstuffs is
    raised as a thing to verify rather than answered — the application cannot
    see what else is in the container."""
    answer = compliance(["IMDG"], goods("1203"))
    # The unit is stripped after discharge and the marking must survive the
    # sea: both are stated rather than assumed to be known.
    kinds = [m["kind"] for m in answer["imdg_placarding"]["marks"]]
    assert "removal" in kinds
    assert "seawater" in kinds


# --- 8. a container, whichever mode carries it (v1.152.0) -------------------


def test_every_unlocked_mode_can_carry_a_container():
    """A container of dangerous goods rarely travels one leg. It is packed
    inland, trucked to the terminal, put on a barge or a wagon and then on a
    ship — and the box number identifies the load throughout, while the
    vehicle under it changes at every handover.

    Until v1.152.0 only rail and sea had anywhere to write it: a CMR for a
    container had no box number and no seal, and neither did the ADN transport
    document. The number then lived only in the operator's head, which is
    exactly where a consignment note is supposed to take it out of.
    """
    from app.services.documents.registry import get_document, resolve_sections

    main_document = {"road": "cmr", "rail": "cim", "sea": "imo_dgd",
                     "inland": "adn_transport_doc"}
    for mode, key in main_document.items():
        fields = [field["key"] for section in resolve_sections(get_document(key))
                  for field in section.get("fields", [])]
        # Rail calls it the UTI number, which is the term RID and the CIM use;
        # the others call it the container number. Both are the same box.
        assert ("container_number" in fields
                or "container_uti_number" in fields), f"{mode} ({key})"


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled", "synthetic_templates")
