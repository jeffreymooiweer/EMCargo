"""Kept groupage trips: the judgement over a load, kept beside the shipments.

What is pinned here:

1. **Only with the switch.** With *Keep shipments* off the trips routes
   answer 404, like the shipments'.
2. **The server judges.** A kept trip carries the check's answer as the
   server computed it from the consignments sent, with the editions, and
   the index columns (points, the lost exemption) come out of that answer.
3. **Reopening returns what was kept**, consignments and result alike.
4. **Who sees it** follows the departments rule the shipments use.
5. **Switching the history off** counts the trips with the shipments, and
   deleting the history deletes them too.
6. **The audit log** gets a line per keep, update and forget.
7. **The schema step** exists for an old database.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.audit import AuditEvent
from app.models.trip import Trip
from app.models.user import Department, User
from app.services import departments, history, trips
from app.schemas.trips import TripIn


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    monkeypatch.delenv("EMCARGO_MODE", raising=False)
    monkeypatch.delenv("EMCARGO_HISTORY", raising=False)
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    sales = Department(id=1, name="Sales")
    session.add(sales)
    session.add(User(id=1, username="ada", email="ada@example.com", password_hash="x",
                     role="user", department_id=1))
    session.add(User(id=2, username="bob", email="bob@example.com", password_hash="x",
                     role="user"))
    session.add(User(id=3, username="root", email="root@example.com", password_hash="x",
                     role="admin"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def application(db, monkeypatch, as_user: int = 1, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, as_user)
    return TestClient(app)


ADA = SimpleNamespace(id=1, username="ada", role="user", active=True, department_id=1)


def petrol(quantity: str) -> dict:
    return {"un_number": "1203", "proper_shipping_name": "BENZINE", "class": "3",
            "transport_category": "2", "adr_total_quantity": quantity}


def trip(**overrides) -> dict:
    payload = {
        "name": "Wezep - Rotterdam, 6 September",
        "consignments": [
            {"name": "Klant A", "entries": [{"products": [petrol("200")]}], "shipment_id": 7},
            {"name": "Klant B", "entries": [{"products": [petrol("200")]}]},
        ],
        "profiles": ["ADR"],
        "language": "en",
        "unit_max_mass_tonnes": 18,
    }
    payload.update(overrides)
    return payload


# --- 1. only with the switch ------------------------------------------------------


def test_without_the_switch_the_trips_routes_do_not_exist(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="false") as client:
        assert client.get("/api/trips").status_code == 404
        assert client.post("/api/trips", json=trip()).status_code == 404
        # The calculation itself is still there for everybody.
        assert client.post("/api/dg/trip", json={
            "consignments": trip()["consignments"], "profiles": ["ADR"]}).status_code == 200


def test_existing_trip_reopens_as_saved_without_recalculation(db, monkeypatch):
    """Legacy editions and the historical calculation must not change on read."""
    old = trips.keep(db, ADA, TripIn(**trip()))
    old_result = old.result_json
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        detail = client.get(f"/api/trips/{old.id}").json()
        assert detail["consignment_count"] == 2
        assert detail["total_points"] == 1200
        assert detail["result"]["exemption_lost"]["consignments"] == ["Klant A", "Klant B"]
        assert "adr" in detail["editions"]
    db.refresh(old)
    assert old.result_json == old_result


def test_legacy_writes_are_refused_and_conversion_creates_no_physical_events(db, monkeypatch):
    """The new workflow cannot silently reinterpret a saved DG calculation as transport."""
    old = trips.keep(db, ADA, TripIn(**trip()))
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        assert client.post("/api/trips", json=trip()).status_code == 409
        assert client.put(f"/api/trips/{old.id}", json=trip(name="Changed")).status_code == 409
        converted = client.post(f"/api/deliveries/v1/from-trip/{old.id}").json()
        assert converted["status"] == "draft"
        assert converted["allocations"] == []
        assert converted["events"] == []
        assert converted["files"] == []
        assert converted["legs"] == []
        assert converted["legacy_trip_id"] == old.id
        assert len(converted["legacy_consignments"]) == 2
    db.refresh(old)
    assert old.name == trip()["name"]


# --- 3/4. the list and who sees it ----------------------------------------------------


def test_the_list_filters_and_follows_the_departments(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        trips.keep(db, ADA, TripIn(**trip(name="Monday")))
        trips.keep(db, ADA, TripIn(**trip(name="Tuesday")))
    with application(db, monkeypatch, as_user=2) as bob:
        # Bob has no department; Sales' trips are not there for him.
        assert bob.get("/api/trips").json()["total"] == 0
        trips.keep(db, db.get(User, 2), TripIn(**trip(name="Bob's van")))
        assert bob.get("/api/trips").json()["total"] == 1
        assert bob.get("/api/trips/1").status_code == 404
    with application(db, monkeypatch, as_user=3) as root:
        everything = root.get("/api/trips").json()
        assert everything["total"] == 3
        assert [t["name"] for t in everything["items"]] == ["Bob's van", "Tuesday", "Monday"]
        assert root.get("/api/trips", params={"q": "tues"}).json()["total"] == 1
        assert root.get("/api/trips", params={"department": "1"}).json()["total"] == 2
        assert root.get("/api/trips", params={"department": "none"}).json()["total"] == 1
        assert root.get("/api/trips/1").status_code == 200


def test_forgetting_removes_the_row(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        kept = trips.detail(trips.keep(db, ADA, TripIn(**trip()))).model_dump()
        assert client.delete(f"/api/trips/{kept['id']}").json()["ok"] is True
        assert client.get(f"/api/trips/{kept['id']}").status_code == 404
        assert client.delete(f"/api/trips/{kept['id']}").status_code == 404
    assert trips.count(db) == 0


def test_a_removed_department_leaves_no_trip_behind_under_its_id(db, monkeypatch):
    """SQLite hands a new department the old id; a trip still carrying it
    would be that department's. Until v1.190.0 the removal cleared users
    and shipments and forgot the trips."""
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        kept = trips.detail(trips.keep(db, ADA, TripIn(**trip()))).model_dump()
        assert kept["department_id"] == 1
    gone = departments.remove(db, db.get(Department, 1))
    assert gone["trips"] == 1
    db.expire_all()
    assert db.get(Trip, kept["id"]).department_id is None
    docks = departments.create(db, "Docks")
    assert docks.id == 1  # the id came back; the trip did not come with it
    assert trips.search(db, SimpleNamespace(id=9, role="user", department_id=1))[1] == 0


# --- 5. the switch ----------------------------------------------------------------------


def test_trips_are_counted_when_the_history_is_switched_off(db, monkeypatch):
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    get_settings.cache_clear()
    trips.keep(db, ADA, TripIn(**trip()))
    assert history.kept_counts(db) == {"shipments": 0, "trips": 1, "deliveries": 0}
    # Start-up with the setting off and a trip in the table switches it on.
    monkeypatch.setenv("EMCARGO_HISTORY", "false")
    get_settings.cache_clear()
    assert history.adopt_kept_data(db) is True
    assert trips.count(db) == 1


def test_discarding_the_history_deletes_trips_too(db, monkeypatch, caplog):
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    get_settings.cache_clear()
    trips.keep(db, ADA, TripIn(**trip()))
    with caplog.at_level(logging.WARNING):
        assert history.discard_kept(db) == {"shipments": 0, "trips": 1, "deliveries": 0}
    assert trips.count(db) == 0
    assert "1 kept trip(s)" in caplog.text


# --- 6. the audit log ---------------------------------------------------------------------


def test_the_audit_log_names_the_trip_and_nothing_on_it(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        kept = trips.detail(trips.keep(db, ADA, TripIn(**trip()))).model_dump()
        assert client.put(f"/api/trips/{kept['id']}", json=trip()).status_code == 409
        client.delete(f"/api/trips/{kept['id']}")
    events = list(db.execute(select(AuditEvent).order_by(AuditEvent.id)).scalars())
    assert [e.action for e in events] == ["trip.forgotten"]
    assert all(e.target_type == "trip" and e.summary == "Wezep - Rotterdam, 6 September"
               for e in events)
    assert not any("Klant" in e.summary or "1203" in e.summary for e in events)


# --- 7. the schema ------------------------------------------------------------------------


def test_the_schema_step_makes_the_table_on_an_old_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(engine)
    Department.__table__.create(engine)
    assert not inspect(engine).has_table("trips")
    migrations.run(engine, fresh=False)
    assert inspect(engine).has_table("trips")
    assert "trips" in [name for _v, name, _s in migrations.MIGRATIONS]
