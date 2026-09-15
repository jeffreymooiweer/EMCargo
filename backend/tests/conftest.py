"""Fixtures every test gets.

The rate limits are real in the tests, deliberately — switching them off would
mean the end-to-end limit tests measure nothing. But the limiter counts against
the caller's address, and under a `TestClient` every test in the session is the
same caller, `testclient`. Left alone the counters accumulate across the whole
run, so a test that posts one message fails because eleven earlier tests in
other files posted theirs. That is not a finding about the code; it is one test
leaking into the next.

So the budget is reset before each test. Every test then starts with a full
allowance, and a test that wants to reach a limit still reaches it inside its
own body.
"""
import pytest

from app.core.ratelimit import limiter


@pytest.fixture(autouse=True)
def a_fresh_rate_limit_budget():
    limiter.reset()
    yield


@pytest.fixture
def dg_review_disabled(monkeypatch):
    """Rendering, retention and regulation fixtures opt out of the new workflow.

    They intentionally construct incomplete or synthetic shipments to test a
    specific renderer or persistence rule. Keep the release policy disabled
    in that explicit test configuration; test_dg_review_permissions exercises
    the real default-on policy across all final-output routes.
    """
    from app.services import dg_review
    original = dg_review.instance_settings
    monkeypatch.setattr(dg_review, "instance_settings", lambda db:
                        original(db).model_copy(update={"dg_review_enabled": False}))


@pytest.fixture
def synthetic_templates(tmp_path, monkeypatch):
    """Original test forms keep export/policy tests independent of publisher PDFs.

    They intentionally use plain boxes and measured field names, without an
    issuing body's artwork. Real-form layout tests can separately use local
    originals through EMCARGO_TEST_FORM_DIR; absence/import tests opt out.
    """
    import hashlib
    import io
    from reportlab.pdfgen.canvas import Canvas
    from app.services import document_templates, regulations

    # A process-local cache saves rebuilding all forms for each policy test.
    global _synthetic_originals
    if "_synthetic_originals" not in globals():
        generated = {}
        for key, profile in document_templates.profiles().items():
            buffer = io.BytesIO()
            canvas = Canvas(buffer, pagesize=(1200, 2200))
            for index in range(profile["pages"]):
                canvas.drawString(30, 2170, f"ORIGINAL EMCARGO TEST FIXTURE: {key} / {index + 1}")
                for row, name in enumerate(profile["fields"]):
                    canvas.acroForm.textfield(name=name, x=30, y=2120-row*23, width=1140,
                                             height=20, fontSize=8, value="")
                canvas.showPage()
            canvas.save()
            content = buffer.getvalue()
            generated[key] = (content, {**profile, "sha256": hashlib.sha256(content).hexdigest(),
                              "media_boxes": [[0.0, 0.0, 1200.0, 2200.0]] * profile["pages"]})
        _synthetic_originals = generated
    forms = tmp_path / "fixture-forms"; forms.mkdir()
    models = tmp_path / "fixture-models"; models.mkdir()
    for content, profile in _synthetic_originals.values():
        ((forms if profile["kind"] == "form" else models) / profile["filename"]).write_bytes(content)
    monkeypatch.setattr(document_templates, "profiles", lambda: {k: p for k, (_, p) in _synthetic_originals.items()})
    monkeypatch.setattr(document_templates, "BUNDLED_FORMS", forms)
    monkeypatch.setattr(regulations, "BUNDLED_MODELS", models)


@pytest.fixture
def official_templates(monkeypatch):
    """Optional integration evidence supplied locally, never downloaded by CI."""
    import os
    from pathlib import Path
    from app.services import document_templates
    directory = os.environ.get("EMCARGO_TEST_FORM_DIR")
    if not directory:
        pytest.skip("Layout integration requires independently obtained local originals")
    monkeypatch.setattr(document_templates, "BUNDLED_FORMS", Path(directory))
