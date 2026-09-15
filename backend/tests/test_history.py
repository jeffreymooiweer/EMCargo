"""The shipment history: kept only where the switch is on, and never orphaned.

What is pinned here, in the order it matters:

1. **With the switch off the addresses do not exist.** Not 401, not 403 — 404,
   like every other route the installation does not have. The open
   application ignores the switch altogether.
2. **The switch is the administrator's** — a setting on the screen, read on
   every request — and off never hides data: switching it off with kept
   shipments in the table is refused until they are deleted, on the screen,
   after a confirmation that names the counts; and a database that holds
   shipments while the setting says off gets the setting switched back on
   at start-up.
3. **The kept record is the structured export, built by the server** from
   the same parts the download uses, so the two cannot disagree — and the
   index columns a list filters on come out of it.
4. **The documents again come from the kept bundle**, through the same code
   path as the export step's download.
5. **The schema runner** stamps a fresh database and migrates an old one, and
   running it twice does nothing the second time.
"""
from __future__ import annotations

import io
import logging
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.user import User
from app.services import history, settings_store
from tests.test_export_bundle import CONSIGNMENT, DG, doc


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
    monkeypatch.delenv("EMCARGO_HISTORY", raising=False)
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="ada", email="ada@example.com",
                     password_hash="x", role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def application(db, monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, 1)
    return TestClient(app)


ADA = SimpleNamespace(id=1, username="ada", role="user", active=True)


def switch_history(db, on: bool) -> None:
    """What the administrator's toggle does: save the setting."""
    current = settings_store.instance_settings(db)
    settings_store.save_instance_settings(db, current.model_copy(update={"history_enabled": on}))


def administrator(db, monkeypatch, **env):
    """A client signed in as an administrator, for the settings routes."""
    from app.core.deps import require_admin

    db.get(User, 1).role = "admin"
    db.commit()
    client = application(db, monkeypatch, **env)
    client.app.dependency_overrides[require_admin] = lambda: db.get(User, 1)
    return client


def shipment(**overrides) -> dict:
    payload = {
        "modality": "road",
        "language": "nl",
        "profiles": ["ADR"],
        "values": dict(CONSIGNMENT),
        "lines": [{"description": "Vaten benzine", "quantity": 4, "weight_total_kg": 800.0}],
        "dangerous_goods": DG,
        "documents": ["cmr"],
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "snapshot": {"version": 1, "stepKey": "export", "docValues": dict(CONSIGNMENT)},
    }
    payload.update(overrides)
    return payload


# --- 1. the addresses exist only with the switch --------------------------------


def test_without_the_switch_the_shipments_routes_do_not_exist(db, monkeypatch):
    with application(db, monkeypatch) as client:
        assert client.get("/api/shipments").status_code == 404
        assert client.post("/api/shipments", json=shipment()).status_code == 404
        assert client.get("/api/settings/public").json()["history_enabled"] is False
        assert client.get("/api/health").json()["history"] is False


def test_with_the_switch_they_do(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        assert client.get("/api/shipments").status_code == 200
        assert client.get("/api/settings/public").json()["history_enabled"] is True
        assert client.get("/api/health").json()["history"] is True


def test_a_retired_mode_variable_cannot_hide_kept_shipments(db, monkeypatch):
    """Upgrading a former guest installation must not hide existing history.
    Login is mandatory, while the saved retention setting still controls data.
    """
    switch_history(db, True)
    with application(db, monkeypatch, EMCARGO_HISTORY="true", EMCARGO_MODE="open") as client:
        assert client.get("/api/shipments").status_code == 200
        assert client.get("/api/health").json()["history"] is True
    assert settings_store.history_enabled(db) is True


# --- 2. the switch is the administrator's, and off never hides data ---------------


def test_the_setting_switches_the_routes_on_and_off_without_a_restart(db, monkeypatch):
    with application(db, monkeypatch) as client:
        assert client.get("/api/shipments").status_code == 404
        switch_history(db, True)
        assert client.get("/api/shipments").status_code == 200
        assert client.get("/api/settings/public").json()["history_enabled"] is True
        switch_history(db, False)
        assert client.get("/api/shipments").status_code == 404
        assert client.get("/api/settings/public").json()["history_enabled"] is False


def test_a_saved_setting_overrules_the_legacy_variable(db, monkeypatch):
    switch_history(db, False)
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        assert client.get("/api/shipments").status_code == 404
        assert client.get("/api/health").json()["history"] is False


def test_switching_off_with_kept_shipments_is_refused_until_they_are_deleted(db, monkeypatch):
    switch_history(db, True)
    with administrator(db, monkeypatch) as client:
        assert client.post("/api/shipments", json=shipment()).status_code == 200
        current = client.get("/api/settings/instance").json()
        refused = client.put("/api/settings/instance", json={**current, "history_enabled": False})
        assert refused.status_code == 409
        assert "1 kept shipment(s)" in refused.json()["detail"]
        assert settings_store.history_enabled(db) is True
        assert history.count(db) == 1

        assert client.get("/api/settings/instance/history").json() == {"shipments": 1, "trips": 0}
        gone = client.post("/api/settings/instance/history/discard").json()
        assert gone == {"ok": True, "shipments": 1, "trips": 0}
        assert history.count(db) == 0
        assert client.put("/api/settings/instance",
                          json={**current, "history_enabled": False}).status_code == 200
        assert client.get("/api/shipments").status_code == 404
    from app.models.audit import AuditEvent
    actions = [e.action for e in db.query(AuditEvent).order_by(AuditEvent.id)]
    assert "settings.history_discarded" in actions
    assert "settings.changed" in actions


def test_switching_off_an_empty_history_needs_no_deletion(db, monkeypatch):
    switch_history(db, True)
    with administrator(db, monkeypatch) as client:
        current = client.get("/api/settings/instance").json()
        assert client.put("/api/settings/instance",
                          json={**current, "history_enabled": False}).status_code == 200
        assert client.get("/api/shipments").status_code == 404


def test_start_up_switches_the_history_on_for_a_database_that_holds_shipments(db, monkeypatch, caplog):
    """The upgrade from the deploy-time variable: an installation that dropped
    it from its environment must not wake up with a hidden table."""
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    get_settings.cache_clear()
    history.keep(db, ADA, history.ShipmentIn(**shipment()))
    monkeypatch.delenv("EMCARGO_HISTORY")
    get_settings.cache_clear()
    assert settings_store.history_enabled(db) is False
    with caplog.at_level(logging.WARNING):
        assert history.adopt_kept_data(db) is True
    assert settings_store.history_enabled(db) is True
    assert "1 kept shipment(s)" in caplog.text
    assert history.count(db) == 1
    # And it does not keep saying so.
    assert history.adopt_kept_data(db) is False


def test_an_empty_table_is_left_alone(db):
    assert history.adopt_kept_data(db) is False
    assert settings_store.history_enabled(db) is False


# --- 3. the kept record ---------------------------------------------------------


def test_keeping_builds_the_export_and_the_index_from_the_same_parts(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        created = client.post("/api/shipments", json=shipment())
        assert created.status_code == 200, created.text
        summary = created.json()
        assert summary["reference"] == "CP-2026-100"
        assert summary["consignor_name"] == "Afzender BV"
        # The wizard's own field name wins over the fallback.
        wizard_named = client.post("/api/shipments", json=shipment(
            values={**CONSIGNMENT, "shipment_reference": "WZ-1"})).json()
        assert wizard_named["reference"] == "WZ-1"
        assert summary["consignee_name"] == "Ontvanger GmbH"
        assert summary["modality"] == "road"
        assert summary["regulations"] == ["ADR"]
        assert summary["goods_count"] == 1
        assert summary["has_dangerous_goods"] is True
        assert summary["has_documents"] is True
        assert summary["created_by"] == "ada"

        detail = client.get(f"/api/shipments/{summary['id']}").json()
        export = detail["export"]
        assert export["format"] == "emcargo.shipment"
        assert export["consignment"]["reference"] == "CP-2026-100"
        assert export["regulations"] == ["ADR"]
        # The derived half is there, with the editions it was computed against.
        assert "compliance" in export
        assert detail["snapshot"]["stepKey"] == "export"

        as_file = client.get(f"/api/shipments/{summary['id']}/export.json")
        assert as_file.status_code == 200
        assert 'filename="emcargo-shipment-CP-2026-100.json"' in \
            as_file.headers["content-disposition"]


def test_a_reference_outside_latin_1_still_downloads(db, monkeypatch):
    """An emoji in the reference turned the export into a 500: the name was
    written into the header as it was, and a header is ISO 8859-1."""
    from app.core.http import attachment

    with application(db, monkeypatch) as client:
        switch_history(db, True)
        kept = client.post("/api/shipments", json=shipment(
            values={**CONSIGNMENT, "reference": "CP-\U0001f69a-1"}))
        assert kept.status_code == 200, kept.text
        response = client.get(f"/api/shipments/{kept.json()['id']}/export.json")
    assert response.status_code == 200
    assert response.headers["content-disposition"] == (
        "attachment; filename=\"emcargo-shipment-CP--1.json\"; "
        "filename*=UTF-8''emcargo-shipment-CP-%F0%9F%9A%9A-1.json")
    assert attachment("plain.json") == 'attachment; filename="plain.json"'
    assert attachment('a"b\r\nc.json') == 'attachment; filename="a_b__c.json"'
    assert attachment("Zoë.json").startswith('attachment; filename="Zoe.json"; filename*=')


def test_keeping_again_brings_the_same_row_up_to_date(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        first = client.post("/api/shipments", json=shipment()).json()
        changed = shipment(values={**CONSIGNMENT, "reference": "CP-2026-101"})
        second = client.put(f"/api/shipments/{first['id']}", json=changed).json()
        assert second["id"] == first["id"]
        assert second["reference"] == "CP-2026-101"
        assert client.get("/api/shipments").json()["total"] == 1


def test_the_list_filters_and_pages_newest_first(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        for reference, modality in (("A-1", "road"), ("B-2", "sea"), ("A-3", "road")):
            client.post("/api/shipments", json=shipment(
                modality=modality, dangerous_goods=[], values={**CONSIGNMENT, "reference": reference}))
        everything = client.get("/api/shipments").json()
        assert [s["reference"] for s in everything["items"]] == ["A-3", "B-2", "A-1"]
        assert everything["total"] == 3

        assert [s["reference"] for s in
                client.get("/api/shipments?q=a-").json()["items"]] == ["A-3", "A-1"]
        assert [s["reference"] for s in
                client.get("/api/shipments?modality=sea").json()["items"]] == ["B-2"]
        by_name = client.get("/api/shipments?q=ontvanger").json()
        assert by_name["total"] == 3

        page = client.get("/api/shipments?per_page=2&page=2").json()
        assert [s["reference"] for s in page["items"]] == ["A-1"]
        assert page["total"] == 3


def test_a_shipment_kept_without_ready_documents_says_so(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        kept = client.post("/api/shipments", json=shipment(bundle=None)).json()
        assert kept["has_documents"] is False
        again = client.post(f"/api/shipments/{kept['id']}/documents")
        assert again.status_code == 404


def test_forgetting_removes_the_row(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        kept = client.post("/api/shipments", json=shipment()).json()
        assert client.delete(f"/api/shipments/{kept['id']}").json()["ok"] is True
        assert client.get(f"/api/shipments/{kept['id']}").status_code == 404
        assert client.delete(f"/api/shipments/{kept['id']}").status_code == 404
    assert history.count(db) == 0


def test_a_record_too_large_is_refused_before_it_is_kept(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        bloated = shipment(snapshot={"blob": "x" * (history.MAX_RECORD_BYTES + 1)})
        assert client.post("/api/shipments", json=bloated).status_code == 413
    assert history.count(db) == 0


# --- 3b. drafts: entry in progress, kept but not counted as a shipment ----------


def test_a_draft_is_kept_but_is_not_a_kept_shipment(db, monkeypatch):
    """The point of the whole feature: a reload must not lose the entry, and a
    half-typed consignment must not turn up in the history as if it went."""
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        saved = client.put("/api/shipments/draft", json=shipment()).json()
        assert saved["is_draft"] is True
        # Not on the shipments page, and not counted as kept.
        assert client.get("/api/shipments").json()["total"] == 0
        assert history.count(db) == 0
        # But the entry itself comes back, snapshot and all.
        draft = client.get("/api/shipments/draft").json()
        assert draft["id"] == saved["id"]
        assert draft["snapshot"]["stepKey"] == "export"


def test_saving_the_draft_again_writes_the_same_row(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        first = client.put("/api/shipments/draft", json=shipment()).json()
        second = client.put("/api/shipments/draft", json=shipment(
            snapshot={"version": 1, "stepKey": "details"})).json()
        assert second["id"] == first["id"]
        assert client.get("/api/shipments/draft").json()["snapshot"]["stepKey"] == "details"


def test_keeping_the_draft_as_a_shipment_makes_it_one(db, monkeypatch):
    """No second row and no copying: the same row, with the flag off."""
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        draft = client.put("/api/shipments/draft", json=shipment()).json()
        kept = client.put(f"/api/shipments/{draft['id']}", json=shipment()).json()
        assert kept["id"] == draft["id"]
        assert kept["is_draft"] is False
        assert client.get("/api/shipments").json()["total"] == 1
        assert client.get("/api/shipments/draft").json() is None


def test_a_discarded_draft_leaves_nothing(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        client.put("/api/shipments/draft", json=shipment())
        assert client.delete("/api/shipments/draft").json()["ok"] is True
        assert client.get("/api/shipments/draft").json() is None


def test_nobody_elses_draft(db, monkeypatch):
    """A draft is unfinished entry, not a record a colleague may read: the
    department rules that open a kept shipment to others stop here."""
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        client.put("/api/shipments/draft", json=shipment())
        other = User(id=2, username="bob", role="user", active=True)
        assert history.running_draft(db, other) is None


def test_the_annual_report_counts_shipments_and_not_drafts(db, monkeypatch):
    from datetime import datetime
    db.get(User, 1).role = "dg_specialist"
    db.commit()

    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        client.post("/api/shipments", json=shipment())
        client.put("/api/shipments/draft", json=shipment())
        year = datetime.now().year
        report = client.get(f"/api/shipments/report?year={year}").json()
        assert report["totals"]["shipments"] == 1


def test_switching_the_history_off_discards_the_drafts(db, monkeypatch):
    """Off means nothing is kept. A draft does not stand in the way of the
    switch — it is not a kept shipment — but it must not survive it either."""
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        client.put("/api/shipments/draft", json=shipment())
    admin = administrator(db, monkeypatch, EMCARGO_HISTORY="true")
    with admin as client:
        settings = client.get("/api/settings/instance").json()
        settings["history_enabled"] = False
        assert client.put("/api/settings/instance", json=settings).status_code == 200
    assert history.running_draft(db, db.get(User, 1)) is None


# --- 4. the documents again -----------------------------------------------------


def test_the_documents_again_are_the_kept_bundle_rerendered(db, monkeypatch):
    with application(db, monkeypatch, EMCARGO_HISTORY="true") as client:
        kept = client.post("/api/shipments", json=shipment()).json()
        again = client.post(f"/api/shipments/{kept['id']}/documents")
        assert again.status_code == 200, again.text
        assert again.headers["content-type"] == "application/zip"
        assert "CP-2026-100" in again.headers["content-disposition"]
        with zipfile.ZipFile(io.BytesIO(again.content)) as archive:
            names = archive.namelist()
        assert any(name.lower().startswith("cmr") or "cmr" in name.lower() for name in names), names


# --- 5. the schema runner -------------------------------------------------------


def test_a_fresh_database_is_stamped_and_an_old_one_migrated(tmp_path):
    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(bind=fresh_engine)
    assert migrations.run(fresh_engine, fresh=True) == STEPS
    assert migrations.current(fresh_engine) == STEPS[-1]
    assert inspect(fresh_engine).has_table("shipments")

    # A database from before v1.173.0: the users table exists, shipments does not.
    old_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(old_engine)
    assert not inspect(old_engine).has_table("shipments")
    assert migrations.run(old_engine, fresh=False) == STEPS
    assert inspect(old_engine).has_table("shipments")
    # Twice does nothing the second time.
    assert migrations.run(old_engine, fresh=False) == []
    assert migrations.current(old_engine) == STEPS[-1]


def test_a_later_step_runs_on_an_old_database_and_is_stamped_on_a_fresh_one(tmp_path, monkeypatch):
    ran: list[str] = []

    def _004_colour(conn):
        ran.append(f"{NEXT:03d}")
        migrations.add_column(conn, "shipments", "colour VARCHAR(16)")

    monkeypatch.setattr(migrations, "MIGRATIONS",
                        migrations.MIGRATIONS + [(NEXT, "colour", _004_colour)])

    old_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(old_engine)
    assert migrations.run(old_engine, fresh=False) == STEPS + [NEXT]
    assert ran == [f"{NEXT:03d}"]
    with old_engine.connect() as conn:
        assert migrations.column_exists(conn, "shipments", "colour")
        # And adding it again is a no-op, so a restored backup recovers.
        assert migrations.add_column(conn, "shipments", "colour VARCHAR(16)") is False

    fresh_engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}")
    Base.metadata.create_all(bind=fresh_engine)
    assert migrations.run(fresh_engine, fresh=True) == STEPS + [NEXT]
    assert ran == [f"{NEXT:03d}"], "a fresh database is stamped, the step must not run"


def test_a_failed_step_leaves_the_version_where_it_was(tmp_path, monkeypatch):
    def _004_explodes(conn):
        conn.execute(text("SELECT * FROM no_such_table"))

    monkeypatch.setattr(migrations, "MIGRATIONS",
                        migrations.MIGRATIONS + [(NEXT, "explodes", _004_explodes)])
    old_engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    User.__table__.create(old_engine)
    with pytest.raises(Exception):
        migrations.run(old_engine, fresh=False)
    assert migrations.current(old_engine) == STEPS[-1]


# --- the settings answer -------------------------------------------------------


def test_public_settings_say_whether_shipments_are_kept(db, monkeypatch):
    assert settings_store.public_settings(db).history_enabled is False
    # The legacy variable is the starting value ...
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    get_settings.cache_clear()
    assert settings_store.public_settings(db).history_enabled is True
    # ... and the administrator's setting decides from then on.
    switch_history(db, False)
    assert settings_store.public_settings(db).history_enabled is False
    switch_history(db, True)
    assert settings_store.public_settings(db).history_enabled is True


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled", "synthetic_templates")
