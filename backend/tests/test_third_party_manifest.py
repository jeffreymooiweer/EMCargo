"""Publication must not turn missing metadata into permission to distribute.

The historical repository lacked a file-level boundary between project code,
ODbL data and regulatory reproductions. These tests exercise actual packaging
failures with original synthetic content, without publishing a third-party
fixture or treating a license scanner as a legal decision maker.
"""
import hashlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rights_gate", ROOT / "scripts/check_third_party_manifest.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def inventory(tmp_path, status="documented"):
    name = "original.json"
    (tmp_path / name).write_text('{"original": true}')
    (tmp_path / "Fixture").write_text("Synthetic test grant")
    return {"schema_version": 1, "components": [{
        "id": "sample", "paths": [name], "version": "1", "source_url": "https://example.invalid",
        "copyright_holder": "Fixture author", "license_expression": "MIT", "rights_status": status,
        "redistribution_basis": "Synthetic test grant", "evidence_reference": "Fixture",
        "sha256": {name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()},
        "distribution_channels": ["source", "image"], "reviewed_at": "2026-09-15", "reviewer": "Fixture",
    }]}


def test_unregistered_asset_blocks_even_an_otherwise_valid_inventory(tmp_path):
    data = inventory(tmp_path)
    errors = gate.validate(tmp_path, data, assets={"original.json", "unreviewed.pdf"})
    assert any("Unregistered asset: unreviewed.pdf" in message for message in errors)


def test_changed_source_hash_requires_a_new_review(tmp_path):
    data = inventory(tmp_path)
    (tmp_path / "original.json").write_text('{"different": true}')
    assert any("changed content" in message for message in gate.validate(tmp_path, data, assets=set()))


def test_a_complete_unresolved_record_can_be_audited_but_cannot_be_published(tmp_path):
    data = inventory(tmp_path, "unresolved")
    assert gate.validate(tmp_path, data, assets=set()) == []
    assert any("publication blocked" in message
               for message in gate.validate(tmp_path, data, "image", assets=set()))


def test_retired_content_cannot_keep_an_active_distribution_path(tmp_path):
    assert any("retired content" in message
               for message in gate.validate(tmp_path, inventory(tmp_path, "retired"), assets=set()))


def test_documented_rights_still_require_a_recorded_grant(tmp_path):
    data = inventory(tmp_path)
    data["components"][0]["redistribution_basis"] = ""
    assert any("redistribution_basis" in message for message in gate.validate(tmp_path, data, assets=set()))


def test_removing_a_channel_does_not_bypass_publication(tmp_path):
    data = inventory(tmp_path, "unresolved")
    data["components"][0]["distribution_channels"] = []
    errors = gate.validate(tmp_path, data, "source", assets=set())
    assert any("omitted distribution channels" in e for e in errors)
    assert any("No content registered" in e for e in errors)
