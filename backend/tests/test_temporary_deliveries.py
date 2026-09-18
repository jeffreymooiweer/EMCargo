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


def test_issue_without_history_leaves_no_cargo_review_or_document_rows(db, monkeypatch):
    before = {model: db.query(model).count() for model in (Shipment, Delivery, DeliveryFile, DgReview)}
    with client_for(db, monkeypatch) as client:
        body = request()
        assert client.post("/api/temporary-deliveries/v1/assessment", json=body).status_code == 200
        issued = client.post("/api/temporary-deliveries/v1/documents", json=body)
        assert issued.status_code == 200, issued.text
        with zipfile.ZipFile(io.BytesIO(issued.content)) as archive:
            assert archive.read("packing_list.pdf").startswith(b"%PDF")
            metadata = json.loads(archive.read("delivery.json"))
            assert metadata["files"][0]["inputs"]["values"]["carrier_name"] == "Carrier"
    assert {model: db.query(model).count() for model in before} == before


def test_temporary_review_token_cannot_approve_changed_inputs_or_another_user(db, monkeypatch):
    body = request("sea")
    body["reason"] = "Checked the planned carrier and modal requirements"
    with client_for(db, monkeypatch) as client:
        assert client.post("/api/temporary-deliveries/v1/documents", json=body).status_code == 409
        reviewed = client.post("/api/temporary-deliveries/v1/review", json=body)
        assert reviewed.status_code == 200, reviewed.text
        body["review_token"] = reviewed.json()["token"]
        assert client.post("/api/temporary-deliveries/v1/documents", json=body).status_code == 200
        body["leg"]["destination"] = "Changed port"
        assert client.post("/api/temporary-deliveries/v1/documents", json=body).status_code == 409
        body["leg"]["destination"] = "B"
    with client_for(db, monkeypatch, 2) as other:
        assert other.post("/api/temporary-deliveries/v1/documents", json=body).status_code == 409


def test_stateless_validation_refuses_unknown_mass_and_fractional_pieces(db, monkeypatch):
    with client_for(db, monkeypatch) as client:
        body = request()
        body["shipment"]["lines"][0]["weight_total_kg"] = None
        assert client.post("/api/temporary-deliveries/v1/documents", json=body).status_code == 422
        body = request()
        body["shipment"]["lines"][0]["quantity"] = 0.5
        assert client.post("/api/temporary-deliveries/v1/documents", json=body).status_code == 422
