"""Role and release regressions for the specialist workflow.

A disabled button is not a shipment release policy. These tests exercise the
actual HTTP export, mail, persistence and report routes, including edited
payloads and account takeover attempts by an operational manager.
"""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.user import User
from app.models.dg_review import DgReview
from app.schemas.settings import InstanceSettings
from app.services import settings_store
from tests.test_export_bundle import CONSIGNMENT, DG, LINES


@pytest.fixture
def setup(synthetic_templates):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    people = {}
    for index, role in enumerate(["user", "super_user", "dg_specialist", "admin"], 1):
        user = User(id=index, username=role, email=f"{role}@example.com", password_hash="unused", role=role, active=True)
        db.add(user); people[role] = user
    db.commit()
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    current = [people["user"]]
    app.dependency_overrides[get_current_user] = lambda: current[0]
    client = TestClient(app)
    def as_role(role):
        current[0] = people[role]
        return client
    yield db, as_role
    client.close(); db.close(); engine.dispose()


def shipment():
    document = {"document_key": "cmr", "values": deepcopy(CONSIGNMENT), "lines": deepcopy(LINES),
                "dangerous_goods": deepcopy(DG), "profiles": ["ADR"], "modality": "road", "output_language": "nl"}
    return {"modality": "road", "language": "nl", "profiles": ["ADR"], "values": deepcopy(CONSIGNMENT),
            "lines": deepcopy(LINES), "dangerous_goods": deepcopy(DG), "documents": ["cmr"],
            "bundle": {"documents": [document], "dangerous_goods": deepcopy(DG), "profiles": ["ADR"], "output_language": "nl"},
            "snapshot": {"version": 1, "stepKey": "export", "docValues": deepcopy(CONSIGNMENT)}}


def release(as_role, payload):
    response = as_role("user").post("/api/dg-reviews", json=payload)
    assert response.status_code == 200, response.text
    review_id = response.json()["id"]
    response = as_role("dg_specialist").post(f"/api/dg-reviews/{review_id}/decision", json={"status": "approved"})
    assert response.status_code == 200, response.text
    payload["dg_review_id"] = review_id
    payload["bundle"]["dg_review_id"] = review_id
    payload["bundle"]["documents"][0]["dg_review_id"] = review_id
    return review_id


def test_defaults_and_review_storage_are_independent_of_history(setup):
    db, as_role = setup
    settings = as_role("user").get("/api/settings/public").json()
    assert settings["dg_review_enabled"] is True
    assert settings["super_user_dgsa_enabled"] is False
    assert settings["history_enabled"] is False
    payload = shipment()
    review_id = release(as_role, payload)
    assert db.get(DgReview, review_id).status == "approved"
    assert settings_store.history_enabled(db) is False
    # Reloads recover an approval by the actual inputs, not a browser token.
    assert as_role("user").post("/api/dg-reviews/status", json=payload).json()["status"] == "approved"
    payload["values"]["reference"] = "changed"
    assert as_role("user").post("/api/dg-reviews/status", json=payload).json() is None


def test_preparation_exports_are_stamped_without_execution_approval(setup):
    """Saving source goods or printing a concept grants no permission to execute.

    The delivery API now owns final issue. Old shipment/export endpoints must
    remain useful for preparation, and must visibly mark every PDF as a draft,
    even after an old specialist review is deleted or the source is edited.
    """
    import io
    import zipfile
    from pypdf import PdfReader
    db, as_role = setup
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True))
    payload = shipment()
    client = as_role("user")
    document = client.post("/api/documents/export", json=payload["bundle"]["documents"][0])
    assert document.status_code == 200, document.text
    assert "DRAFT" in "".join(page.extract_text() for page in PdfReader(io.BytesIO(document.content)).pages)
    assert "DRAFT-" in document.headers["content-disposition"]
    bundle = client.post("/api/documents/export/bundle", json=payload["bundle"])
    assert bundle.status_code == 200
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as archive:
        papers = [name for name in archive.namelist() if name.startswith("DRAFT-") and name.endswith(".pdf")]
        assert papers
        for name in papers:
            assert "DRAFT" in "".join(page.extract_text() for page in PdfReader(io.BytesIO(archive.read(name))).pages)
    kept = client.post("/api/shipments", json=payload)
    assert kept.status_code == 200, kept.text
    shipment_id = kept.json()["id"]
    assert client.get(f"/api/shipments/{shipment_id}/export.json").status_code == 200
    review_id = release(as_role, payload)
    client = as_role("user")
    assert client.delete(f"/api/dg-reviews/{review_id}").status_code == 200
    assert client.post(f"/api/shipments/{shipment_id}/documents").status_code == 200
    assert client.get(f"/api/shipments/{shipment_id}/export.json").status_code == 200


def test_no_dg_and_policy_off_do_not_require_release(setup):
    db, as_role = setup; client = as_role("user")
    plain = shipment()["bundle"]["documents"][0]; plain.pop("dangerous_goods")
    assert client.post("/api/documents/export", json=plain).status_code == 200
    settings_store.save_instance_settings(db, InstanceSettings(dg_review_enabled=False))
    assert client.post("/api/documents/export", json=shipment()["bundle"]["documents"][0]).status_code == 200


def test_sea_preparation_requires_source_verification_and_stays_a_draft(setup):
    """Verified sea source facts permit drafts, without implying execution release."""
    _, as_role = setup
    payload = shipment()
    payload.update(modality="sea", profiles=["IMDG"], documents=["imo_dgd"])
    values = payload["values"]
    values.update(container_number="MSKU 123456-7", declarant_name="Test consignor",
                  declaration_place="Rotterdam", declaration_date="2026-09-15")
    products = payload["dangerous_goods"]
    products[0]["products"][0].update(
        marine_pollutant="N", imdg_source_reviewed="Y",
        imdg_source_reference="Synthetic test SDS section 14, 2026-09-15")
    document = payload["bundle"]["documents"][0]
    document.update(document_key="imo_dgd", modality="sea", profiles=["IMDG"],
                    values=deepcopy(values), dangerous_goods=deepcopy(products))
    payload["bundle"].update(profiles=["IMDG"], dangerous_goods=deepcopy(products))
    payload["snapshot"]["docValues"] = deepcopy(values)

    client = as_role("user")
    assert client.post("/api/documents/export", json=document).status_code == 200
    assert client.post("/api/documents/export/bundle", json=payload["bundle"]).status_code == 200
    release(as_role, payload)
    client = as_role("user")
    response = client.post("/api/documents/export", json=document)
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"%PDF-")
    response = client.post("/api/documents/export/bundle", json=payload["bundle"])
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"PK")
    document["lines"][0]["weight_total_kg"] = 900
    assert client.post("/api/documents/export", json=document).status_code == 200
    assert client.post("/api/documents/export/bundle", json=payload["bundle"]).status_code == 200

    unverified = deepcopy(document)
    unverified["dangerous_goods"][0]["products"][0]["imdg_source_reviewed"] = "N"
    response = client.post("/api/documents/export", json=unverified)
    assert response.status_code in {409, 422}, response.text

def test_only_specialists_decide_and_rejection_requires_explanation(setup):
    _, as_role = setup
    payload = shipment(); response = as_role("user").post("/api/dg-reviews", json=payload)
    review_id = response.json()["id"]
    path = f"/api/dg-reviews/{review_id}/decision"
    for role in ["user", "super_user", "admin"]:
        assert as_role(role).post(path, json={"status": "approved"}).status_code == 403
    client = as_role("dg_specialist")
    assert client.post(path, json={"status": "changes_requested", "comment": "  "}).status_code == 422
    assert client.post(path, json={"status": "changes_requested", "comment": "Verify packaging"}).status_code == 200
    assert client.post(path, json={"status": "approved"}).status_code == 409
    revised = as_role("user").post("/api/dg-reviews", json=payload)
    assert revised.status_code == 200 and revised.json()["id"] != review_id


def test_super_user_cannot_escalate_or_take_over_privileged_accounts(setup):
    _, as_role = setup; client = as_role("super_user")
    assert client.get("/api/users").status_code == 200
    for role in ["admin", "dg_specialist"]:
        assert client.post("/api/users", json={"username": f"new_{role}", "email": f"new_{role}@example.com", "password": "strong-password", "role": role}).status_code == 403
        assert client.patch("/api/users/2", json={"role": role}).status_code == 403
    for target in [3, 4]:
        for change in [{"role": "user"}, {"password": "strong-password"}, {"email": "new@example.com"}, {"active": False}, {"department_id": None}]:
            assert client.patch(f"/api/users/{target}", json=change).status_code == 403
        assert client.delete(f"/api/users/{target}/two-factor").status_code == 403
        assert client.delete(f"/api/users/{target}").status_code == 403
    assert client.patch("/api/users/1", json={"role": "super_user"}).status_code == 200
    assert client.patch("/api/users/2", json={"email": "updated@example.com"}).status_code == 200
    assert client.patch("/api/users/2", json={"role": "user"}).status_code == 400


def test_operational_settings_are_a_strict_allowlist(setup):
    db, as_role = setup; client = as_role("super_user")
    assert client.get("/api/settings/instance").status_code == 403
    assert client.put("/api/settings/instance", json={"super_user_dgsa_enabled": True}).status_code == 403
    for field, value in [("super_user_dgsa_enabled", True), ("dg_review_enabled", False), ("mail_host", "bad.example"), ("two_factor_policy", "off"), ("brand_name", "changed")]:
        assert client.put("/api/settings/organisation", json={field: value}).status_code == 422
    response = client.put("/api/settings/organisation", json={"organisation_name": "New organisation", "default_language": "de"})
    assert response.status_code == 200, response.text
    assert settings_store.instance_settings(db).organisation_name == "New organisation"
    assert settings_store.instance_settings(db).dg_review_enabled is True
    assert set(response.json()) == {"organisation_name", "organisation_address", "default_language", "default_theme"}


@pytest.mark.parametrize("path,method", [("/report/years", "get"), ("/report?year=2026", "get"), ("/report/form?year=2026", "get"), ("/report/answers?year=2026", "put"), ("/report.pdf?year=2026", "get"), ("/report.xlsx?year=2026", "get")])
def test_every_dgsa_route_respects_role_and_admin_opt_in(setup, path, method):
    db, as_role = setup
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True))
    for role in ["user", "super_user"]:
        response = getattr(as_role(role), method)("/api/shipments" + path, **({"json": {"answers": {}}} if method == "put" else {}))
        assert response.status_code == 403, response.text
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True, super_user_dgsa_enabled=True))
    for role in ["admin", "dg_specialist", "super_user"]:
        response = getattr(as_role(role), method)("/api/shipments" + path, **({"json": {"answers": {}}} if method == "put" else {}))
        assert response.status_code == 200, response.text[:500]
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True))
    assert getattr(as_role("super_user"), method)("/api/shipments" + path, **({"json": {"answers": {}}} if method == "put" else {})).status_code == 403


def test_queue_is_private_and_inconsistent_document_declarations_are_rejected(setup):
    _, as_role = setup
    response = as_role("user").post("/api/dg-reviews", json=shipment())
    review_id = response.json()["id"]
    assert as_role("super_user").get("/api/dg-reviews").json()["total"] == 0
    assert as_role("super_user").get(f"/api/dg-reviews/{review_id}").status_code == 404
    assert as_role("dg_specialist").get("/api/dg-reviews").json()["total"] == 1
    payload = shipment(); payload["bundle"]["documents"][0]["dangerous_goods"] = []
    assert as_role("user").post("/api/dg-reviews", json=payload).status_code == 422


def test_drafts_can_be_saved_but_do_not_bypass_dg_export_policy(setup):
    db, as_role = setup
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True))
    payload = shipment(); client = as_role("user")
    response = client.put("/api/shipments/draft", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["is_draft"] is True
    payload["draft"] = True
    payload["bundle"]["dangerous_goods"] = []
    payload["bundle"]["documents"][0]["dangerous_goods"] = []
    draft = client.post("/api/shipments", json=payload)
    assert draft.status_code == 200, draft.text
    assert client.post(f"/api/shipments/{draft.json()['id']}/documents").status_code == 409
    exported = client.get(f"/api/shipments/{draft.json()['id']}/export.json")
    assert exported.status_code == 200
    assert exported.json()["dangerous_goods"]


def test_concurrent_downloads_keep_one_shipment_for_the_review(tmp_path):
    """Two document downloads used to race their background keep requests.

    Separate database sessions are essential: a shared test session hides the
    lost-update window between creating a shipment and attaching its review.
    """
    from concurrent.futures import ThreadPoolExecutor
    from fastapi import Depends
    from app.models.shipment import Shipment
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        user = User(id=1, username="owner", email="owner@example.com", role="user", password_hash="x", active=True)
        db.add(user); db.commit()
        settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True))
        from app.services import dg_review
        from app.schemas.history import ShipmentIn
        data = shipment()
        record = dg_review.submit(db, user, ShipmentIn(**data))
        record.status = "approved"; record.reviewed_by = "specialist"; db.commit()
        data["dg_review_id"] = record.id
        data["bundle"]["dg_review_id"] = record.id
    app = create_app()
    def database():
        with sessions() as db:
            yield db
    def owner(db=Depends(get_db)):
        return db.get(User, 1)
    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = owner
    def keep(_):
        client = TestClient(app)
        try:
            result = client.post("/api/shipments", json=data)
            assert result.status_code == 200, result.text
            return result.json()["id"]
        finally:
            client.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(keep, range(2)))
    assert ids[0] == ids[1]
    with sessions() as db:
        assert db.query(Shipment).count() == 1
    engine.dispose()


@pytest.mark.parametrize("declaration", [[{}], [{"products": []}], [{"products": ["invalid"]}]])
def test_review_submission_requires_inspectable_dangerous_goods(setup, declaration):
    """A generic document alone must not admit a malformed review snapshot."""
    _, as_role = setup
    payload = shipment()
    payload["dangerous_goods"] = declaration
    payload["bundle"]["dangerous_goods"] = declaration
    payload["bundle"]["documents"][0]["dangerous_goods"] = declaration
    assert as_role("user").post("/api/dg-reviews", json=payload).status_code == 422


def test_removed_accounts_cannot_be_recreated_to_inherit_review_data(setup):
    db, as_role = setup
    review_id = as_role("user").post("/api/dg-reviews", json=shipment()).json()["id"]
    assert as_role("super_user").delete("/api/users/1").status_code == 200
    assert db.get(DgReview, review_id).created_by_id is None
    db.add(User(id=1, username="user", email="replacement@example.com", role="user", password_hash="x"))
    db.commit()
    assert as_role("user").get(f"/api/dg-reviews/{review_id}").status_code == 404
    assert as_role("admin").get(f"/api/dg-reviews/{review_id}").status_code == 200
