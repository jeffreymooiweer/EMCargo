"""Departments: who sees whose kept shipments.

The rule is in ``services/departments.py`` and these tests pin it from the
outside: an administrator sees everything and may filter; anybody else sees
their own department's shipments, and a user without a department sees the
unassigned ones — so an organisation that never makes a department keeps
today's behaviour, everybody seeing everything. A shipment another
department kept is, for the viewer, not there: 404, not 403.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.shipment import Shipment
from app.models.user import Department, User
from app.services import departments, history
from tests.test_history import shipment


#: The real schema steps, so adding one does not renumber every assertion.
STEPS = [version for version, _name, _step in migrations.MIGRATIONS]
NEXT = STEPS[-1] + 1


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    sales = Department(id=1, name="Sales")
    yard = Department(id=2, name="Yard")
    session.add_all([sales, yard])
    session.add_all([
        User(id=1, username="root", email="root@example.com", password_hash="x", role="admin"),
        User(id=2, username="ada", email="ada@example.com", password_hash="x", role="user",
             department_id=1),
        User(id=3, username="bob", email="bob@example.com", password_hash="x", role="user",
             department_id=2),
        User(id=4, username="cyd", email="cyd@example.com", password_hash="x", role="user"),
    ])
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def client_as(db, user_id: int) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user_id)
    return TestClient(app)


def kept_by(db, user_id: int, reference: str) -> Shipment:
    from tests.test_export_bundle import CONSIGNMENT

    payload = history.ShipmentIn(**shipment(values={**CONSIGNMENT, "reference": reference}))
    return history.keep(db, db.get(User, user_id), payload)


@pytest.fixture
def three_shipments(db):
    return {
        "sales": kept_by(db, 2, "SALES-1"),
        "yard": kept_by(db, 3, "YARD-1"),
        "nobody": kept_by(db, 4, "NONE-1"),
    }


# --- the rule -------------------------------------------------------------------


def test_a_shipment_carries_its_keepers_department(three_shipments):
    assert three_shipments["sales"].department_id == 1
    assert three_shipments["yard"].department_id == 2
    assert three_shipments["nobody"].department_id is None


def test_a_user_sees_their_own_departments_shipments(db, three_shipments):
    with client_as(db, 2) as ada:
        seen = [s["reference"] for s in ada.get("/api/shipments").json()["items"]]
        assert seen == ["SALES-1"]
        # The summary names the department, for the page.
        assert ada.get("/api/shipments").json()["items"][0]["department"] == "Sales"
        # Somebody else's shipment is not there — not forbidden, absent.
        assert ada.get(f"/api/shipments/{three_shipments['yard'].id}").status_code == 404
        assert ada.delete(f"/api/shipments/{three_shipments['yard'].id}").status_code == 404
        assert ada.post(f"/api/shipments/{three_shipments['yard'].id}/documents").status_code == 404
        # And an administrator's filter means nothing to them.
        assert [s["reference"] for s in
                ada.get("/api/shipments?department=2").json()["items"]] == ["SALES-1"]


def test_a_user_without_a_department_sees_the_unassigned_pool(db, three_shipments):
    with client_as(db, 4) as cyd:
        assert [s["reference"] for s in cyd.get("/api/shipments").json()["items"]] == ["NONE-1"]
        assert cyd.get(f"/api/shipments/{three_shipments['sales'].id}").status_code == 404


def test_an_administrator_sees_everything_and_may_filter(db, three_shipments):
    with client_as(db, 1) as root:
        everything = root.get("/api/shipments").json()
        assert everything["total"] == 3
        assert [s["reference"] for s in
                root.get("/api/shipments?department=1").json()["items"]] == ["SALES-1"]
        assert [s["reference"] for s in
                root.get("/api/shipments?department=none").json()["items"]] == ["NONE-1"]
        assert root.get(f"/api/shipments/{three_shipments['yard'].id}").status_code == 200


def test_moving_departments_does_not_move_old_shipments(db, three_shipments):
    ada = db.get(User, 2)
    ada.department_id = 2
    db.commit()
    with client_as(db, 2) as client:
        assert [s["reference"] for s in client.get("/api/shipments").json()["items"]] == ["YARD-1"]
    assert three_shipments["sales"].department_id == 1


def test_keeping_again_keeps_the_original_department(db, three_shipments):
    from tests.test_export_bundle import CONSIGNMENT

    record = three_shipments["sales"]
    root = db.get(User, 1)
    history.keep(db, root, history.ShipmentIn(
        **shipment(values={**CONSIGNMENT, "reference": "SALES-1b"})), existing=record)
    assert record.department_id == 1
    assert record.reference == "SALES-1b"


@pytest.mark.parametrize("viewer_id", [1, 3, 5])
def test_direct_draft_addresses_remain_private_to_the_author(db, viewer_id):
    """Hiding a draft from lists did not protect its predictable id: the
    shared record helper let a colleague read, rewrite, export or delete it.
    Administrators must not gain access to another person's unfinished entry
    either; their broader department access applies only to kept shipments.
    """
    db.add(User(id=5, username="eve", email="eve@example.com", password_hash="x",
                role="user", department_id=1))
    db.commit()
    payload = history.ShipmentIn(**shipment(draft=True))
    record = history.keep(db, db.get(User, 2), payload)
    record_id = record.id
    original_snapshot = record.snapshot_json

    with client_as(db, viewer_id) as client:
        path = f"/api/shipments/{record_id}"
        assert client.get(path).status_code == 404
        assert client.get(f"{path}/export.json").status_code == 404
        assert client.post(f"{path}/documents").status_code == 404
        assert client.put(path, json=shipment()).status_code == 404
        assert client.delete(path).status_code == 404
        assert client.get("/api/shipments/draft").json() is None

    db.expire_all()
    unchanged = db.get(Shipment, record_id)
    assert unchanged.is_draft is True
    assert unchanged.created_by_id == 2
    assert unchanged.snapshot_json == original_snapshot


@pytest.mark.parametrize("new_department,new_colleague", [(2, 3), (None, 4)])
def test_author_can_finish_a_draft_after_moving_departments(db, new_department, new_colleague):
    """A running draft follows its author until it is completed. Applying
    only the ordinary department guard to its id stranded an entry after a
    transfer, even though the dedicated draft endpoint still restored it.
    Its first publication belongs to the author's current department: sharing
    an unfinished entry with the old department both exposed it to former
    colleagues and immediately locked the author out of their own result.
    """
    record = history.keep(db, db.get(User, 2), history.ShipmentIn(**shipment(draft=True)))
    record_id = record.id
    db.add(User(id=5, username="eve", email="eve@example.com", password_hash="x",
                role="user", department_id=1))
    db.get(User, 2).department_id = new_department
    db.commit()

    with client_as(db, 2) as author:
        path = f"/api/shipments/{record_id}"
        assert author.get(path).json()["snapshot"] == shipment()["snapshot"]
        assert author.get(f"{path}/export.json").status_code == 200
        completed = author.put(path, json=shipment())
        assert completed.status_code == 200, completed.text
        assert completed.json()["is_draft"] is False
        assert completed.json()["department_id"] == new_department
        assert author.get("/api/shipments/draft").json() is None
        assert author.get(path).status_code == 200

    with client_as(db, 5) as old_colleague:
        assert old_colleague.get(path).status_code == 404
        assert old_colleague.get("/api/shipments").json()["total"] == 0
    with client_as(db, new_colleague) as current_colleague:
        assert current_colleague.get(path).status_code == 200
        assert current_colleague.get("/api/shipments").json()["total"] == 1

    with client_as(db, 1) as administrator:
        assert administrator.get(path).status_code == 200


def test_an_unassigned_colleague_cannot_delete_another_users_draft(db):
    """An installation without departments is the default case. Matching
    two NULL department ids must never grant ownership of a private draft.
    """
    db.get(User, 2).department_id = None
    db.commit()
    record = history.keep(db, db.get(User, 2), history.ShipmentIn(**shipment(draft=True)))
    record_id = record.id
    with client_as(db, 4) as colleague:
        assert colleague.get(f"/api/shipments/{record_id}").status_code == 404
        assert colleague.delete(f"/api/shipments/{record_id}").status_code == 404
    with client_as(db, 2) as author:
        assert author.delete(f"/api/shipments/{record_id}").status_code == 200


# --- managing them ----------------------------------------------------------------


def test_everybody_reads_the_list_and_only_an_administrator_changes_it(db, three_shipments):
    with client_as(db, 2) as ada:
        listed = ada.get("/api/departments").json()
        assert [(d["name"], d["users"], d["shipments"]) for d in listed] == \
            [("Sales", 1, 1), ("Yard", 1, 1)]
        assert ada.post("/api/departments", json={"name": "Docks"}).status_code == 403
        assert ada.put("/api/departments/1", json={"name": "X"}).status_code == 403
        assert ada.delete("/api/departments/1").status_code == 403


def test_an_administrator_creates_renames_and_removes(db, three_shipments):
    with client_as(db, 1) as root:
        created = root.post("/api/departments", json={"name": "  Docks  "})
        assert created.status_code == 200
        assert created.json()["name"] == "Docks"
        # Names are unique, case-insensitively.
        assert root.post("/api/departments", json={"name": "docks"}).status_code == 409
        assert root.post("/api/departments", json={"name": "   "}).status_code in (409, 422)
        assert root.put("/api/departments/1", json={"name": "Yard"}).status_code == 409
        assert root.put("/api/departments/1", json={"name": "Sales & Export"}).json()["name"] == "Sales & Export"

        # Assigning a user: an id must be real, null takes them out.
        assert root.patch("/api/users/4", json={"department_id": 99}).status_code == 404
        assert root.patch("/api/users/4", json={"department_id": created.json()["id"]}).json()["department_id"] == created.json()["id"]
        assert root.patch("/api/users/4", json={"department_id": None}).json()["department_id"] is None
        # A patch that does not mention the department leaves it alone.
        root.patch("/api/users/2", json={"active": True})
        assert db.get(User, 2).department_id == 1

        # Removing leaves people and shipments without a department, not gone.
        gone = root.delete("/api/departments/1").json()
        assert gone == {"ok": True, "users": 1, "shipments": 1, "trips": 0, "deliveries": 0}
        db.expire_all()
        assert db.get(User, 2).department_id is None
        assert three_shipments["sales"].department_id is None
        assert db.get(Shipment, three_shipments["sales"].id) is not None
        assert root.delete("/api/departments/1").status_code == 404


def test_the_users_list_says_who_is_where(db):
    with client_as(db, 1) as root:
        by_name = {u["username"]: u["department_id"] for u in root.get("/api/users").json()}
        assert by_name == {"root": None, "ada": 1, "bob": 2, "cyd": None}


# --- the schema step ---------------------------------------------------------------


def test_step_two_brings_a_v1_173_database_along(tmp_path):
    """A database from v1.173.0 has users and shipments without the column
    and no departments table. The step adds all three, and is idempotent."""
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(64), email VARCHAR(255), "
            "password_hash VARCHAR(255), role VARCHAR(16), active BOOLEAN, created_at DATETIME)")
    assert migrations.run(engine, fresh=False) == STEPS
    inspector = inspect(engine)
    assert inspector.has_table("departments")
    assert "department_id" in {c["name"] for c in inspector.get_columns("users")}
    assert "department_id" in {c["name"] for c in inspector.get_columns("shipments")}
    assert migrations.run(engine, fresh=False) == []


def test_the_rule_in_one_place(db):
    """`visible_to` and `may_see` must agree, or the list would show a row the
    detail refuses — or the other way round."""
    ada, cyd, root = db.get(User, 2), db.get(User, 4), db.get(User, 1)
    for viewer in (ada, cyd, root):
        listed = {s.id for s in departments.visible_to(db.query(Shipment), viewer).all()}
        by_rule = {s.id for s in db.query(Shipment).all() if departments.may_see(s, viewer)}
        assert listed == by_rule, viewer.username


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled")
