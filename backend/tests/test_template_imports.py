"""Synthetic originals exercise imports without redistributing publisher PDFs.

An incorrect field mapping, partial local template directory, or missing
original must not produce a convincing but incorrect transport document.
"""
import hashlib
import io
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas

from app.core.messages import ApiError
from app.services import document_templates as templates
from app.services.documents.pdf_forms import _fill_with_pypdf
from app.services.pdf_pages import file_sha256, page_fingerprint, verified_model_writer
from tests.test_dg_review_permissions import setup  # noqa: F401


def original(labels, field=False):
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=(595, 842))
    for label in labels:
        canvas.drawString(30, 780, label)
        if field:
            canvas.acroForm.textfield(name="consignor", x=30, y=700, width=400, height=40,
                                     value="Original default", fontSize=12)
        canvas.showPage()
    canvas.save()
    return buffer.getvalue()


@pytest.fixture
def local_templates(tmp_path, monkeypatch):
    content = original(["SYNTHETIC TEST FORM"], field=True)
    profile = {"id": "cmr", "name": "Original test", "kind": "form", "filename": "cmr.pdf",
               "sha256": hashlib.sha256(content).hexdigest(), "pages": 1,
               "media_boxes": [[0.0, 0.0, 595.0, 842.0]], "fields": ["consignor"]}
    monkeypatch.setattr(templates, "profiles", lambda: {"cmr": profile, "cim": {**profile, "id": "cim", "filename": "cim.pdf"}})
    monkeypatch.setattr(templates, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path / "data"))
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(templates, "BUNDLED_FORMS", tmp_path / "bundle")
    return content, tmp_path


def test_invalid_import_preserves_current_original(local_templates):
    content, root = local_templates
    templates.install("cmr", content, source="Test author", rights_basis="Original test", actor="admin")
    before = templates.resolve("cmr").read_bytes()
    with pytest.raises(ApiError, match="supported edition"):
        templates.install("cmr", original(["WRONG EDITION"]), source="Test", rights_basis="Test", actor="admin")
    assert templates.resolve("cmr").read_bytes() == before
    assert len(list((root / "data/document-templates/cmr").glob("*.pdf"))) == 1


def test_a_partial_local_directory_does_not_hide_another_compatible_form(local_templates):
    content, root = local_templates
    (root / "data/templates/forms").mkdir(parents=True)
    (root / "data/templates/forms/cmr.pdf").write_bytes(content)
    (root / "bundle").mkdir()
    (root / "bundle/cim.pdf").write_bytes(content)
    assert templates.resolve("cmr") == root / "data/templates/forms/cmr.pdf"
    assert templates.resolve("cim") == root / "bundle/cim.pdf"


def test_template_upload_is_admin_only_and_records_source(setup, local_templates):
    _, as_role = setup
    content, root = local_templates
    for role in ("user", "super_user", "dg_specialist"):
        assert as_role(role).post("/api/settings/document-templates/cmr", files={"file": ("test.pdf", content)},
                                 data={"source": "Test", "rights_basis": "Original test"}).status_code == 403
    response = as_role("admin").post("/api/settings/document-templates/cmr", files={"file": ("test.pdf", content)},
                                      data={"source": "Test author, edition 1", "rights_basis": "Original test"})
    assert response.status_code == 200, response.text
    assert templates.resolve("cmr")
    assert as_role("admin").get("/api/settings/document-templates/cmr/preview").content == content


def test_missing_template_refuses_instead_of_rendering_a_substitute(local_templates):
    from app.api.routes.documents import _render_export
    from app.schemas import DocumentExportRequest
    with pytest.raises(ApiError) as caught:
        _render_export({"exporter": "pdf_template"}, DocumentExportRequest(document_key="cmr"), None)
    assert caught.value.status_code == 409
    assert caught.value.code == "templates.missing"


def test_flattening_keeps_all_pages_and_values_without_viewer_regeneration(tmp_path):
    source = tmp_path / "original.pdf"
    source.write_bytes(original(["COPY 1", "COPY 2", "COPY 3", "COPY 4"], field=True))
    result = _fill_with_pypdf(source, {"consignor": "Transport Müller 123"}, "Original test")
    try:
        reader = PdfReader(result)
        assert len(reader.pages) == 4
        for page in reader.pages:
            assert "Transport Müller 123" in page.extract_text()
            assert not any(a.get_object().get("/Subtype") == "/Widget" for a in page.get("/Annots", []))
        assert not reader.get_fields()
    finally:
        result.unlink()


def test_page_count_drift_uses_every_verified_model_page(tmp_path):
    source = tmp_path / "edition.pdf"
    source.write_bytes(original(["NEW FRONT PAGE", "ORIGINAL FRONT PAGE", "MODEL A", "MODEL B", "MODEL C", "MODEL D"]))
    reader = PdfReader(source)
    cut = {"pages": [2, 5], "fingerprint_method": "pypdf-text-and-boxes-v1",
           "page_fingerprints": [page_fingerprint(p) for p in reader.pages[2:]]}
    writer = verified_model_writer(source, cut, file_sha256(source))
    assert [page.extract_text().strip() for page in writer.pages] == ["MODEL A", "MODEL B", "MODEL C", "MODEL D"]
    cut["page_fingerprints"][-1] = "0" * 64
    with pytest.raises(ValueError, match="missing or ambiguous"):
        verified_model_writer(source, cut, file_sha256(source))
    with pytest.raises(ValueError, match="SHA-256"):
        verified_model_writer(source, cut, "0" * 64)


def test_docker_upgrade_preserves_originals_without_extracting_archive_paths(local_templates):
    import httpx
    import tarfile
    from app.update_helper import retain_templates
    content, root = local_templates
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        member = tarfile.TarInfo("../../must-not-be-extracted.pdf")
        member.size = len(content)
        tar.addfile(member, io.BytesIO(content))
    with httpx.Client(base_url="http://docker", transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=archive.getvalue()))) as client:
        retain_templates(client, "old")
    assert templates.resolve("cmr").read_bytes() == content
    assert templates.resolve("cim").read_bytes() == content
    assert not (root / "must-not-be-extracted.pdf").exists()
    receipt = (root / "data/document-templates/cmr/current.json").read_text()
    assert "installation-upgrade" in receipt
    assert "No redistribution grant inferred" in receipt


def test_docker_upgrade_refuses_a_wrong_original(local_templates):
    import httpx
    import tarfile
    from app.update_helper import retain_templates
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        member = tarfile.TarInfo("cmr.pdf"); member.size = 4
        tar.addfile(member, io.BytesIO(b"oops"))
    with httpx.Client(base_url="http://docker", transport=httpx.MockTransport(
            lambda request: httpx.Response(200, content=archive.getvalue()))) as client:
        with pytest.raises(RuntimeError, match="Could not preserve"):
            retain_templates(client, "old")
    assert templates.resolve("cmr") is None
