"""Outstanding source facts and package obligations must survive final gates."""
import importlib.util
from pathlib import Path

from tests.test_dg_review_permissions import setup, shipment  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("sbom_check", ROOT / "scripts/check_sbom.py")
sbom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbom)


def test_unknown_package_cannot_be_published():
    assert sbom.validate({"bomFormat": "CycloneDX", "components": [{"name": "unreviewed", "purl": "pkg:pypi/example@1"}]},
                         {"approvals": []}, "image")


def test_empty_sbom_is_not_a_clean_distribution():
    assert sbom.validate({"bomFormat": "CycloneDX", "components": []}, {"approvals": []}, "native")


def test_approval_does_not_cover_a_new_version_or_changed_license(tmp_path):
    (tmp_path / "review.md").write_text("Original test grant")
    licenses = [{"expression": "MIT"}]
    policy = {"approvals": [{"purl": "pkg:pypi/example@1", "channels": ["image"], "detected_licenses": licenses,
                             "evidence": "review.md", "reviewer": "Test author", "obligations": "Preserve notice"}]}
    component = {"name": "example", "purl": "pkg:pypi/example@1", "licenses": licenses}
    bom = {"bomFormat": "CycloneDX", "components": [component]}
    assert sbom.validate(bom, policy, "image", tmp_path) == []
    component["licenses"] = [{"expression": "AGPL-3.0-only"}]
    assert sbom.validate(bom, policy, "image", tmp_path)
    component["licenses"] = licenses
    component["purl"] = "pkg:pypi/example@2"
    assert sbom.validate(bom, policy, "image", tmp_path)


def test_specialist_cannot_approve_missing_imdg_source_assessment(setup):
    # Pending reviews from earlier releases must also pass the new server gate.
    import json
    from app.models.dg_review import DgReview
    db, as_role = setup
    payload = shipment()
    payload["profiles"] = ["IMDG"]
    payload["modality"] = "sea"
    payload["dangerous_goods"] = [{"line_id": 1, "products": [{"un_number": "1203", "packing_group": "II"}]}]
    review_id = "legacy-unverified-imdg"
    db.add(DgReview(id=review_id, fingerprint="legacy", created_by_id=1, created_by="user",
                    modality="sea", payload_json=json.dumps(payload), status="pending"))
    db.commit()
    decision = as_role("dg_specialist").post(f"/api/dg-reviews/{review_id}/decision", json={"status": "approved"})
    assert decision.status_code == 409
    assert decision.json()["detail"]["code"] == "imdg.source_verification_required"
    assert db.get(DgReview, review_id).status == "pending"


def test_source_check_cannot_be_bypassed_by_switching_off_specialist_review(setup):
    from app.services import settings_store
    from app.schemas.settings import InstanceSettings
    db, as_role = setup
    settings_store.save_instance_settings(db, InstanceSettings(dg_review_enabled=False))
    payload = shipment()["bundle"]["documents"][0]
    payload["profiles"] = ["IMDG"]
    response = as_role("user").post("/api/documents/export", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "imdg.source_verification_required"
