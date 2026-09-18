"""Stateless issuance must not weaken approval or the opt-in retention promise."""
import io
import json
import zipfile

from fastapi.testclient import TestClient
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.delivery import Delivery, DeliveryFile
from app.models.dg_review import DgReview
from app.models.shipment import Shipment
from app.models.user import User
from app.services import deliveries as d
from tests.test_deliveries import db  # noqa: F401 - shared file-backed fixture
from tests.test_export_bundle import CONSIGNMENT


def request(mode="road"):
    return {"shipment": {"values": {**CONSIGNMENT, "document_date": "2026-09-17"},
            "lines": [{"cargo_goods_id": 0, "description": "Steel", "quantity": 10, "unit": "pcs", "weight_total_kg": 100}]},
            "leg": {"id": "temporary", "mode": mode, "origin": "A", "destination": "B", "carrier": "Carrier", "planned_start": d.stamp(), "max_mass_tonnes": "30"},
            "document_keys": ["packing_list"], "language": "en"}


def client_for(db, monkeypatch, uid=1):
    monkeypatch.setenv("EMCARGO_HISTORY", "false")
    get_settings.cache_clear()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, uid)
    return TestClient(app)


def test_stateless_endpoints_retired_without_removing_retained_data(db, monkeypatch):
    """An old history-off installation must not create new transient dossiers."""
    before = {model: db.query(model).count() for model in (Shipment, Delivery, DeliveryFile, DgReview)}
    with client_for(db, monkeypatch) as client:
        for endpoint in ("assessment", "documents", "review"):
            assert client.post(f"/api/temporary-deliveries/v1/{endpoint}", json=request()).status_code == 404
        assert client.get("/api/settings/public").json()["history_enabled"] is True
    assert before == {model: db.query(model).count() for model in before}
