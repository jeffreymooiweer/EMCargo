"""Cargo conservation, unknown measurements, scope and transactional retention.

The regression scenarios cover silent loss of directly loaded goods, double
counting nested tare, stale plugin inputs, physical identity reuse and DG
approval bound to opaque editor state instead of actual cargo data.
"""
from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.schemas.cargo import CargoManifest
from app.schemas.history import ShipmentIn
from app.services.cargo import assess
from app.services import history, dg_review
from app.models.cargo import CargoIdentity, CargoUse
from app.models.user import User
from tests.test_history import db, application


def unit(name="Box", category="box", tare=1, **kwargs):
    identity = str(uuid4())
    return {"id": identity, "code": "BOX-" + identity[:12], "name": name, "category": category, "tare_kg": tare, **kwargs}


def allocation(identity, target, quantity):
    return {"id": str(uuid4()), "goods_id": identity, "unit_id": target["id"], "quantity": quantity}


def manifest(units=(), allocations=()):
    return {"schema_version": 1, "shipment_id": str(uuid4()), "revision": 0, "units": list(units), "allocations": list(allocations)}


def goods(identity=1, quantity=100, weight=10, **kwargs):
    return {"line_id": identity, "cargo_goods_id": identity, "description": "Bolts", "include": True, "unit": "pcs", "quantity": quantity, "weight_total_kg": weight, **kwargs}


def payload(cargo, **kwargs):
    return ShipmentIn(lines=[goods()], cargo=cargo, snapshot={"version": 1, "cargo": cargo}, **kwargs)


def test_mixed_nested_packages_count_each_mass_once_and_leave_remainder():
    pallet = unit("Pallet", "pallet", 20, loaded_dimensions_mm={"length": 1200, "width": 800, "height": 1000})
    large = unit("Large box", tare=3, parent_id=pallet["id"])
    small = unit(parent_id=large["id"])
    result = assess(manifest([pallet, large, small], [allocation(1, small, 50), allocation(2, small, 20), allocation(2, large, 30)]), [goods(), goods(2, weight=20, transport_volume_m3=1)])
    assert result["totals"]["cargo_gross_kg"] == 54
    assert result["units"][0]["calculated_gross_kg"] == 39
    assert [(item["goods_id"], item["quantity"]) for item in result["loose"]] == [(1, 50), (2, 50)]


def test_direct_bulk_and_long_goods_need_no_package_or_carrier_tare():
    trailer = unit("Trailer", "vehicle", None, kind="ctu")
    result = assess(manifest([trailer], [allocation(1, trailer, 10)]), [goods(quantity=10, weight=100, transport_volume_m3=2)])
    assert result["totals"]["cargo_gross_kg"] == 100
    assert result["totals"]["transport_gross_kg"] is None
    assert result["totals"]["occupied_volume_m3"] == 2
    bulk = assess(manifest(), [goods(quantity=2.5, unit="t", weight=2500, transport_volume_m3=1.6)])
    assert bulk["totals"]["goods_kg"] == 2500


def test_null_stable_id_falls_back_for_legacy_pipeline_lines():
    box = unit()
    assert assess(manifest([box], [allocation(1, box, 100)]), [goods(cargo_goods_id=None)])["totals"]["cargo_gross_kg"] == 11


def test_pallet_empty_height_and_measured_weight_do_not_invent_missing_facts():
    pallet = unit("Pallet", "pallet", None, dimensions_mm={"length": 1200, "width": 800, "height": 144}, measured_gross_kg=20)
    result = assess(manifest([pallet], [allocation(1, pallet, 100)]), [goods(weight=None)])
    assert result["totals"]["cargo_gross_kg"] is None
    assert result["totals"]["occupied_volume_m3"] is None
    assert result["units"][0]["measured_gross_kg"] == 20
    assert not result["units"][0]["complete"]


@pytest.mark.parametrize("quantity,code", [(101, "cargo.overallocated"), (0.5, "cargo.whole_items")])
def test_no_overallocation_or_fractional_pieces(quantity, code):
    box = unit()
    with pytest.raises(HTTPException) as raised:
        assess(manifest([box], [allocation(1, box, quantity)]), [goods()])
    assert raised.value.detail["code"] == code


def test_decimal_allocations_do_not_drift():
    boxes = [unit() for _ in range(10)]
    result = assess(manifest(boxes, [allocation(1, box, 0.1) for box in boxes]), [goods(quantity=1, unit="kg", weight=1)])
    assert result["loose"] == []
    assert result["totals"]["cargo_gross_kg"] == 11


def test_cycle_duplicate_equipment_and_depth_are_rejected(monkeypatch):
    from app.core.config import get_settings
    box = unit(); box["parent_id"] = box["id"]
    with pytest.raises(HTTPException) as raised:
        assess(manifest([box]), [])
    assert raised.value.detail["code"] == "cargo.cycle"
    with pytest.raises(HTTPException):
        assess(manifest([unit(equipment_id=3), unit(equipment_id=3)]), [])
    monkeypatch.setattr(get_settings(), "cargo_max_depth", 2)
    a, b, c = unit(), unit(), unit()
    b["parent_id"] = a["id"]; c["parent_id"] = b["id"]
    with pytest.raises(HTTPException):
        assess(manifest([a, b, c]), [])


def test_measurements_reject_nonfinite_and_abusively_large_numbers():
    for value in (float("nan"), float("inf"), -1, 1e300):
        with pytest.raises(ValidationError):
            CargoManifest.model_validate(manifest([unit(tare=value)]))


def test_retained_cargo_roundtrip_revision_and_removal(db):
    box = unit(); cargo = manifest([box], [allocation(1, box, 100)])
    saved = history.keep(db, db.get(User, 1), payload(cargo))
    assert saved.cargo_revision == 1
    assert history.detail(saved).export["cargo"]["units"][0]["id"] == box["id"]
    cargo["units"][0]["name"] = "Changed"
    with pytest.raises(HTTPException) as raised:
        history.keep(db, db.get(User, 1), payload(cargo, expected_cargo_revision=0), saved)
    assert raised.value.status_code == 409
    saved = history.keep(db, db.get(User, 1), payload(cargo, expected_cargo_revision=1), saved)
    assert saved.cargo_revision == 2
    history.keep(db, db.get(User, 1), payload(cargo, expected_cargo_revision=1), saved)
    assert saved.cargo_revision == 2
    history.forget(db, saved)
    assert db.query(CargoUse).count() == db.query(CargoIdentity).count() == 0


def test_reusable_identity_preserves_history_and_blocks_overlapping_use(db):
    from datetime import datetime, timezone
    box = unit(reusable=True); cargo = manifest([box], [allocation(1, box, 100)])
    first = history.keep(db, db.get(User, 1), payload(cargo)); before = history.detail(first).export
    second = deepcopy(cargo); second["shipment_id"] = str(uuid4()); second["units"][0]["name"] = "Later name"
    with pytest.raises(HTTPException) as raised:
        history.keep(db, db.get(User, 1), payload(second))
    assert raised.value.detail["code"] == "cargo.unit_in_use"
    db.rollback(); first.work_completed_at = datetime.now(timezone.utc); db.commit()
    history.keep(db, db.get(User, 1), payload(second))
    assert history.detail(first).export == before
    assert db.query(CargoIdentity).count() == 1
    import json
    assert json.loads(db.query(CargoIdentity).one().unit_json)["name"] == box["name"]


def test_assessment_is_stateless_and_history_contract_retention_gated(db, monkeypatch):
    cargo = manifest([unit()]); client = application(db, monkeypatch)
    response = client.post("/api/cargo/v1/assess", json={"cargo": cargo, "lines": [goods()]})
    assert response.status_code == 200, response.text
    assert db.query(CargoIdentity).count() == 0
    assert client.get("/api/shipments/1/cargo/v1").status_code == 404
    assert len(client.get("/api/cargo/templates").json()) >= 15


def test_dg_fingerprint_tracks_contents_not_revision_bookkeeping():
    cargo = manifest([unit()]); original = payload(cargo)
    changed = original.model_copy(update={"expected_cargo_revision": 3})
    assert dg_review.fingerprint(original) == dg_review.fingerprint(changed)
    cargo["revision"] = 5
    assert dg_review.fingerprint(original) == dg_review.fingerprint(payload(cargo))
    cargo["units"][0]["name"] = "Different packaging"
    assert dg_review.fingerprint(original) != dg_review.fingerprint(payload(cargo))


def test_cmr_projection_preserves_nested_mass_and_original_dg_declarations():
    from app.services.cargo_documents import project_lines
    pallet = unit("Pallet", "pallet", 20); box = unit(parent_id=pallet["id"])
    cargo = manifest([pallet, box], [allocation(1, box, 100)])
    rows = project_lines(cargo, [goods()])
    assert len(rows) == 1
    assert rows[0]["weight_total_kg"] == 31
    assert "100 pcs Bolts" in rows[0]["description"]
    assert box["code"] in rows[0]["description"]


def test_changed_goods_invalidate_plugin_revision_even_with_same_hierarchy(db):
    cargo = manifest([unit()]); original = payload(cargo)
    saved = history.keep(db, db.get(User, 1), original)
    modified = original.model_copy(update={"lines": [goods(weight=15)], "expected_cargo_revision": 1})
    history.keep(db, db.get(User, 1), modified, saved)
    assert saved.cargo_revision == 2
    with pytest.raises(HTTPException) as raised:
        history.keep(db, db.get(User, 1), original.model_copy(update={"expected_cargo_revision": 1}), saved)
    assert raised.value.status_code == 409


def test_retried_creation_reuses_shipment_and_late_autosave_cannot_unpublish(db):
    from app.models.shipment import Shipment
    original = payload(manifest([unit()]))
    first = history.keep(db, db.get(User, 1), original)
    again = history.keep(db, db.get(User, 1), original)
    assert again.id == first.id
    assert db.query(Shipment).count() == 1
    with pytest.raises(HTTPException):
        history.keep(db, db.get(User, 1), original.model_copy(update={"draft": True}))
    assert first.is_draft is False
    assert history.count(db) == 1


def test_two_sessions_cannot_overwrite_each_others_cargo(db):
    from sqlalchemy.orm import Session
    from app.models.shipment import Shipment
    cargo = manifest([unit()]); saved = history.keep(db, db.get(User, 1), payload(cargo))
    second = Session(db.get_bind())
    stale = second.get(Shipment, saved.id)
    updated = deepcopy(cargo); updated["units"][0]["name"] = "First editor"
    history.keep(db, db.get(User, 1), payload(updated, expected_cargo_revision=1), saved)
    updated["units"][0]["name"] = "Second editor"
    with pytest.raises(HTTPException) as raised:
        history.keep(second, second.get(User, 1), payload(updated, expected_cargo_revision=1), stale)
    assert raised.value.status_code == 409
    second.rollback(); second.close()
    assert history.detail(saved).export["cargo"]["units"][0]["name"] == "First editor"


def test_legacy_container_snapshot_preserves_tare_but_excludes_it_from_cargo_mass():
    box = unit("Container", "container", 2000, kind="ctu", legacy_goods_id=1)
    cargo = manifest([box], [allocation(2, box, 10)])
    original = [goods(1, quantity=1, weight=2000, equipment_role="container"), goods(2, quantity=10, weight=1000, transport_volume_m3=2)]
    before = deepcopy(original)
    result = assess(cargo, original)
    assert original == before
    assert result["totals"]["goods_kg"] == 1000
    assert result["totals"]["transport_gross_kg"] == 3000
    assert result["totals"]["occupied_volume_m3"] == 2


def test_format_limit_is_specific_and_does_not_block_unrelated_documents():
    from app.services.cargo_documents import validate_for_document
    box = unit(); cargo = manifest([box], [allocation(1, box, 100)])
    with pytest.raises(HTTPException) as raised:
        validate_for_document(cargo, [goods()], "iata_dgd", {})
    assert raised.value.detail["params"]["document"] == "iata_dgd"
    validate_for_document(cargo, [goods()], "cmr", {})
    validate_for_document(cargo, [goods()], "equipment_sheet", {})
    validate_for_document(cargo, [goods()], "shipment_export", {})


def test_dg_descriptions_are_not_split_or_changed_when_goods_span_boxes():
    from app.services.cargo_documents import project_lines
    from app.services.dg.autofill import description_line
    boxes = [unit(), unit()]
    cargo = manifest(boxes, [allocation(1, box, 50) for box in boxes])
    product = {"un_number": "1203", "proper_shipping_name": "PETROL", "class": "3", "packing_group": "II", "quantity_packages": "2", "adr_total_quantity": "10", "adr_quantity_unit": "L"}
    rows = project_lines(cargo, [goods()], [{"line_id": 1, "products": [product]}])
    assert sum(row["weight_total_kg"] or 0 for row in rows) == 12
    assert sum(row["quantity"] or 0 for row in rows) == 2
    assert rows[-1]["description"] == description_line(product, "ADR")
    assert rows[-1]["quantity"] is None
    assert rows[-1]["weight_total_kg"] is None


def test_template_edit_permissions_and_optimistic_versions(db, monkeypatch):
    client = application(db, monkeypatch)
    assert client.post("/api/cargo/templates", json={"name": "Own box"}).status_code == 403
    db.get(User, 1).role = "admin"; db.commit()
    created = client.post("/api/cargo/templates", json={"name": "Own box", "tare_kg": 1}).json()
    assert created["version"] == 1
    updated = client.put("/api/cargo/templates/" + created["id"], json={"name": "Bigger box", "version": 1})
    assert updated.status_code == 200, updated.text
    assert client.put("/api/cargo/templates/" + created["id"], json={"name": "Old edit", "version": 1}).status_code == 409
    assert client.delete("/api/cargo/templates/" + created["id"] + "?version=2").status_code == 200
    assert not any(item["id"] == created["id"] for item in client.get("/api/cargo/templates").json())


def test_reusable_master_remains_selectable_when_history_is_disabled(db, monkeypatch):
    import json
    physical = unit(reusable=True)
    db.add(CargoIdentity(id=physical["id"], code=physical["code"], reusable=True, unit_json=json.dumps(physical)))
    db.commit()
    client = application(db, monkeypatch)
    response = client.get("/api/cargo/units")
    assert response.status_code == 200
    assert response.json()[0]["id"] == physical["id"]
    assert client.get("/api/shipments/1/cargo/v1").status_code == 404


def test_equipment_identity_can_be_resolved_beyond_first_reusable_page(db, monkeypatch):
    import json
    from app.models.user import Equipment
    db.add(Equipment(id=99, specifications="Trailer", weight_kg=3000))
    for index in range(201):
        physical = unit(reusable=True)
        physical["code"] = f"LU-{index:04d}"
        if index == 200:
            physical["equipment_id"] = 99
            expected_id = physical["id"]
        db.add(CargoIdentity(id=physical["id"], code=physical["code"], reusable=True,
                             equipment_id=physical.get("equipment_id"), unit_json=json.dumps(physical)))
    db.commit()
    client = application(db, monkeypatch)
    assert len(client.get("/api/cargo/units").json()) == 200
    response = client.get("/api/cargo/units?equipment_id=99")
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [expected_id]
