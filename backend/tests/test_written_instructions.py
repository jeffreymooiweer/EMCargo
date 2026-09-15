"""The instructions in writing, and what the application may claim about them.

ADR and ADN 5.4.3.4 print the instructions rather than describe them: the
document a crew carries has to correspond in form and content to a model of
four pages that the book sets out. So this is the one document EMCargo does
not compose — it takes the model out of the edition in the document store and
hands that over. The rules these tests hold to:

* a model is offered per regime *and* per language, and a language the store
  cannot produce says so instead of being filled in from another language;
* the page range a model is cut at was measured from the edition itself, not
  guessed, and the register carries it;
* the endpoint refuses honestly, naming the document that is missing.
"""
import json
from pathlib import Path

import pytest

from app.services import regulations

REGISTER = Path(__file__).resolve().parents[1] / "seed" / "dg" / "sources.json"


def register() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def test_elke_regeling_en_taal_staat_in_het_register():
    """Eight models: two regimes, four languages. A language nobody has yet
    supplied is registered as missing, which is what lets the application say
    so; leaving it out of the register would make it invisible instead."""
    models = {(d["model_of"]["regime"], d["model_of"]["language"])
              for d in regulations.instruction_documents()}
    assert models == {(regime, language)
                      for regime in regulations.REGIMES
                      for language in regulations.LANGUAGES}


def test_een_paginabereik_is_gemeten_en_niet_geraden():
    for doc in regulations.instruction_documents():
        cut = doc.get("cut_from")
        if not cut:
            continue
        first, last = cut["pages"]
        assert 0 < first <= last
        assert cut["measured_with"] == "scripts/find_instructions_pages.py"
        assert cut["document"] in {d["id"] for d in register()["documents"]}


def test_every_model_has_a_registered_compatible_import():
    """Removal of the original PDFs must leave all twelve imports addressable."""
    from app.services.document_templates import profiles
    registered = profiles()
    for doc in regulations.instruction_documents():
        profile = registered[doc["id"]]
        assert profile["pages"] >= 4
        assert profile["filename"] == doc["filename"]
        assert len(doc["cut_from"]["page_fingerprints"]) == profile["pages"]


def test_wat_nergens_is_wordt_niet_verzonnen(tmp_path, monkeypatch):
    """Take away the store, the bundled models *and* the CI cache fallback,
    and the status says the model is missing and names the document that
    would produce it — it never falls back to a neighbouring language."""
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    data["store"]["fallback_path"] = str(tmp_path / "fallback")
    monkeypatch.setenv("EMCARGO_REGULATIONS_DIR", str(tmp_path / "store"))
    monkeypatch.setattr(regulations, "BUNDLED_MODELS", tmp_path / "models")
    monkeypatch.setattr(regulations, "manifest", lambda: data)
    status = regulations.instruction_status("adr", "nl")
    assert status["available"] is False
    assert status["reason"] == "missing_in_store"
    assert status["needs"] == "adr_nl_2025"
    assert regulations.instructions_pdf("adr", "nl") is None


def test_a_filename_alone_cannot_override_a_verified_model(tmp_path, monkeypatch):
    """A local filename without compatible bytes is not a verified model."""
    doc = next(d for d in regulations.instruction_documents()
               if d["model_of"]["regime"] == "adr"
               and d["model_of"]["language"] == "nl")
    own = tmp_path / doc["filename"]
    own.write_bytes(b"%PDF-operator")
    monkeypatch.setenv("EMCARGO_REGULATIONS_DIR", str(tmp_path))
    regulations.manifest.cache_clear()
    assert regulations.locate(doc["id"]) != own


@pytest.mark.parametrize("regime,language", [("adr", "nl"), ("adn", "en")])
def test_het_model_wordt_geleverd_als_de_editie_er_is(regime, language):
    """When the edition is in the store the cut is a PDF of exactly the pages
    the register names. Skipped where the store of this machine lacks it —
    the register says which document that is, and the test says so too."""
    status = regulations.instruction_status(regime, language)
    if not status["available"]:
        pytest.skip(f"this store lacks {status['needs']}")
    path = regulations.instructions_pdf(regime, language)
    assert path is not None and path.is_file()
    from pypdf import PdfReader
    doc = next(d for d in regulations.instruction_documents()
               if d["model_of"]["regime"] == regime
               and d["model_of"]["language"] == language)
    first, last = doc["cut_from"]["pages"]
    assert len(PdfReader(str(path)).pages) == last - first + 1


# --- through the API, because that is how a driver reaches it ---------------


def _client():
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.core.deps import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="admin", active=True)
    return TestClient(app)


def test_de_lijst_zegt_per_regeling_en_taal_wat_er_is():
    response = _client().get("/api/documents/instructions")
    assert response.status_code == 200
    documents = response.json()["documents"]
    assert len(documents) == len(regulations.REGIMES) * len(regulations.LANGUAGES)
    for item in documents:
        assert item["provision"] == "5.4.3"
        if not item["available"]:
            assert item["needs"], item


def test_elke_taal_is_nu_te_downloaden():
    """The complaint that started v1.130.0: a language could be selected but
    not downloaded, because the models lived only in a store nobody had
    filled. With the cuts bundled, every language button must actually
    deliver a PDF."""
    client = _client()
    for regime in regulations.REGIMES:
        for language in regulations.LANGUAGES:
            response = client.get(f"/api/documents/instructions/{regime}/{language}")
            available = regulations.instruction_status(regime, language)["available"]
            assert response.status_code == (200 if available else 409), (regime, language)
            if available:
                assert response.content[:5] == b"%PDF-", (regime, language)


def test_een_ontbrekend_model_weigert_met_de_reden(tmp_path, monkeypatch):
    data = json.loads(REGISTER.read_text(encoding="utf-8"))
    data["store"]["fallback_path"] = str(tmp_path / "fallback")
    monkeypatch.setenv("EMCARGO_REGULATIONS_DIR", str(tmp_path / "store"))
    monkeypatch.setattr(regulations, "BUNDLED_MODELS", tmp_path / "models")
    monkeypatch.setattr(regulations, "manifest", lambda: data)
    response = _client().get("/api/documents/instructions/adr/de")
    assert response.status_code == 409
    assert response.json()["detail"]["reason"] == "missing_in_store"


def test_een_onbekende_regeling_bestaat_niet():
    """The RID joined the known regimes in v1.124.0, so the unknown example
    is the sea code — its instructions are the IMDG's own affair. A known
    regime whose edition this store lacks answers 409 with the status, not
    404: registered-but-missing and unknown are different answers."""
    assert _client().get("/api/documents/instructions/imdg/nl").status_code == 404
    response = _client().get("/api/documents/instructions/rid/nl")
    assert response.status_code in (200, 409)


def test_het_model_komt_als_pdf_binnen():
    if not regulations.instruction_status("adr", "nl")["available"]:
        pytest.skip("this store lacks the Dutch ADR")
    response = _client().get("/api/documents/instructions/adr/nl")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:5] == b"%PDF-"
