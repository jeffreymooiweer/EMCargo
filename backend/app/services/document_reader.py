"""Bounded, local document reading in a disposable subprocess.

No model, network requests or persistent source files. The parent enforces an
overall deadline; Tesseract also has its own deadline for every page.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

MAX_PAGES = 10
MAX_PIXELS = 12_000_000
MAX_SOURCE_PIXELS = 60_000_000
MAX_TEXT = 40_000
MAX_LINES = 1200
LANGUAGES = {"nl": "nld", "en": "eng", "de": "deu", "fr": "fra"}


class ReadError(Exception):
    pass


def _ocr(png: bytes, language: str) -> tuple[list[dict], list[str]]:
    executable = shutil.which("tesseract")
    if not executable:
        raise ReadError("ocr_missing")
    try:
        probe = subprocess.run([executable, "--list-langs"], capture_output=True, timeout=5, check=True)
        installed = set(probe.stdout.decode("utf-8", "replace").splitlines()[1:])
        wanted = LANGUAGES.get(language, "eng")
        chosen = [key for key in (wanted, "eng") if key in installed]
        chosen = list(dict.fromkeys(chosen))
        if not chosen:
            raise ReadError("ocr_missing")
        result = subprocess.run(
            [executable, "stdin", "stdout", "-l", "+".join(chosen), "--psm", "3", "tsv"],
            input=png, capture_output=True, timeout=25, check=True,
            env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    except subprocess.TimeoutExpired as exc:
        raise ReadError("timeout") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReadError("ocr_failed") from exc
    words = []
    for word in csv.DictReader(io.StringIO(result.stdout.decode("utf-8", "replace")), delimiter="\t"):
        if word.get("level") != "5" or not (word.get("text") or "").strip():
            continue
        words.append(word)
    # Tesseract may put adjacent table columns in separate blocks. Reassemble
    # physical rows so that a quantity stays beside its own goods description.
    grouped: list[list[dict]] = []
    for word in sorted(words, key=lambda item: (int(item["top"]), int(item["left"]))):
        if not grouped or abs(int(word["top"]) - int(grouped[-1][0]["top"])) > max(3, int(word["height"]) * .45):
            grouped.append([word])
        else:
            grouped[-1].append(word)
    lines = []
    for words in grouped:
        words.sort(key=lambda word: int(word["left"]))
        confidences = [float(word.get("conf") or 0) for word in words]
        lines.append({"text": " ".join(word["text"] for word in words),
                      "confidence": round(min(confidences), 1)})
    warnings = ["language_fallback"] if wanted not in installed else []
    if any(line["confidence"] < 65 for line in lines):
        warnings.append("low_confidence")
    return lines, warnings


def _text_lines(page) -> list[dict]:
    """pypdf's physical layout keeps neighbouring table cells on one row."""
    text = page.extract_text(extraction_mode="layout", layout_mode_strip_rotated=False)
    return [{"text": " ".join(line.split()), "confidence": None}
            for line in text.splitlines() if line.strip()]


def _encoded_image(image, *, preview: bool = False) -> bytes:
    output = io.BytesIO()
    if preview:
        with image.convert("RGB") as thumbnail:
            thumbnail.thumbnail((1000, 1000))
            thumbnail.save(output, format="JPEG", quality=75)
    else:
        image.save(output, format="PNG")
    return output.getvalue()


def _render(page, scale: float, *, preview: bool = False) -> bytes:
    # Rendering happens only in this bounded subprocess. PDFium is not called
    # concurrently from API threads, and its native buffers close explicitly.
    bitmap = page.render(scale=scale)
    try:
        image = bitmap.to_pil()
        try:
            return _encoded_image(image, preview=preview)
        finally:
            image.close()
    finally:
        bitmap.close()


def read(path: str, extension: str, language: str) -> dict:
    import pypdfium2 as pdfium
    from pypdf import PdfReader
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS
    data = Path(path).read_bytes()
    pages, total_text, total_lines = [], 0, 0

    def append(index, lines, warnings, method, preview):
        nonlocal total_text, total_lines
        lines = [{**line, "id": f"p{index + 1}l{n + 1}"} for n, line in enumerate(lines) if line["text"].strip()]
        if not lines:
            warnings.append("empty_page")
        total_text += sum(len(line["text"]) for line in lines)
        total_lines += len(lines)
        if total_text > MAX_TEXT or total_lines > MAX_LINES:
            raise ReadError("text_large")
        pages.append({"number": index + 1, "method": method, "lines": lines, "warnings": warnings,
                      "preview": "data:image/jpeg;base64," + base64.b64encode(preview).decode()})

    try:
        if extension in {"jpg", "jpeg", "png"}:
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"PNG", "JPEG"}:
                    raise ReadError("unsupported")
                if original.width * original.height > MAX_SOURCE_PIXELS:
                    raise ReadError("image_large")
                image = ImageOps.exif_transpose(original).convert("RGB")
                try:
                    scale = min(1, math.sqrt(MAX_PIXELS / (image.width * image.height)))
                    if scale < 1:
                        resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
                        image.close()
                        image = resized
                    lines, warnings = _ocr(_encoded_image(image), language)
                    append(0, lines, warnings, "ocr", _encoded_image(image, preview=True))
                finally:
                    image.close()
        else:
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ReadError("encrypted")
            if not 0 < len(reader.pages) <= MAX_PAGES:
                raise ReadError("pages")
            with pdfium.PdfDocument(data) as document:
                document.init_forms()
                if len(document) != len(reader.pages):
                    raise ReadError("invalid")
                for index, source in enumerate(reader.pages):
                    page = document[index]
                    try:
                        width, height = page.get_size()
                        area = width * height
                        if not math.isfinite(area) or area <= 0 or area > 100_000_000:
                            raise ReadError("image_large")
                        lines = _text_lines(source)
                        method, warnings = "text", []
                        # Image identifiers do not decode their pixel buffers.
                        # Any image may contain the entire table below a heading.
                        if len(source.images) or source.get("/Annots"):
                            scale = min(2.5, math.sqrt(MAX_PIXELS / area))
                            lines, warnings = _ocr(_render(page, scale), language)
                            method = "ocr"
                        preview = _render(page, min(1.5, 1000 / max(width, height)), preview=True)
                        append(index, lines, warnings, method, preview)
                    finally:
                        page.close()
    except ReadError:
        raise
    except (Exception, Warning) as exc:
        raise ReadError("invalid") from exc
    if not total_text:
        raise ReadError("no_text")
    return {"pages": pages}


if __name__ == "__main__":
    try:
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (65, 65))
            resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))
        except (ImportError, ValueError, OSError):
            pass
        result = read(*sys.argv[1:4])
    except ReadError as exc:
        result = {"error": str(exc)}
    except Exception:
        result = {"error": "invalid"}
    print(json.dumps(result, ensure_ascii=False))
