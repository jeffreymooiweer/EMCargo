"""The administrator's audit log: who did what, and never what the goods were.

What is pinned here:

1. **The routes write it.** Signing in, failing to, signing out, changing a
   password, managing an account, changing a setting, keeping and forgetting
   a shipment, handing out documents: each leaves one line with the actor,
   the action and a short summary.
2. **Metadata only.** The summary of a settings change names the keys and
   never a value; the summary of a document export names the document key
   and nothing from the form; the mail line counts recipients and never
   names them. The whole table is searched for the consignment's words.
3. **Only an administrator reads it** — 403 for a user, 401 without a
   session, including deployments with a retired mode variable.
4. **The retention** an administrator sets is applied at start-up.
5. **The schema step** exists, so an old database gets the table.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.main import create_app
from app.models.audit import AuditEvent
from app.models.user import User
from app.services import audit, settings_store
from app.schemas.settings import InstanceSettings
from tests.test_export_bundle import CONSIGNMENT, PRODUCT, doc
from tests.test_history import shipment

PASSWORD = "correct horse battery staple"


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    monkeypatch.delenv("EMCARGO_MODE", raising=False)
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="ada", email="ada@example.com",
                     password_hash=hash_password(PASSWORD), role="admin"))
    session.add(User(id=2, username="bob", email="bob@example.com",
                     password_hash=hash_password(PASSWORD), role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def application(db, *, as_user: int | None = None) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    if as_user is not None:
        app.dependency_overrides[get_current_user] = lambda: db.get(User, as_user)
        if db.get(User, as_user).role == "admin":
            app.dependency_overrides[require_admin] = lambda: db.get(User, as_user)
    return TestClient(app)


def rows(db) -> list[AuditEvent]:
    return list(db.execute(select(AuditEvent).order_by(AuditEvent.id)).scalars())


def actions(db) -> list[str]:
    return [r.action for r in rows(db)]


# --- what the routes write ---------------------------------------------------


def test_signing_in_and_failing_to_are_both_written(db):
    with application(db) as client:
        assert client.post("/api/auth/login", json={"username": "ada", "password": "wrong"}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "nobody", "password": "x"}).status_code == 401
        assert client.post("/api/auth/login", json={"username": "ada", "password": PASSWORD}).status_code == 200
        assert client.post("/api/auth/logout").json()["ok"] is True
    events = rows(db)
    assert [e.action for e in events] == [
        "auth.login_failed", "auth.login_failed", "auth.login", "auth.logout"]
    assert events[0].actor_username == "ada" and events[0].summary == "wrong password"
    assert events[0].actor_id is None
    assert events[1].actor_username == "nobody" and events[1].summary == "unknown name"
    assert events[2].actor_id == 1 and events[2].summary == "password"
    assert events[2].client == "testclient"
    assert events[3].actor_username == "ada"


def test_an_inactive_account_is_refused_and_written(db):
    db.get(User, 2).active = False
    db.commit()
    with application(db) as client:
        assert client.post("/api/auth/login", json={"username": "bob", "password": PASSWORD}).status_code == 403
    assert actions(db) == ["auth.login_failed"]
    assert rows(db)[0].summary == "inactive account"


def test_a_password_change_is_written_without_the_password(db):
    with application(db, as_user=2) as client:
        response = client.post("/api/auth/change-password", json={
            "current_password": PASSWORD, "new_password": "another long password"})
        assert response.status_code == 200, response.text
    assert actions(db) == ["auth.password_changed"]
    assert "another" not in rows(db)[0].summary


def test_self_service_password_change_requires_current_password_and_expires_sessions(db):
    """The account form must preserve access on a failed change and force a
    fresh sign-in after success, including cookies held on another device."""
    with application(db) as client:
        credentials = {"username": "bob", "password": PASSWORD}
        assert client.post("/api/auth/login", json=credentials).status_code == 200
        previous_token = client.cookies.get("access_token")
        failed = client.post("/api/auth/change-password", json={"current_password": "incorrect", "new_password": "new synthetic password"})
        assert failed.status_code == 400
        assert failed.json()["detail"]["code"] == "auth.current_password_incorrect"
        assert client.get("/api/auth/me").status_code == 200
        assert "auth.password_changed" not in actions(db)
        changed = client.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "new synthetic password"})
        assert changed.json() == {"ok": True, "reauthenticate": True}
        assert client.get("/api/auth/me").status_code == 401
        client.cookies.clear()
        client.cookies.set("access_token", previous_token)
        assert client.get("/api/auth/me").status_code == 401
        assert client.post("/api/auth/login", json=credentials).status_code == 401
        assert client.post("/api/auth/login", json={**credentials, "password": "new synthetic password"}).status_code == 200
        assert client.get("/api/auth/me").status_code == 200


def test_account_management_names_the_account_and_the_fields(db):
    with application(db, as_user=1) as client:
        made = client.post("/api/users", json={
            "username": "cleo", "email": "cleo@example.com",
            "password": "a long enough password", "role": "user"})
        assert made.status_code == 200, made.text
        cleo = made.json()["id"]
        assert client.patch(f"/api/users/{cleo}", json={
            "password": "a different long password", "role": "admin"}).status_code == 200
        assert client.delete(f"/api/users/{cleo}/two-factor").status_code == 200
        assert client.delete(f"/api/users/{cleo}").status_code == 200
    events = rows(db)
    assert [e.action for e in events] == [
        "user.created", "user.updated", "user.two_factor_cleared", "user.deleted"]
    assert all(e.actor_username == "ada" and e.target_type == "user"
               and e.target_id == str(cleo) for e in events)
    assert events[0].summary == "cleo (user)"
    assert events[1].summary == "cleo: password, role"
    assert events[3].summary == "cleo"
    assert not any("different" in e.summary for e in events)


def test_a_settings_change_names_the_keys_and_never_the_values(db):
    with application(db, as_user=1) as client:
        current = client.get("/api/settings/instance").json()
        changed = {**current, "mail_host": "mail.example.com",
                   "mail_password": "hunter2", "audit_retention_days": 90}
        assert client.put("/api/settings/instance", json=changed).status_code == 200
        # Saving the same thing again is not a change.
        again = client.get("/api/settings/instance").json()
        assert client.put("/api/settings/instance", json=again).status_code == 200
    events = rows(db)
    assert [e.action for e in events] == ["settings.changed"]
    assert events[0].summary == "audit_retention_days, mail_host, mail_password, mail_password_set"
    assert "hunter2" not in events[0].summary
    assert "mail.example.com" not in events[0].summary


def test_shipments_and_documents_leave_lines_without_the_goods(db):
    with application(db, as_user=2) as client:
        kept = client.post("/api/shipments", json=shipment())
        assert kept.status_code == 200, kept.text
        shipment_id = kept.json()["id"]
        assert client.put(f"/api/shipments/{shipment_id}", json=shipment()).status_code == 200
        assert client.get(f"/api/shipments/{shipment_id}/export.json").status_code == 200
        assert client.post(f"/api/shipments/{shipment_id}/documents").status_code == 200
        assert client.post("/api/documents/export", json=doc("cmr")).status_code == 200
        assert client.post("/api/documents/export/bundle", json={
            "documents": [doc("cmr")],
            "output_language": "nl"}).status_code == 200
        assert client.delete(f"/api/shipments/{shipment_id}").status_code == 200
    events = rows(db)
    assert [e.action for e in events] == [
        "shipment.kept", "shipment.updated", "shipment.export", "shipment.documents",
        "documents.exported", "documents.bundle", "shipment.forgotten"]
    for e in events[:4]:
        assert e.target_type == "shipment" and e.target_id == str(shipment_id)
        assert e.summary == "CP-2026-100"
    assert events[4].summary == "cmr" and events[5].summary == "cmr"
    assert events[6].summary == "CP-2026-100"
    # Nothing a consignment says is in the table: not a party, not a good.
    everything = " ".join(f"{e.summary} {e.target_id}" for e in events)
    for word in (CONSIGNMENT["consignor_name"], CONSIGNMENT["consignee_name"],
                 PRODUCT["proper_shipping_name"], PRODUCT["un_number"]):
        assert word not in everything, word


# --- who may read it -----------------------------------------------------------


def test_the_export_hands_a_spreadsheet_text_not_formulas(db):
    audit.record(db, "shipment.kept", actor=db.get(User, 1), target=("shipment", 1),
                 summary="=1+1")
    audit.record(db, "user.created", actor=db.get(User, 1), target=("user", 9),
                 summary="@cmd|'/C calc'!A0")
    body = audit.export_csv(db)
    assert "'=1+1" in body and ",=1+1" not in body
    assert "'@cmd" in body
    assert audit.csv_cell("2026-09-06T08:30:00") == "2026-09-06T08:30:00"
    assert audit.csv_cell("-5") == "'-5" and audit.csv_cell("+1") == "'+1"


def test_only_an_administrator_reads_it(db):
    audit.record(db, "auth.login", actor=db.get(User, 1), summary="password")
    with application(db) as client:
        assert client.get("/api/audit").status_code == 401
    with application(db, as_user=2) as client:
        assert client.get("/api/audit").status_code == 403
        assert client.get("/api/audit/export.csv").status_code == 403
    with application(db, as_user=1) as client:
        page = client.get("/api/audit").json()
        assert page["total"] == 1 and page["items"][0]["action"] == "auth.login"
        assert client.get("/api/audit/actions").json()["actors"] == ["ada"]
        assert "auth.login" in client.get("/api/audit/actions").json()["actions"]
        csv = client.get("/api/audit/export.csv")
        assert csv.headers["content-type"].startswith("text/csv")
        assert csv.text.splitlines()[0] == "at,actor,action,target_type,target_id,summary,client"
        assert "ada,auth.login" in csv.text


def test_the_filters_narrow_the_page(db):
    ada, bob = db.get(User, 1), db.get(User, 2)
    audit.record(db, "auth.login", actor=ada)
    audit.record(db, "auth.login", actor=bob)
    audit.record(db, "shipment.kept", actor=bob, target=("shipment", 7), summary="X-1")
    with application(db, as_user=1) as client:
        assert client.get("/api/audit", params={"actor": "bob"}).json()["total"] == 2
        assert client.get("/api/audit", params={"action": "shipment.kept"}).json()["total"] == 1
        # A group filters on its prefix.
        assert client.get("/api/audit", params={"action": "auth"}).json()["total"] == 2
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        assert client.get("/api/audit", params={"since": tomorrow}).json()["total"] == 0
        paged = client.get("/api/audit", params={"per_page": 2, "page": 2}).json()
        assert paged["total"] == 3 and len(paged["items"]) == 1
        assert client.get("/api/audit/actions").json()["actors"] == ["ada", "bob"]


def test_a_retired_mode_variable_cannot_disable_auditing(db, monkeypatch):
    """Old deployment variables must not silently stop recording account actions
    after guest access is retired; the existing audit records must stay visible.
    """
    monkeypatch.setenv("EMCARGO_MODE", "open")
    get_settings.cache_clear()
    with application(db, as_user=1) as client:
        assert client.post("/api/documents/export", json=doc("cmr")).status_code == 200
        assert client.get("/api/audit").status_code == 200
    assert "documents.exported" in actions(db)


def test_an_unknown_action_is_a_programming_error(db):
    with pytest.raises(ValueError):
        audit.record(db, "shipment.launched")


# --- retention ------------------------------------------------------------------


def test_the_retention_is_applied(db):
    old = AuditEvent(actor_username="ada", action="auth.login",
                     at=datetime.now(timezone.utc) - timedelta(days=400))
    recent = AuditEvent(actor_username="ada", action="auth.login")
    db.add_all([old, recent])
    db.commit()
    assert audit.prune(db, audit.DEFAULT_RETENTION_DAYS) == 1
    assert len(rows(db)) == 1
    assert audit.prune(db, 365) == 0


def test_the_retention_is_a_setting_with_bounds(db):
    settings_store.save_instance_settings(db, InstanceSettings(audit_retention_days=30))
    assert settings_store.instance_settings(db).audit_retention_days == 30
    with pytest.raises(ValueError):
        InstanceSettings(audit_retention_days=0)
    with pytest.raises(ValueError):
        InstanceSettings(audit_retention_days=4000)
    assert InstanceSettings().audit_retention_days == audit.DEFAULT_RETENTION_DAYS


# --- the schema ------------------------------------------------------------------


def test_the_schema_step_makes_the_table_on_an_old_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(engine)
    assert not inspect(engine).has_table("audit_events")
    migrations.run(engine, fresh=False)
    assert inspect(engine).has_table("audit_events")
    assert "audit_events" in [name for _v, name, _s in migrations.MIGRATIONS]


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled", "synthetic_templates")
