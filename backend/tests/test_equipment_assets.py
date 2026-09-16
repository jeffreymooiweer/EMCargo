"""An asset selection freezes transport facts; only a confirmed handover moves it.

These regressions cover stale edits, old imports, duplicate machine names and
container allocations. A believable but doubled container weight is a shipping
error, so assertions check mass and volume independently and recheck exports.
"""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.core.messages import ApiError
from app.core.migrations import _010_equipment_assets
from app.main import app
from app.models.equipment import EquipmentEvent
from app.models.user import User
from app.schemas.equipment import EquipmentMovement
from app.services import equipment as library
from app.services.container_loading import assess
from app.services.equipment_import import EQUIPMENT_HEADERS, equipment_to_rows, import_equipment_rows
from app.services.pipeline import match_equipment, parse_and_calculate


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{tmp_path / 'assets.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(id=1, username="manager", email="manager@example.local", role="admin", password_hash="x"))
        session.commit()
        yield session
    engine.dispose()
    get_settings.cache_clear()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, 1)
    client = TestClient(app)
    yield client
    client.close()
    app.dependency_overrides.clear()


def machine(db, **overrides):
    record = library.save(db, {"specifications": "DEMO telehandler", "kind": "machine", "asset_code": "DEMO-01",
                              "weight_kg": 7000, "length_cm": 500, "width_cm": 230, "height_cm": 250,
                              "current_location": "Depot A", **overrides}, db.get(User, 1))
    library.commit(db)
    return record


def loaded(db, cargo_weight=5000):
    record = machine(db, specifications="DEMO container", kind="container", asset_code="DEMO-C01", container_number="DEMO000001",
                     weight_kg=2200, length_cm=600, width_cm=240, height_cm=260, max_payload_kg=10000, max_gross_kg=12200)
    result = parse_and_calculate("DEMO container | 1 | pcs\nDEMO goods | 2 | pcs", db, line_overrides=[
        {"line_id": 1, "equipment": library.snapshot(record), "equipment_role": "container"},
        {"line_id": 2, "container_line_id": 1, "weight_total_kg": cargo_weight, "length_m": 1, "width_m": 1, "height_m": 1},
    ])
    return record, result


def test_upgrade_preserves_old_equipment_and_is_repeatable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE equipment_items (id INTEGER PRIMARY KEY, specifications TEXT, weight_kg FLOAT)"))
        conn.execute(text("INSERT INTO equipment_items VALUES (7, 'DEMO legacy', 1234)"))
        _010_equipment_assets(conn)
        _010_equipment_assets(conn)
        assert tuple(conn.execute(text("SELECT id, specifications, weight_kg, kind, version, details_json FROM equipment_items")).one()) == (7, "DEMO legacy", 1234, "other", 1, "{}")
    engine.dispose()


@pytest.mark.parametrize("legacy_dimension", [0, -1, float("inf")])
def test_legacy_unknown_dimensions_stay_readable_and_selectable(client, db, legacy_dimension):
    """The old API accepted unrestricted optional dimensions, and spreadsheets
    could use zero for unknown. Stricter input validation must not make a whole
    existing library fail to load or prevent selection of its known weight.
    Reading must also leave the stored legacy record unchanged.
    """
    record = machine(db)
    dimensions = ("length_cm", "width_cm", "height_cm", "wall_thickness_mm")
    for key in dimensions:
        setattr(record, key, legacy_dimension)
    db.commit()
    response = client.get("/api/equipment")
    assert response.status_code == 200
    assert all(response.json()[0][key] is None for key in dimensions)
    frozen = library.snapshot(record)
    assert frozen["weight_kg"] == 7000 and frozen["length_cm"] is None
    db.refresh(record)
    assert all(getattr(record, key) == legacy_dimension for key in dimensions)
    assert client.patch(f"/api/equipment/{record.id}", json={"length_cm": 0}).status_code == 422


def test_confirmed_transfer_cannot_be_undone_by_stale_edit_or_import(db):
    record = machine(db)
    before = library.to_dict(record)
    moved = library.move(db, record, EquipmentMovement(version=1, to_location="Site B", reference="JOB-42"), db.get(User, 1))
    library.commit(db)
    assert library.to_dict(moved)["current_location"] == "Site B"
    with pytest.raises(ApiError) as err:
        library.save(db, {**before, "notes": "Old screen"}, db.get(User, 1), existing=moved)
    assert err.value.code == "equipment.changed"
    with pytest.raises(ApiError) as err:
        library.save(db, {"current_location": "Depot A"}, db.get(User, 1), existing=moved)
    assert err.value.code == "equipment.move_required"
    assert [event.action for event in db.query(EquipmentEvent).order_by(EquipmentEvent.id)] == ["created", "moved"]


def test_frozen_selection_survives_rename_weight_change_archive_and_delete(db):
    record = machine(db)
    frozen = library.snapshot(record)
    args = [{"line_id": 1, "equipment": frozen, "length_m": 4.5}]
    for changes in ({"specifications": "Renamed", "weight_kg": 9000}, {"active": False}):
        library.save(db, changes, None, existing=record)
        library.commit(db)
        result = parse_and_calculate("DEMO telehandler | 1 | pcs", db, line_overrides=args)
        assert result["lines"][0]["weight_total_kg"] == 7000
        assert result["lines"][0]["length_cm"] == 450
        assert "DEMO-01" in result["lines"][0]["output_description"]
    db.delete(record)
    db.commit()
    result = parse_and_calculate("DEMO telehandler | 1 | pcs", db, line_overrides=args)
    assert result["lines"][0]["weight_total_kg"] == 7000


def test_same_names_are_selected_by_frozen_id_not_text(db):
    machine(db)
    other = machine(db, asset_code="DEMO-02", weight_kg=8000)
    assert match_equipment("DEMO telehandler", db) is None
    result = parse_and_calculate("DEMO telehandler | 1 | pcs", db, line_overrides=[{"line_id": 1, "equipment": library.snapshot(other)}])
    assert result["lines"][0]["weight_total_kg"] == 8000
    assert result["lines"][0]["equipment"]["equipment_id"] == other.id


def test_container_tare_and_outer_volume_count_once_without_recording_movement(db):
    record, result = loaded(db)
    assert result["totals"]["total_weight_kg"] == 7200
    assert result["totals"]["total_transport_volume_m3"] == 37.44
    parent, child = result["lines"]
    assert parent["container_load"] == {"tare_kg": 2200, "cargo_kg": 5000, "gross_kg": 7200, "complete": True, "line_ids": [2]}
    assert child["weight_total_kg"] == 5000 and child["transport_volume_m3"] == 0
    assert child["package_transport_volume_m3"] == 2
    assert "DEMO000001" in child["output_description"]
    again, errors = assess(result["lines"])
    assert not errors and again == result["lines"]
    assert library.to_dict(record)["current_location"] == "Depot A"
    assert db.query(EquipmentEvent).filter_by(equipment_id=record.id).count() == 1


@pytest.mark.parametrize("change,code", [
    (lambda lines: lines[0].update(include=False), "equipment.container_missing"),
    (lambda lines: lines[1].update(container_line_id=99), "equipment.container_missing"),
    (lambda lines: lines[0].update(container_line_id=1), "equipment.container_invalid"),
    (lambda lines: lines[0].update(quantity=2), "equipment.single_asset"),
    (lambda lines: lines[1].update(weight_total_kg=None), "equipment.container_weight_missing"),
    (lambda lines: lines[1].update(weight_total_kg=11000), "equipment.payload_exceeded"),
])
def test_allocations_are_rechecked_instead_of_trusting_stored_summary(db, change, code):
    _, result = loaded(db)
    change(result["lines"])
    _, errors = assess(result["lines"])
    assert code in errors


def test_capacity_recovery_and_unassignment_restore_original_volume(db):
    _, result = loaded(db, 11000)
    assert "equipment.payload_exceeded" in result["lines"][0]["messages"]
    result["lines"][1].update(weight_total_kg=5000, container_line_id=None)
    lines, errors = assess(result["lines"])
    assert errors == [] and lines[0]["status"] == "ok"
    assert lines[1]["transport_volume_m3"] == 2
    assert "DEMO000001" not in lines[1]["output_description"]


def test_export_import_preserves_fields_and_updates_only_own_identifier(db):
    first = machine(db, configurations=[{"name": "Lowered", "weight_kg": 6800, "height_cm": 210}], propulsion="diesel", planned_date="2026-10-01")
    second = machine(db, asset_code="DEMO-02", weight_kg=8000)
    response = import_equipment_rows(db, [EQUIPMENT_HEADERS, *equipment_to_rows([first])], user=db.get(User, 1))
    assert response.updated == 1 and not response.errors
    assert library.to_dict(first)["configurations"][0]["height_cm"] == 210
    assert library.to_dict(first)["planned_date"] == "2026-10-01" and second.weight_kg == 8000
    ambiguous = import_equipment_rows(db, [["specifications", "weight_kg"], [first.specifications, "1000"]])
    assert ambiguous.errors and ambiguous.updated == 0


def test_api_permissions_unique_ids_photos_and_history(client, db):
    payload = {"specifications": "DEMO loader", "kind": "machine", "weight_kg": 1500, "asset_code": " demo-20 "}
    response = client.post("/api/equipment", json=payload)
    assert response.status_code == 200
    record = response.json()
    assert record["asset_code"] == "DEMO-20"
    assert client.post("/api/equipment", json=payload).status_code == 409
    picture = io.BytesIO()
    Image.new("RGB", (60, 40), "blue").save(picture, format="PNG")
    upload = client.post(f"/api/equipment/{record['id']}/files", files={"file": ("../../photo.png", picture.getvalue(), "image/png")})
    assert upload.status_code == 200 and upload.json()["name"] == "photo.jpg"
    file_id = upload.json()["id"]
    download = client.get(f"/api/equipment/{record['id']}/files/{file_id}")
    assert download.headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/equipment/{record['id'] + 1}/files/{file_id}").status_code == 404
    assert len(client.get(f"/api/equipment/{record['id']}/events").json()["events"]) == 1
    user = db.get(User, 1); user.role = "user"; db.commit()
    assert client.get("/api/equipment").status_code == 200
    assert client.patch(f"/api/equipment/{record['id']}", json={"weight_kg": 1}).status_code == 403
    assert client.post(f"/api/equipment/{record['id']}/movements", json={"version": 1, "to_location": "Elsewhere"}).status_code == 403
    assert client.delete(f"/api/equipment/{record['id']}/files/{file_id}").status_code == 403


def test_document_validation_checks_capacity_and_single_container_scope(db):
    """The export API cannot trust a green status saved before a weight edit,
    nor apply one container number to goods in several carrying containers.
    Road goods lists can still carry multiple containers as separate rows.
    """
    from app.services.documents.exporter import validate_document
    _, result = loaded(db)
    road = {"key": "cmr", "sections": []}
    sea = {"key": "vgm", "sections": []}
    assert validate_document(road, {}, result["lines"], [], "en")[0] == []
    result["lines"][1]["weight_total_kg"] = 11000
    errors, _ = validate_document(road, {}, result["lines"], [], "en")
    assert "equipment.payload_exceeded" in [error["code"] for error in errors]
    result["lines"][1]["weight_total_kg"] = 5000
    errors, _ = validate_document(sea, {"container_number": "WRONG"}, result["lines"], [], "en")
    assert "equipment.document_container" in [error["code"] for error in errors]
    assert validate_document(sea, {"container_number": "DEMO000001"}, result["lines"], [], "en")[0] == []


def test_legacy_inspection_date_is_read_as_unknown_general_check_without_writing(db, client):
    """A single pre-upgrade date does not prove CSC or electrical approval.

    Reading an old asset must preserve the stored JSON and version while exposing
    one generic inspection, so rolling back does not lose the original date.
    """
    import json
    record = machine(db)
    record.details_json = json.dumps({"inspection_due": "2027-01-01"})
    db.commit()
    original = record.details_json
    data = client.get(f"/api/equipment/{record.id}").json()
    assert data["inspections"][0] == {
        "id": "legacy-inspection", "kind": "general", "name": "", "scope": "",
        "performed_on": None, "due_on": "2027-01-01", "result": "unknown",
        "inspector": "", "reference": "", "notes": "", "archived": False,
    }
    db.refresh(record)
    assert record.details_json == original and record.version == 1


@pytest.mark.parametrize("kind", ["vehicle", "machine", "container", "other"])
def test_independent_inspections_round_trip_and_legacy_patch_keeps_them(client, db, kind):
    """Electrical and vehicle checks may have different dates on the same asset.

    Old API clients are allowed to change the legacy date, but must not discard
    any separately maintained result. Export/import retains all typed records.
    """
    checks = [
        {"id": "electrical", "kind": "nen3140", "scope": "DEMO distribution board", "performed_on": "2026-01-01", "due_on": "2027-01-01", "result": "passed", "reference": "DEMO-NEN"},
        {"id": "cooling", "kind": "fgas", "scope": "DEMO air conditioner", "performed_on": "2026-06-01", "due_on": "2026-12-01", "result": "conditional", "notes": "DEMO action"},
    ]
    response = client.post("/api/equipment", json={"specifications": "DEMO inspected asset", "kind": kind, "weight_kg": 3000, "asset_code": "DEMO-CHECK", "facilities": ["electricity", "air_conditioning"], "inspections": checks})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["inspection_due"] == "2026-12-01"
    record = db.get(library.Equipment, data["id"])
    original = data["inspections"]
    result = client.patch(f"/api/equipment/{record.id}", json={"inspection_due": "2027-05-01"})
    assert result.status_code == 200
    assert result.json()["inspections"][:2] == original
    result = client.patch(f"/api/equipment/{record.id}", json={"inspection_due": None})
    assert result.json()["inspections"] == original
    rows = [EQUIPMENT_HEADERS] + equipment_to_rows([record])
    db.delete(record)
    db.commit()
    imported = import_equipment_rows(db, rows)
    assert not imported.errors and imported.created == 1
    restored = db.query(library.Equipment).one()
    assert library.to_dict(restored)["inspections"] == original
    assert library.to_dict(restored)["facilities"] == ["electricity", "air_conditioning"]


def test_renewal_keeps_previous_report_but_excludes_it_from_next_due_date(db, client):
    """Renewing one check must neither erase its report nor change another check.

    A cleared current check must stay cleared instead of being resurrected from
    the backwards-compatible scalar date during the next read.
    """
    record = machine(db, inspections=[{"id": "old", "kind": "apk", "due_on": "2026-01-01"}, {"id": "other", "kind": "lifting", "due_on": "2027-01-01"}])
    checks = library.to_dict(record)["inspections"]
    checks[0]["archived"] = True
    checks.append({"id": "new", "kind": "apk", "performed_on": "2026-09-01", "due_on": "2027-09-01", "result": "passed"})
    result = client.patch(f"/api/equipment/{record.id}", json={"inspections": checks}).json()
    assert len(result["inspections"]) == 3 and result["inspection_due"] == "2027-01-01"
    assert db.query(EquipmentEvent).filter_by(action="inspections").count() == 1
    result = client.patch(f"/api/equipment/{record.id}", json={"inspections": []}).json()
    assert result["inspections"] == [] and result["inspection_due"] is None
    assert client.get(f"/api/equipment/{record.id}").json()["inspections"] == []


@pytest.mark.parametrize("checks, code", [
    ([{"kind": "other"}], "equipment.inspection_name"),
    ([{"performed_on": "2026-09-01", "due_on": "2026-08-01"}], "equipment.inspection_dates"),
    ([{"result": "passed"}], "equipment.inspection_date_required"),
    ([{"id": "same"}, {"id": "same"}], "equipment.inspection_ids"),
])
def test_invalid_inspections_are_rejected_atomically_with_translatable_errors(client, db, checks, code):
    """Invalid records must not partially overwrite an asset or create events.

    PATCH uses merged validation, so it needs the same machine-readable errors
    as creation for all interface languages to explain the rejected input.
    """
    record = machine(db)
    response = client.patch(f"/api/equipment/{record.id}", json={"inspections": checks})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == code
    db.refresh(record)
    assert record.version == 1 and library.to_dict(record)["inspections"] == []


def test_container_catalog_has_sourced_templates_and_does_not_seed_owned_assets(client, db):
    """Catalog examples are not inventory, and conflicting weights stay unknown.

    Supplier-specific widths and high-cube heights must survive millimetre to
    centimetre conversion. Every known mass triple must remain self-consistent.
    """
    from app.services.container_templates import container_templates
    container_templates.cache_clear()
    result = client.get("/api/equipment/container-templates")
    assert result.status_code == 200
    models = result.json()
    assert len(models) >= 35 and db.query(library.Equipment).count() == 0
    assert len({row["id"] for row in models}) == len(models)
    assert {5, 10, 20, 40} <= {row["size_ft"] for row in models}
    assert {"side_door", "double_door", "double_side_door", "flatrack", "high_cube", "site"} <= {row["family"] for row in models}
    for row in models:
        assert row["source_url"].startswith("https://") and set(row["language_labels"]) == {"nl", "en", "de", "fr"}
        assert row["length_cm"] > 100 and row["height_cm"] > 200
        assert "inspections" not in row and "facilities" not in row
        if all(row[k] is not None for k in ("weight_kg", "max_payload_kg", "max_gross_kg")):
            assert row["weight_kg"] + row["max_payload_kg"] == row["max_gross_kg"]
        if row["basis"] == "mass_conflict":
            assert row["max_gross_kg"] is None and row["max_payload_kg"] is None
    rack = next(row for row in models if row["id"] == "trident-20ft-flatrack")
    assert (rack["length_cm"], rack["width_cm"], rack["height_cm"]) == (605.8, 243.8, 259.1)
    shell = next(row for row in models if row["basis"] == "base_shell")
    assert shell["weight_kg"] is None and shell["inner_length_cm"] is None
