import base64
import io

import pytest
from PIL import Image

from app.services.documents.signature import decode_signature_image


def _data_url(img: Image.Image, fmt: str = "PNG", mime: str = "image/png") -> str:
    buf = io.BytesIO()
    img.save(buf, fmt)
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode()


def _signature_img(bg=(255, 255, 255)) -> Image.Image:
    from PIL import ImageDraw

    img = Image.new("RGB", (300, 100), bg)
    draw = ImageDraw.Draw(img)
    draw.line([(30, 30), (270, 70)], fill=(20, 30, 90), width=10)
    return img


def test_decode_normalizes_to_cropped_transparent_png():
    png = decode_signature_image(_data_url(_signature_img()))
    out = Image.open(io.BytesIO(png))
    assert out.mode == "RGBA"
    # cropped tightly around the ink (smaller than the original 300x100 canvas)
    assert out.width < 260 and out.height < 60
    # witte achtergrond transparant
    assert out.getpixel((0, 0))[3] in (0, 255)


def test_decode_accepts_jpeg():
    png = decode_signature_image(_data_url(_signature_img(), "JPEG", "image/jpeg"))
    assert Image.open(io.BytesIO(png)).mode == "RGBA"


def test_rejects_invalid_mime():
    with pytest.raises(ValueError):
        decode_signature_image("data:text/html;base64,PGI+aGk8L2I+")


def test_rejects_garbage_base64():
    with pytest.raises(ValueError):
        decode_signature_image("data:image/png;base64,not-base64!!")


def test_rejects_fully_white_image():
    img = Image.new("RGB", (200, 80), "white")
    with pytest.raises(ValueError):
        decode_signature_image(_data_url(img))


def test_cmr_signature_stamped(tmp_path, official_templates):
    pytest.importorskip("fitz")
    from app.services.documents.pdf_forms import fill_pdf_document, has_pdf_template

    if not has_pdf_template("cmr"):
        pytest.skip("cmr template not available")
    png = decode_signature_image(_data_url(_signature_img()))
    out = fill_pdf_document(
        "cmr",
        {"consignor_name": "Test BV", "consignor_address": "Straat 1", "consignee_name": "X", "consignee_address": "Y"},
        [{"description": "pallet", "quantity": 1, "include": True}],
        None,
        "nl",
        signature_png=png,
    )
    import fitz

    doc = fitz.open(str(out))
    # box 22 (consignor) now has dark pixels on all four copies
    for page_no in range(4):
        pix = doc[page_no].get_pixmap(matrix=fitz.Matrix(2, 2), clip=fitz.Rect(48, 742, 200, 786))
        assert any(sum(pix.pixel(x, y)) < 500 for x in range(pix.width) for y in range(pix.height))
    doc.close()
    out.unlink()


def test_generated_pdf_contains_signature():
    from app.services.documents import get_document
    from app.services.documents.pdf_render import render_document_pdf

    png = decode_signature_image(_data_url(_signature_img()))
    out = render_document_pdf(
        get_document("packing_list"),
        {"consignor_name": "Test BV"},
        [{"description": "pallet", "quantity": 1, "include": True}],
        None,
        "nl",
        signature_png=png,
    )
    assert out.stat().st_size > 1000
    out.unlink()
