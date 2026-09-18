"""The address book: kept only with the history, shared by everybody.

Two rules worth pinning: saving the same party twice brings the one entry up
to date rather than adding a second — the save button on the details step
is pressed on every shipment, not once — and the routes do not exist where
the history is off, like everything else an organisation keeps beyond its
accounts.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.user import User


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, username="ada", email="ada@example.com", password_hash="x", role="user"))
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def application(db, monkeypatch, history: bool) -> TestClient:
    monkeypatch.setenv("EMCARGO_HISTORY", "true" if history else "false")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, 1)
    return TestClient(app)


ENTRY = {"name": "Ontvanger GmbH", "address": "Hafenstrasse 4\n47119 Duisburg", "contact": "Herr Weber"}


def test_legacy_opt_out_keeps_address_book_available(db, monkeypatch):
    with application(db, monkeypatch, history=False) as client:
        assert client.get("/api/addresses").status_code == 200
        assert client.post("/api/addresses", json=ENTRY).status_code == 200


def test_add_list_search_change_and_remove(db, monkeypatch):
    with application(db, monkeypatch, history=True) as client:
        created = client.post("/api/addresses", json=ENTRY)
        assert created.status_code == 200, created.text
        entry = created.json()
        assert entry["name"] == "Ontvanger GmbH"
        client.post("/api/addresses", json={"name": "Afzender BV", "address": "Havenweg 1", "contact": ""})

        listed = client.get("/api/addresses").json()
        assert [e["name"] for e in listed] == ["Afzender BV", "Ontvanger GmbH"]
        assert [e["name"] for e in client.get("/api/addresses?q=duisburg").json()] == ["Ontvanger GmbH"]
        assert [e["name"] for e in client.get("/api/addresses?q=weber").json()] == ["Ontvanger GmbH"]

        changed = client.put(f"/api/addresses/{entry['id']}", json={**ENTRY, "contact": "Frau Weber"})
        assert changed.json()["contact"] == "Frau Weber"

        assert client.delete(f"/api/addresses/{entry['id']}").json()["ok"] is True
        assert client.delete(f"/api/addresses/{entry['id']}").status_code == 404
        assert [e["name"] for e in client.get("/api/addresses").json()] == ["Afzender BV"]


def test_saving_the_same_party_again_updates_the_one_entry(db, monkeypatch):
    """The save button is pressed on every shipment. The book must not grow
    by one Ontvanger GmbH each time."""
    with application(db, monkeypatch, history=True) as client:
        first = client.post("/api/addresses", json=ENTRY).json()
        again = client.post("/api/addresses", json={**ENTRY, "name": "ontvanger gmbh",
                                                    "contact": "Herr Schmidt"}).json()
        assert again["id"] == first["id"]
        assert again["contact"] == "Herr Schmidt"
        assert len(client.get("/api/addresses").json()) == 1


def test_a_name_is_required_and_whitespace_is_not_a_name(db, monkeypatch):
    with application(db, monkeypatch, history=True) as client:
        assert client.post("/api/addresses", json={"name": "   "}).status_code == 422
        assert client.post("/api/addresses", json={"address": "x"}).status_code == 422
