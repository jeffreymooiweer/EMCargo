"""Read real PDF/image bytes and reject unsupported model assertions.

OCR errors and a local model's plausible guesses must stay reviewable source
data. No test uses an operational packing list or an external inference service.
"""
import io
import shutil
from copy import deepcopy

import pymupdf
import pytest
from fastapi import HTTPException
from PIL import Image
from pydantic import ValidationError
from reportlab.pdfgen.canvas import Canvas

from app.services import document_intake as intake, document_reader as reader
from tests.test_dg_review_permissions import setup  # noqa: F401


def packing_pdf():
    output = io.BytesIO()
    canvas = Canvas(output, pagesize=(595, 842))
    canvas.setFont("Helvetica", 14)
    canvas.drawString(35, 785, "PACKING LIST - TEST DATA")
    canvas.drawString(35, 748, "Reference: PL-2048")
    canvas.drawString(35, 710, "Dispatch date: 14-09-2026")
    for y, cells in [(650, ("Description", "Quantity", "Unit", "Total kg")),
                     (615, ("Boxes of bolts", "12", "boxes", "240")),
                     (580, ("Pump assemblies", "2", "pcs", "180"))]:
        for x, cell in zip((35, 285, 380, 480), cells):
            canvas.drawString(x, y, cell)
    canvas.save()
    return output.getvalue()


def raster():
    with pymupdf.open(stream=packing_pdf(), filetype="pdf") as document:
        return document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")


def test_text_pdf_preserves_table_rows_and_provides_page_evidence():
    data = packing_pdf()
    result = intake.read_document(data, "../packing.pdf", "en")
    assert result["name"] == "packing.pdf" and len(result["sha256"]) == 64
    page = result["pages"][0]
    assert page["number"] == 1 and page["method"] == "text"
    assert page["preview"].startswith("data:image/jpeg;base64,")
    row = next(line for line in page["lines"] if "Boxes of bolts" in line["text"])
    assert row["text"] == "Boxes of bolts 12 boxes 240"
    assert row["id"].startswith("p1l")


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Native OCR requires Tesseract; CI and Docker install it")
@pytest.mark.parametrize("kind", ["png", "jpeg", "scan", "mixed"])
def test_real_ocr_recovers_image_table_and_mixed_pdf_pages(kind):
    data, extension = raster(), "png"
    if kind == "jpeg":
        image = Image.open(io.BytesIO(data)).rotate(90, expand=True)
        exif = image.getexif()
        exif[274] = 6  # A phone stores pixels sideways and the intended orientation separately.
        output = io.BytesIO(); image.save(output, format="JPEG", exif=exif, quality=95)
        data, extension = output.getvalue(), "jpg"
    elif kind in {"scan", "mixed"}:
        with pymupdf.open() as document:
            if kind == "mixed":
                with pymupdf.open(stream=packing_pdf(), filetype="pdf") as original:
                    document.insert_pdf(original)
            document.new_page(width=595, height=842).insert_image(pymupdf.Rect(0, 0, 595, 842), stream=data)
            data, extension = document.tobytes(), "pdf"
    result = intake.read_document(data, f"scan.{extension}", "en")
    page = result["pages"][-1]
    assert page["method"] == "ocr"
    row = next(line for line in page["lines"] if "Boxes of bolts" in line["text"])
    assert all(value in row["text"] for value in ("12", "boxes", "240"))
    if kind == "mixed":
        assert len(result["pages"]) == 2 and result["pages"][0]["method"] == "text"


@pytest.mark.skipif(not shutil.which("tesseract"), reason="Native OCR requires Tesseract; CI and Docker install it")
def test_a_small_image_table_is_read_even_beneath_native_pdf_text():
    """An image-area threshold silently discarded tables occupying part of a page."""
    with pymupdf.open(stream=packing_pdf(), filetype="pdf") as original:
        table = original[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=pymupdf.Rect(0, 170, 595, 290)).tobytes("png")
    with pymupdf.open() as document:
        page = document.new_page(width=595, height=842)
        page.insert_text((35, 65), "Packing list from Example Factory - reference PL-2048", fontsize=14)
        page.insert_image(pymupdf.Rect(30, 280, 565, 388), stream=table)
        data = document.tobytes()
    source = intake.read_document(data, "partial-scan.pdf", "en")
    assert source["pages"][0]["method"] == "ocr"
    row = next(line for line in source["pages"][0]["lines"] if "Boxes of bolts" in line["text"])
    assert all(value in row["text"] for value in ("12", "boxes", "240"))


@pytest.mark.parametrize("kind,code", [("encrypted", "encrypted"), ("pages", "pages"), ("invalid", "invalid")])
def test_unreadable_or_oversized_documents_fail_explicitly(kind, code):
    data = b"not a PDF"
    if kind != "invalid":
        with pymupdf.open(stream=packing_pdf(), filetype="pdf") as document:
            if kind == "pages":
                for _ in range(10):
                    document.new_page()
                data = document.tobytes()
            else:
                data = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="reader")
    with pytest.raises(HTTPException) as caught:
        intake.read_document(data, "packing.pdf", "nl")
    assert caught.value.detail["code"] == f"intake.{code}"


def test_reader_limits_and_missing_ocr_do_not_silently_drop_text(monkeypatch, tmp_path):
    monkeypatch.setattr(reader.shutil, "which", lambda name: None)
    with pytest.raises(reader.ReadError, match="ocr_missing"):
        reader._ocr(b"bytes", "nl")
    source = tmp_path / "source.pdf"; source.write_bytes(packing_pdf())
    monkeypatch.setattr(reader, "MAX_TEXT", 15)
    with pytest.raises(reader.ReadError, match="text_large"):
        reader.read(str(source), "pdf", "en")
    with pytest.raises(HTTPException) as caught:
        intake.read_document(b"data", "file.svg", "en")
    assert caught.value.status_code == 415
    monkeypatch.setattr(intake, "MAX_BYTES", 3)
    with pytest.raises(HTTPException) as caught:
        intake.read_document(b"data", "file.pdf", "en")
    assert caught.value.status_code == 413


def proposed(monkeypatch, lines, result):
    monkeypatch.setattr(intake.runtime, "installed", lambda: True)
    monkeypatch.setattr(intake.runtime, "extract_json", lambda *args, **kwargs: deepcopy(result))
    return intake.propose(intake.ProposalRequest(lines=[{"id": f"p1l{i+1}", "text": value} for i, value in enumerate(lines)]))


def test_proposal_preserves_only_cited_facts_and_never_guesses_a_weight_basis(monkeypatch):
    result = proposed(monkeypatch, ["Description Qty Unit Total kg", "Boxes of bolts 12 boxes 240 kg total", "Invoice date: 14-09-2026"], {
        "goods": [{"description": "Boxes of bolts", "quantity": "12 boxes", "unit": "boxes", "weight": "240 kg total", "weight_unit": "kg",
                   "weight_basis": "total", "dimensions": "120x80x100 cm", "source_ids": ["p1l1", "p1l2"]},
                  {"description": "Invented goods", "quantity": "30", "unit": "pcs", "source_ids": ["p1l2"]}],
        "fields": [{"key": "loading_date", "value": "14-09-2026", "source_ids": ["p1l3"]},
                   {"key": "consignee_name", "value": "Made-up Company", "source_ids": ["p1l2"]},
                   {"key": "signature", "value": "approved", "source_ids": ["p1l2"]}]
    })
    assert len(result["goods"]) == 1 and result["fields"] == []
    row = result["goods"][0]
    assert row["quantity"] == 12 and row["unit"] == "box" and row["weight_kg"] == 240
    assert row["weight_basis"] == "unknown" and row["dimensions_cm"] is None
    assert result["warnings"] == ["unsupported_value"]


def test_missing_units_quantities_and_invalid_citations_remain_unresolved(monkeypatch):
    result = proposed(monkeypatch, ["Pump assemblies", "Mass 2,5 t", "Dispatch date: 14-09-2026"], {
        "goods": [{"description": "Pump assemblies", "quantity": "", "unit": "", "weight": "2,5", "weight_unit": "t", "source_ids": ["p1l1", "p1l2"]},
                  {"description": "Pump assemblies", "source_ids": ["p9l9"]}],
        "fields": [{"key": "loading_date", "value": "14-09-2026", "source_ids": ["p1l3"]}]
    })
    assert result["goods"][0]["quantity"] is None and result["goods"][0]["unit"] == ""
    assert result["goods"][0]["weight_kg"] == 2500
    assert result["fields"][0]["value"] == "2026-09-14"


def test_model_failure_and_request_bounds_are_explicit(monkeypatch):
    monkeypatch.setattr(intake.runtime, "installed", lambda: False)
    payload = intake.ProposalRequest(lines=[{"id": "p1l1", "text": "Boxes"}])
    with pytest.raises(HTTPException) as caught:
        intake.propose(payload)
    assert caught.value.detail["code"] == "assistant.model_required"
    monkeypatch.setattr(intake.runtime, "installed", lambda: True)
    monkeypatch.setattr(intake.runtime, "extract_json", lambda *args, **kwargs: None)
    with pytest.raises(HTTPException) as caught:
        intake.propose(payload)
    assert caught.value.detail["code"] == "intake.model_failed"
    with pytest.raises(ValidationError):
        intake.ProposalRequest(lines=[{"id": "p1l1", "text": "x"}, {"id": "p1l1", "text": "y"}])
    with pytest.raises(ValidationError):
        intake.ProposalRequest(lines=[{"id": f"p1l{i}", "text": "x" * 3000} for i in (1, 2)])


def test_authenticated_read_route_uses_installed_model_gate_and_actual_reader(setup, monkeypatch):
    _, as_role = setup
    client = as_role("user")
    monkeypatch.setattr(intake.runtime, "installed", lambda: False)
    assert client.post("/api/assistant/documents/read", files={"file": ("packing.pdf", packing_pdf(), "application/pdf")}).status_code == 409
    monkeypatch.setattr(intake.runtime, "installed", lambda: True)
    response = client.post("/api/assistant/documents/read?language=en", files={"file": ("packing.pdf", packing_pdf(), "application/pdf")})
    assert response.status_code == 200, response.text
    assert response.json()["pages"][0]["method"] == "text"


def test_accepted_document_mass_and_evidence_survive_assistant_round_trip(setup):
    """A total from the source must stay a total after a missing count is answered."""
    from app.services.assistant.orchestrator import step
    db, _ = setup
    evidence = [{"name": "packing.pdf", "sha256": "a" * 64, "pages": [1], "excerpt": "Boxes of bolts 240 kg",
                 "method": "text", "target": "goods:1", "value": "Boxes of bolts · 240 kg (total)"}]
    state = {"modality": "road", "doc_values": {}, "dg_entries": [], "document_evidence": evidence,
             "draft_lines": [{"id": 1, "description": "Boxes of bolts", "unit": "box", "quantity_unconfirmed": True,
                              "weight_basis": "total", "stated_weight_kg": 240}]}
    result = step(state, "", None, db, "en", "add_goods")
    assert result["pending"]["scope"] == "goods_quantity"
    answered = step(result["state"], "12", result["pending"], db, "en")
    line = answered["state"]["draft_lines"][0]
    assert line["quantity"] == 12 and line["weight_each_kg"] == 20 and line["weight_total_kg"] == 240
    assert answered["state"]["document_evidence"] == evidence


def test_failed_document_requests_still_observe_their_real_rate_limits(setup, monkeypatch):
    """A failing model must not permit an unlimited stream of expensive retries."""
    _, as_role = setup
    client = as_role("user")
    monkeypatch.setattr(intake.runtime, "installed", lambda: False)
    for _ in range(6):
        assert client.post("/api/assistant/documents/read", files={"file": ("packing.pdf", b"test", "application/pdf")}).status_code == 409
    assert client.post("/api/assistant/documents/read", files={"file": ("packing.pdf", b"test", "application/pdf")}).status_code == 429
    payload = {"lines": [{"id": "p1l1", "text": "Boxes of bolts"}]}
    for _ in range(30):
        assert client.post("/api/assistant/documents/propose", json=payload).status_code == 409
    assert client.post("/api/assistant/documents/propose", json=payload).status_code == 429
