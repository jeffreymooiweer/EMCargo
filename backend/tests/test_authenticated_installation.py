"""Retiring guest mode closes every application route, including QR cards.

Exercise real cookies and real route dependencies, including deployments that
still carry EMCARGO_MODE=open. Scanning a transport document never grants
anonymous access to an installation's card store.
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user, require_admin
from app.core.startup import bootstrap_admin
from app.main import create_app
from app.models.user import User
from app.schemas.settings import InstanceSettings
from app.services import settings_store
from tests import route_table

PASSWORD = "a-test-password-for-authenticated-access"


@pytest.fixture(params=[None, "open", "opne"])
def installation(request, tmp_path, monkeypatch):
    if request.param is None:
        monkeypatch.delenv("EMCARGO_MODE", raising=False)
    else:
        monkeypatch.setenv("EMCARGO_MODE", request.param)
    for key, value in {
        "DATA_DIR": str(tmp_path), "APP_ENV": "test", "CATALOG_AUTO_SYNC": "false",
        "ADMIN_USERNAME": "administrator", "ADMIN_EMAIL": "admin@example.com",
        "ADMIN_PASSWORD": PASSWORD, "COOKIE_SECURE": "false",
    }.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        monkeypatch.setattr("app.main.init_app", lambda: bootstrap_admin(db))
        application = create_app()
        application.dependency_overrides[get_db] = lambda: db
        with TestClient(application) as client:
            yield client, db, application, tmp_path
    engine.dispose()
    get_settings.cache_clear()


def login(client):
    response = client.post("/api/auth/login", json={"username": "administrator", "password": PASSWORD})
    assert response.status_code == 200
    assert "access_token" in client.cookies


def test_every_protected_route_requires_a_real_session(installation):
    """A table sweep catches indirect dependencies and future routes as well as
    the wizard. Missing form bodies and path parameters must not bypass login.
    """
    client, _, application, _ = installation
    protected = [address for address in route_table.addresses(application)
                 if address.guards & {get_current_user, require_admin}]
    assert {"/api/calculate", "/api/users", "/api/settings/me", "/api/shipments", "/api/trips", "/api/articles", "/docs", "/openapi.json"} <= {a.path for a in protected}
    for address in protected:
        path = re.sub(r"\{[^}]+\}", "1", address.path)
        for method in address.methods:
            response = client.request(method, path)
            assert response.status_code == 401, (method, path, response.status_code)
    # A made-up cookie must not become the retired visitor account either.
    client.cookies.set("access_token", "not-a-session")
    assert client.post("/api/calculate", json={"lines": []}).status_code == 401


def test_login_unlocks_the_full_application_and_logout_closes_it(installation):
    """Do not trade the guest bypass for missing account routes or a broken
    bootstrap. Real login must unlock work, settings and administrator pages.
    """
    client, db, _, _ = installation
    assert db.query(User).count() == 1
    assert client.get("/api/setup-status").json()["has_admin"] is True
    login(client)
    assert client.get("/api/auth/me").json()["user"]["username"] == "administrator"
    response = client.post("/api/calculate", json={"lines": [{"quantity": 2, "weight_total_kg": 10.0}]})
    assert response.status_code == 200
    assert response.json()["totals"]["total_weight_kg"] == 10.0
    for path in ("/api/users", "/api/settings/me", "/api/settings/instance", "/api/audit", "/docs", "/openapi.json"):
        assert client.get(path).status_code == 200, path
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/users").status_code == 401


def test_qr_lookup_and_pdf_require_login_even_when_links_are_enabled(installation):
    """Enabling links previously exposed both lookup and PDFs without a session.
    Real cookies must unlock both and logout must close even a copied PDF URL.
    """
    client, db, _, data_dir = installation
    assert client.get("/api/cards/lookup?un=1203").status_code == 401
    settings_store.save_instance_settings(db, InstanceSettings(card_links_enabled=True))
    directory = data_dir / "un-cards" / "ADR"
    directory.mkdir(parents=True)
    pdf = b"%PDF-1.4\n% authenticated test card\n"
    (directory / "UN1203_ADR.pdf").write_bytes(pdf)
    assert not client.cookies
    assert client.get("/api/cards/lookup?un=1203&modality=ADR").status_code == 401
    assert client.get("/api/cards/1203/ADR.pdf").status_code == 401
    login(client)
    lookup = client.get("/api/cards/lookup?un=1203&modality=ADR")
    assert lookup.status_code == 200
    assert lookup.json()["cards"] == [{"un_number": "1203", "available": True}]
    download = client.get("/api/cards/1203/ADR.pdf")
    assert download.status_code == 200
    assert download.content == pdf
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/cards/lookup?un=1203&modality=ADR").status_code == 401
    assert client.get("/api/cards/1203/ADR.pdf").status_code == 401


def test_saved_settings_and_existing_accounts_survive_upgrade(installation):
    """An obsolete mode variable must not suppress administrator overrides or
    create another account on every restart. There is no automatic data reset.
    """
    client, db, _, _ = installation
    account = db.query(User).one()
    password_hash = account.password_hash
    settings_store.save_instance_settings(db, InstanceSettings(organisation_name="Existing organisation", history_enabled=True))
    assert bootstrap_admin(db) is True
    assert db.query(User).count() == 1
    assert account.password_hash == password_hash
    login(client)
    shared = client.get("/api/settings/public").json()
    assert shared["organisation_name"] == "Existing organisation"
    assert shared["history_enabled"] is True
    assert client.get("/api/health").json()["mode"] == "organisation"
