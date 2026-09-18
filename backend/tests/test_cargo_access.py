"""The plugin-facing cargo view inherits shipment privacy and retention.

A separate read endpoint must not become a shortcut around department or
private-draft guards. Template selection remains available to operational
users, while changing organisation master data requires a manager.
"""
from copy import deepcopy

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import create_app
from app.models.cargo import CargoIdentity, CargoUse
from app.models.shipment import Shipment
from app.models.user import User
from app.services import history
from tests.test_cargo import allocation, goods, manifest, payload, unit
from tests.test_departments import client_as, db
from tests.test_history import switch_history


def keep_cargo(db, *, draft=False):
    box = unit()
    cargo = manifest([box], [allocation(1, box, 100)])
    request = payload(cargo, draft=draft)
    return history.keep(db, db.get(User, 2), request), request


def test_cargo_routes_require_an_authenticated_account(db):
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    client = TestClient(app)
    for path in ("/api/cargo/templates", "/api/cargo/units", "/api/cargo/v1/contract",
                 "/api/shipments/1/cargo/v1"):
        assert client.get(path).status_code == 401, path
    assert client.post("/api/cargo/v1/assess", json={
        "cargo": manifest(), "lines": [goods()],
    }).status_code == 401


@pytest.mark.parametrize("viewer_id,expected", [(2, 200), (1, 200), (3, 404), (4, 404)])
def test_retained_cargo_view_enforces_department_visibility(db, viewer_id, expected):
    record, request = keep_cargo(db)
    client = client_as(db, viewer_id)
    response = client.get(f"/api/shipments/{record.id}/cargo/v1")
    assert response.status_code == expected
    if expected == 200:
        assert response.json()["cargo"]["shipment_id"] == request.cargo.shipment_id
        assert response.json()["cargo"]["revision"] == record.cargo_revision == 1
        assert response.json()["shipment_id"] == record.id
        return
    # The same guessed identifier cannot be used to write a different graph.
    before = record.export_json
    changed = request.model_dump(mode="json")
    changed["cargo"]["units"][0]["name"] = "Unauthorised change"
    changed["snapshot"]["cargo"] = deepcopy(changed["cargo"])
    changed["expected_cargo_revision"] = record.cargo_revision
    assert client.put(f"/api/shipments/{record.id}", json=changed).status_code == 404
    db.expire_all()
    assert db.get(Shipment, record.id).export_json == before


@pytest.mark.parametrize("viewer_id", [1, 3, 5])
def test_cargo_view_keeps_drafts_private_even_from_admin_and_same_department(db, viewer_id):
    db.add(User(id=5, username="eve", email="eve@example.com", password_hash="x",
                role="user", department_id=1))
    db.commit()
    record, _ = keep_cargo(db, draft=True)
    path = f"/api/shipments/{record.id}/cargo/v1"
    assert client_as(db, 2).get(path).status_code == 200
    assert client_as(db, viewer_id).get(path).status_code == 404


def test_legacy_opt_out_keeps_cargo_visible_and_assessment_stateless(db):
    record, request = keep_cargo(db)
    # Settings/purge behaviour has its own coverage; force the resulting gate
    # here to prove this new endpoint observes it on every request.
    switch_history(db, False)
    before = (db.query(CargoIdentity).count(), db.query(CargoUse).count())
    client = client_as(db, 2)
    assert client.get(f"/api/shipments/{record.id}/cargo/v1").status_code == 200
    assert client.get("/api/cargo/units").json() == []
    response = client.post("/api/cargo/v1/assess", json={
        "cargo": request.cargo.model_dump(mode="json"), "lines": [goods()],
    })
    assert response.status_code == 200
    assert (db.query(CargoIdentity).count(), db.query(CargoUse).count()) == before


def test_ordinary_user_can_choose_templates_but_only_manager_can_change_them(db):
    user = client_as(db, 2)
    assert user.get("/api/cargo/templates").status_code == 200
    template = {"name": "Parts box", "category": "box", "tare_kg": 0.2}
    assert user.post("/api/cargo/templates", json=template).status_code == 403
    db.add(User(id=5, username="manager", email="manager@example.com",
                password_hash="x", role="super_user", department_id=1))
    db.commit()
    manager = client_as(db, 5)
    created = manager.post("/api/cargo/templates", json=template)
    assert created.status_code == 200, created.text
    identity = created.json()["id"]
    updated = {**template, "name": "Changed parts box", "version": 1}
    assert user.put(f"/api/cargo/templates/{identity}", json=updated).status_code == 403
    assert user.delete(f"/api/cargo/templates/{identity}?version=1").status_code == 403
    assert manager.put(f"/api/cargo/templates/{identity}", json=updated).status_code == 200


def test_effective_goods_volume_invalidates_the_retained_plugin_revision(db):
    """Legacy container calculations zero the public line volume and preserve
    the real volume separately. Changing that retained value changes the cargo
    assessment even when neither the graph nor the zeroed field changes; it
    must therefore reject stale saves and advance the plugin revision.
    """
    request = payload(manifest()).model_copy(update={"lines": [
        goods(transport_volume_m3=0, package_transport_volume_m3=2),
    ]})
    record = history.keep(db, db.get(User, 2), request)
    changed = request.model_copy(update={"lines": [
        goods(transport_volume_m3=0, package_transport_volume_m3=3),
    ], "expected_cargo_revision": 0})
    with pytest.raises(HTTPException) as rejected:
        history.keep(db, db.get(User, 2), changed, existing=record)
    assert rejected.value.status_code == 409
    assert record.cargo_revision == 1
    history.keep(db, db.get(User, 2), changed.model_copy(update={
        "expected_cargo_revision": 1,
    }), existing=record)
    assert record.cargo_revision == 2
    result = client_as(db, 2).get(f"/api/shipments/{record.id}/cargo/v1")
    assert result.status_code == 200
    assert result.json()["cargo"]["revision"] == 2
    assert result.json()["totals"]["occupied_volume_m3"] == 3
