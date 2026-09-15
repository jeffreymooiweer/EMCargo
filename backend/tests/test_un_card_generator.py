"""A smoke pass over the UN card generator the workflow runs.

The generator lives in scripts/, outside the application, but the
application's import trusts what it produces — so the suite holds the two
ends of that contract together: filenames follow UN####_<MODALITY>.pdf, the
manifest's hashes match the files, several transport entries of one UN
number become pages of one PDF, unavailable modalities fail aloud, and the
store accepts a package the generator built.
"""
import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

pytest.importorskip("reportlab")


@pytest.fixture(scope="module")
def generator():
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "un_cards.generate", REPO / "scripts" / "un_cards" / "generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def generated(generator, tmp_path_factory):
    out = tmp_path_factory.mktemp("cards")
    report = generator.generate(["1203", "1263", "0004"],
                                ["ADR", "ADN", "IMDG", "RID", "ICAO"], out)
    manifest = generator.build_manifest(out, report)
    return out, report, manifest


def test_filenames_follow_the_contract(generated):
    out, report, _ = generated
    for row in report["results"]:
        if row["status"] != "generated":
            continue
        expected = f"{row['modality']}/UN{row['un_number']}_{row['modality']}.pdf"
        assert row["file"] == expected
        assert (out / expected).is_file()


def test_unavailable_modalities_fail_aloud(generated):
    """Air is the one modality without a measured table since the RID's
    joined in v1.132.0; it still fails by name, never by silence."""
    _, report, _ = generated
    failed = {(r["un_number"], r["modality"])
              for r in report["results"] if r["status"] == "failed"}
    assert ("1203", "ICAO") in failed
    assert ("1203", "RID") not in failed
    reasons = [r["reason"] for r in report["results"] if r["status"] == "failed"]
    assert all(reason for reason in reasons)


def test_the_rid_card_carries_the_rails_own_columns(generator):
    """UN 1547 (aniline, the rail test substance since v1.122.0): transport
    category, hazard number, RID tank code and the CW/CE provisions come
    from the three-reading table, and no shunting model is claimed where
    column (5) brackets none."""
    from un_cards.sources import rid
    page = rid.cards("1547")[0]
    identity = dict(page.identity_extra)
    assert identity["Transport category"] == "2"
    assert identity["Hazard identification number"] == "60"
    rows = dict(page.provision_rows)
    assert rows["Loading, unloading and handling"].startswith("CW13 CW28 CW31")
    assert rows["Express parcels"].startswith("CE5")
    assert dict(page.tank_rows)["RID tank code (4.3)"] == "L4BH"
    assert "None assigned" in dict(page.label_extra)["Shunting labels (5.3.4)"]


def test_the_rid_card_prints_the_shunting_model(generator):
    from un_cards.sources import rid
    page = rid.cards("0004")[0]
    shunting = dict(page.label_extra)["Shunting labels (5.3.4)"]
    assert "13" in shunting and "5.3.4" in shunting


def test_a_released_entry_says_so_instead_of_borrowing(generator):
    """UN 1845 (dry ice) is NOT SUBJECT TO RID: its card says exactly that
    and carries no coded columns pretending otherwise."""
    from un_cards.sources import rid
    page = rid.cards("1845")[0]
    assert "NOT SUBJECT TO RID" in dict(page.identity_extra)["Rail status"]
    assert page.labels == []


def test_multiple_entries_become_pages_of_one_pdf(generated):
    """UN 1263 (PAINT) has packing groups I-III in table A: one file, several
    pages — never a silent pick of the first row."""
    _, report, _ = generated
    row = next(r for r in report["results"]
               if r["un_number"] == "1263" and r["modality"] == "ADR")
    assert row["status"] == "generated"
    assert row["pages"] >= 3


def test_the_manifest_matches_the_files(generated):
    import hashlib
    out, _, manifest = generated
    assert manifest["schema_version"] == 1
    assert manifest["total_cards"] > 0
    assert manifest["editions"]["ADR"] == "ADR 2025"
    for card in manifest["cards"]:
        content = (out / card["file"]).read_bytes()
        assert content.startswith(b"%PDF")
        assert hashlib.sha256(content).hexdigest() == card["sha256"]
        assert len(content) == card["size"]


def test_the_store_accepts_what_the_generator_packages(generated, generator,
                                                       tmp_path, monkeypatch):
    from app.core.config import get_settings
    out, _, manifest = generated
    package = tmp_path / "emcargo-un-cards.zip"
    generator.build_zip(out, manifest, package)

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    try:
        from app.services.documents import un_card_store
        result = un_card_store.import_package(package)
        assert result["imported"] == manifest["total_cards"]
        for filename in ("CalSans-LICENSE.txt", "DejaVu-LICENSE.txt"):
            assert (un_card_store.store_dir() / "licenses" / filename).read_bytes() == (
                REPO / "backend/app/assets/fonts" / filename).read_bytes()
        assert (un_card_store.store_dir() / "THIRD_PARTY_NOTICES.md").is_file()
        assert un_card_store.card_path("1203", "ADR") is not None
        assert un_card_store.card_path("1203", "RID") is not None
        assert un_card_store.card_path("1203", "ICAO") is None
    finally:
        get_settings.cache_clear()


def test_the_imdg_card_prints_the_code_descriptions(generator):
    """Column 16a/16b codes appear with the verbatim descriptions of IMDG
    7.1.5/7.1.6/7.2.8 from the measured imdg_codes.json seed — a code the
    seed lacks keeps its chapter reference, and nothing is paraphrased."""
    from un_cards.sources import imdg
    page = imdg.cards("1017")[0]
    rows = dict(page.provision_rows)
    assert "Clear of living quarters." in rows["Stowage and handling"]
    assert "Category D — see IMDG 7.1.3.2" in rows["Stowage and handling"]
    assert "Segregation as for class 5.1." in rows["Segregation"]


def test_the_adn_card_is_honest_without_its_texts_seed(generator, monkeypatch):
    """Until the extraction workflow commits adn_provision_texts.json, the
    7.1.6 codes stay code-plus-reference — never a written summary."""
    from un_cards.sources import adn
    monkeypatch.setattr(adn, "_provision_texts", lambda: {})
    page = adn.cards("1203")[0]
    rows = dict(page.provision_rows)
    assert rows["Ventilation"].startswith("VE01 — ")
    assert "see ADN 7.1.6" in rows["Ventilation"]


def test_the_adn_card_prints_texts_once_the_seed_exists(generator, monkeypatch):
    from un_cards.sources import adn
    monkeypatch.setattr(
        adn, "_provision_texts",
        lambda: {"VE": {"VE01": "Holds shall be ventilated."}})
    page = adn.cards("1203")[0]
    assert dict(page.provision_rows)["Ventilation"] == (
        "VE01 — Holds shall be ventilated.")


def test_the_cards_carry_no_third_party_branding(generated):
    fitz = pytest.importorskip("fitz")
    out, _, manifest = generated
    for card in manifest["cards"][:6]:
        with fitz.open(str(out / card["file"])) as doc:
            text = "".join(page.get_text() for page in doc)
        assert "Generated by EMCargo" in text
        assert "Cantell" not in text
        assert f"UN {card['un_number']}" in text or card["un_number"] in text


def test_partial_generation_cannot_pass_the_publication_gate(generator, monkeypatch, tmp_path):
    """One successful PDF used to hide failures for other requested cards.
    The workflow must stop before publishing such a partial package."""
    monkeypatch.setattr(sys, "argv", ["generate.py", "--scope", "all", "--out", str(tmp_path)])
    monkeypatch.setattr(generator, "generate", lambda *args: {
        "summary": {"generated": 1, "failed": 1, "not_applicable": 0},
        "not_applicable": {},
        "results": [{"status": "failed", "un_number": "1203", "modality": "ADR",
                     "reason": "source entry unavailable"}],
    })
    assert generator.main() == 1


def test_explicitly_unavailable_modality_does_not_block_measured_cards(generator, monkeypatch, tmp_path):
    """All mode explicitly reports the missing air source; it must still
    allow the complete set for the modalities with measured tables."""
    monkeypatch.setattr(sys, "argv", ["generate.py", "--scope", "all", "--out", str(tmp_path)])
    monkeypatch.setattr(generator, "generate", lambda *args: {
        "summary": {"generated": 1, "failed": 0, "not_applicable": 1},
        "not_applicable": {"ICAO": "no measured air source"}, "results": [],
    })
    assert generator.main() == 0
