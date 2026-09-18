"""Installation-owned PDF templates, validated against reviewed mappings.

An import records the operator's source and basis for local use. It never
changes the project's redistribution rights. Immutable PDF versions are kept
so replacing the current selection cannot destroy an earlier document input.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from app.core.config import get_settings
from app.core.messages import error

PROFILES = Path(__file__).resolve().parents[1] / "config/document_templates.json"
BUNDLED_FORMS = Path(__file__).resolve().parents[3] / "templates/forms"
MAX_BYTES = 30 * 1024 * 1024


def profiles() -> dict[str, dict]:
    return {item["id"]: item for item in json.loads(PROFILES.read_text())["templates"]}


def _directory(key: str) -> Path:
    if key not in profiles():
        raise error(404, "templates.unknown")
    return get_settings().data_dir / "document-templates" / key


def validate(key: str, content: bytes) -> str:
    profile = profiles().get(key)
    if profile is None:
        raise error(404, "templates.unknown")
    if not content or len(content) > MAX_BYTES:
        raise error(422, "templates.size")
    digest = hashlib.sha256(content).hexdigest()
    # Exact identity protects field mappings, all pages and the issuing body's
    # artwork. Matching only a filename or a few field names is insufficient.
    if digest != profile["sha256"]:
        raise error(422, "templates.incompatible")
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        if reader.is_encrypted or len(reader.pages) != profile["pages"]:
            raise ValueError("Unexpected page count or encryption")
        boxes = [[round(float(x), 3) for x in page.mediabox] for page in reader.pages]
        if boxes != profile["media_boxes"] or sorted((reader.get_fields() or {}).keys()) != profile["fields"]:
            raise ValueError("Unexpected page geometry or fields")
    except Exception as exc:
        raise error(422, "templates.incompatible") from exc
    return digest


def resolve(key: str) -> Path | None:
    profile = profiles().get(key)
    if profile is None:
        return None
    directory = _directory(key)
    candidates = []
    try:
        receipt = json.loads((directory / "current.json").read_text())
        # Use the registered digest, never an arbitrary path from a receipt.
        if receipt.get("sha256") == profile["sha256"]:
            candidates.append(directory / f"{profile['sha256']}.pdf")
    except (OSError, ValueError):
        pass
    if profile["kind"] == "form":
        candidates += [get_settings().data_dir / "templates/forms" / profile["filename"],
                       BUNDLED_FORMS / profile["filename"]]
    else:
        from app.services import regulations
        candidates += [regulations.store_dir() / profile["filename"],
                       regulations.BUNDLED_MODELS / profile["filename"]]
    for path in candidates:
        try:
            if not path.is_symlink() and path.stat().st_size <= MAX_BYTES:
                if hashlib.sha256(path.read_bytes()).hexdigest() == profile["sha256"]:
                    return path
        except OSError:
            continue
    return None


def status() -> list[dict]:
    return [{"id": p["id"], "name": p["name"], "kind": p["kind"],
             "filename": p["filename"], "pages": p["pages"], "sha256": p["sha256"],
             "available": resolve(p["id"]) is not None} for p in profiles().values()]


def _atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            owner = path.parent.stat()
            os.chown(temporary, owner.st_uid, owner.st_gid)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install(key: str, content: bytes, *, source: str, rights_basis: str, actor: str) -> dict:
    if not source.strip() or not rights_basis.strip():
        raise error(422, "templates.source_required")
    digest = validate(key, content)
    directory = _directory(key)
    directory.mkdir(parents=True, exist_ok=True)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        owner = get_settings().data_dir.stat()
        os.chown(directory.parent, owner.st_uid, owner.st_gid)
        os.chown(directory, owner.st_uid, owner.st_gid)
    receipt = {"id": key, "sha256": digest, "source": source.strip(),
               "local_use_basis": rights_basis.strip(), "actor": actor,
               "imported_at": datetime.now(timezone.utc).isoformat()}
    _atomic(directory / f"{digest}.pdf", content)
    encoded = (json.dumps(receipt, indent=2) + "\n").encode()
    _atomic(directory / f"{digest}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}.json", encoded)
    _atomic(directory / "current.json", encoded)
    return receipt


def retain_legacy(key: str, content: bytes, source: str) -> None:
    """Preserve a known template during an upgrade, without a new rights grant."""
    if resolve(key) is None:
        install(key, content, source=source,
                rights_basis="Retained from this installation; original terms still apply. No redistribution grant inferred.",
                actor="installation-upgrade")
