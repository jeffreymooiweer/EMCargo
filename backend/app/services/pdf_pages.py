"""Select prescribed PDF pages by their pinned content, not library page counts."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def page_fingerprint(page) -> str:
    text = re.sub(r"\s+", " ", unicodedata.normalize("NFC", page.extract_text() or "")).strip()
    payload = {"text": text, "media_box": [round(float(x), 3) for x in page.mediabox],
               "crop_box": [round(float(x), 3) for x in page.cropbox], "rotation": page.rotation}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def verified_model_writer(source: Path, cut: dict, expected_source_sha256: str) -> PdfWriter:
    """Refuse an unpinned edition, an incomplete model or ambiguous page matches.

    Historic ranges were measured by MuPDF; pypdf can count an extra page in
    ADN volumes. A small search around that known range is permitted only when
    every page matches the fingerprints of the previously verified model.
    A new edition requires new measured fingerprints, never an unchecked range.
    """
    if not expected_source_sha256 or file_sha256(source) != expected_source_sha256:
        raise ValueError("The regulation source does not match its registered SHA-256")
    fingerprints = cut.get("page_fingerprints")
    first, last = cut["pages"]
    if (cut.get("fingerprint_method") != "pypdf-text-and-boxes-v1"
            or not isinstance(fingerprints, list) or len(fingerprints) != last - first + 1):
        raise ValueError("This regulatory model needs verified pypdf page fingerprints")
    reader = PdfReader(source)
    cache: dict[int, str] = {}
    matches = []
    for start in range(max(0, first - 1 - 4), min(len(reader.pages) - len(fingerprints) + 1, first + 4)):
        for offset, expected in enumerate(fingerprints):
            number = start + offset
            if number not in cache:
                cache[number] = page_fingerprint(reader.pages[number])
            if cache[number] != expected:
                break
        else:
            matches.append(start)
    if len(matches) != 1:
        raise ValueError("The prescribed model pages are missing or ambiguous in this source")
    writer = PdfWriter()
    for number in range(matches[0], matches[0] + len(fingerprints)):
        writer.add_page(reader.pages[number])
    return writer
