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
    """Keep cells on one physical table row together instead of losing columns."""
    words = sorted(page.get_text("words"), key=lambda word: (round(word[1], 1), word[0]))
    rows: list[list] = []
    for word in words:
        if not rows or abs(word[1] - rows[-1][0][1]) > max(2, (word[3] - word[1]) * .35):
            rows.append([word])
        else:
            rows[-1].append(word)
    return [{"text": " ".join(str(word[4]) for word in sorted(row, key=lambda word: word[0])),
             "confidence": None} for row in rows]


def read(path: str, extension: str, language: str) -> dict:
    import pymupdf
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_SOURCE_PIXELS
    data = Path(path).read_bytes()
    try:
        if extension in {"jpg", "jpeg", "png"}:
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"PNG", "JPEG"}:
                    raise ReadError("unsupported")
                if original.width * original.height > MAX_SOURCE_PIXELS:
                    raise ReadError("image_large")
                image = ImageOps.exif_transpose(original).convert("RGB")
                scale = min(1, math.sqrt(MAX_PIXELS / (image.width * image.height)))
                if scale < 1:
                    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
                output = io.BytesIO()
                image.save(output, format="PNG")
                data = output.getvalue()
            with pymupdf.open(stream=data, filetype="png") as picture:
                document = pymupdf.open(stream=picture.convert_to_pdf(), filetype="pdf")
        else:
            document = pymupdf.open(stream=data, filetype="pdf")
    except ReadError:
        raise
    except (Exception, Warning) as exc:
        raise ReadError("invalid") from exc
    with document:
        if document.needs_pass:
            raise ReadError("encrypted")
        if not 0 < len(document) <= MAX_PAGES:
            raise ReadError("pages")
        pages, total_text, total_lines = [], 0, 0
        for index, page in enumerate(document):
            area = page.rect.width * page.rect.height
            if not math.isfinite(area) or area <= 0 or area > 100_000_000:
                raise ReadError("image_large")
            lines = _text_lines(page)
            images = page.get_image_info()
            # Even a small image can be the complete goods table beneath a
            # native PDF heading. Its area cannot decide whether to read it.
            needs_ocr = extension != "pdf" or bool(images)
            method, warnings = "text", []
            if needs_ocr:
                zoom = min(2.5, math.sqrt(MAX_PIXELS / area))
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB, alpha=False)
                lines, warnings = _ocr(pixmap.tobytes("png"), language)
                method = "ocr"
            lines = [{**line, "id": f"p{index + 1}l{n + 1}"} for n, line in enumerate(lines) if line["text"].strip()]
            if not lines:
                warnings.append("empty_page")
            total_text += sum(len(line["text"]) for line in lines)
            total_lines += len(lines)
            if total_text > MAX_TEXT or total_lines > MAX_LINES:
                raise ReadError("text_large")
            zoom = min(1.5, 1000 / max(page.rect.width, page.rect.height))
            preview = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB, alpha=False)
            pages.append({"number": index + 1, "method": method, "lines": lines, "warnings": warnings,
                          "preview": "data:image/jpeg;base64," + base64.b64encode(preview.tobytes("jpg", jpg_quality=75)).decode()})
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
