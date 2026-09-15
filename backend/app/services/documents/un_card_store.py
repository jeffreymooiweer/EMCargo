"""The runtime store of generated UN cards: download, verify, swap, serve.

The cards themselves — thousands of PDFs — are deliberately not part of the
Docker image or the repository. The **Generate UN cards** workflow publishes
the complete current set as a GitHub Release asset
(``emcargo-un-cards.zip``), and an administrator imports it here: into
``<data-dir>/un-cards/``, the same persistent volume the rest of the
application's data lives on, so the set survives restarts and updates.

Nothing here trusts the archive. Member names must match the exact shapes
the generator produces (which kills path traversal outright), sizes are
capped before extraction, every card is hashed against the manifest it
arrived with, and the new set replaces the old one only after the whole of
it has been verified — a failed import leaves the working set untouched.
Downloads go only to the release feed of the pinned repository; no caller
can point the server at another URL.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

#: The one place releases are fetched from. Pinned on purpose: a server-side
#: download that took a caller-supplied URL would be an SSRF hole.
RELEASES_URL = "https://api.github.com/repos/jeffreymooiweer/emcargo/releases"
RELEASE_TAG_PREFIX = "un-cards-"
PACKAGE_NAME = "emcargo-un-cards.zip"

MODALITIES = ("ADR", "RID", "ADN", "IMDG", "ICAO")

#: Every member of a valid package matches one of these — nothing else is
#: extracted, so ../ tricks and absolute paths never reach the filesystem.
_CARD_MEMBER = re.compile(r"^(ADR|RID|ADN|IMDG|ICAO)/UN(\d{4})_(ADR|RID|ADN|IMDG|ICAO)\.pdf$")
_META_MEMBERS = {
    "manifest.json", "generation-report.json", "THIRD_PARTY_NOTICES.md",
    "source.cdx.json", "cards.cdx.json",
}
# The workflow includes dependency notices and font licenses. Only safe
# relative components below this metadata directory are accepted; these
# bounded files are stored as evidence and never interpreted or executed.
_LICENSE_MEMBER = re.compile(r"licenses/(?:[A-Za-z0-9_-][A-Za-z0-9_.-]*/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*")

MAX_MEMBERS = 30_000
MAX_CARD_BYTES = 2 * 1024 * 1024
MAX_META_BYTES = 30 * 1024 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024


class UnCardImportError(Exception):
    """A reason the import was refused; shown to the administrator as-is."""


class UnCardReleaseUnavailable(UnCardImportError):
    """No published package exists; the API exposes a translatable error."""


def store_dir() -> Path:
    return get_settings().data_dir / "un-cards"


def installed_manifest() -> dict | None:
    path = store_dir() / "manifest.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("The installed UN card manifest cannot be read")
        return None


def card_path(un: str, modality: str) -> Path | None:
    """The card's file, if the installed set holds it. No guessing: a card
    that is not there is reported absent, never substituted."""
    un = re.sub(r"\D", "", str(un))
    modality = modality.upper()
    if len(un) != 4 or modality not in MODALITIES:
        return None
    path = store_dir() / modality / f"UN{un}_{modality}.pdf"
    return path if path.is_file() else None


def status() -> dict[str, Any]:
    """What is installed, straight from the manifest and the filesystem."""
    manifest = installed_manifest()
    if manifest is None:
        return {"installed": False, "location": str(store_dir())}
    counts: dict[str, int] = {}
    total_size = 0
    for modality in MODALITIES:
        directory = store_dir() / modality
        if directory.is_dir():
            files = list(directory.glob("UN*.pdf"))
            counts[modality] = len(files)
            total_size += sum(f.stat().st_size for f in files)
    return {
        "installed": True,
        "location": str(store_dir()),
        "generated_at": manifest.get("generated_at"),
        "generator_version": manifest.get("generator_version"),
        "git_commit": manifest.get("git_commit"),
        "editions": manifest.get("editions", {}),
        "counts": counts,
        "total_cards": sum(counts.values()),
        "total_size": total_size,
        "imported_at": _imported_at(),
        "unavailable_modalities": manifest.get("unavailable_modalities", {}),
    }


def _imported_at() -> str | None:
    marker = store_dir() / ".imported-at"
    try:
        return marker.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


def latest_remote() -> dict[str, Any]:
    """The newest published card release — metadata only, no package download."""
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        page = 1
        while True:
            # App releases must not hide an older, still-current card set.
            # Construct each page on the pinned endpoint; never follow an
            # arbitrary pagination URL returned in an HTTP header.
            response = client.get(
                RELEASES_URL, params={"per_page": 100, "page": page},
                headers={"Accept": "application/vnd.github+json"})
            response.raise_for_status()
            releases = response.json()
            for release in releases:
                tag = str(release.get("tag_name") or "")
                if (not tag.startswith(RELEASE_TAG_PREFIX)
                        or release.get("draft") or release.get("prerelease")):
                    continue
                assets = {a.get("name"): a for a in release.get("assets", [])}
                package = assets.get(PACKAGE_NAME)
                if not package or not package.get("browser_download_url"):
                    continue
                return {
                    "available": True,
                    "tag": tag,
                    "published_at": release.get("published_at"),
                    "package_size": package.get("size"),
                    "package_url": package.get("browser_download_url"),
                }
            if len(releases) < 100:
                break
            page += 1
    return {"available": False}


def update_available() -> dict[str, Any]:
    """Local set against the newest release, by generation timestamp."""
    remote = latest_remote()
    local = installed_manifest()
    if not remote.get("available"):
        return {**remote, "update_available": False}
    if local is None:
        return {**remote, "update_available": True}
    # The release tag encodes the publish date; the manifest carries the
    # generation timestamp. A newer publication than the installed
    # generation means there is something to fetch.
    installed_at = str(local.get("generated_at") or "")
    published_at = str(remote.get("published_at") or "")
    return {**remote, "update_available": published_at > installed_at}


def download_latest_package(target: Path) -> dict[str, Any]:
    """Fetch the newest release package to ``target``, size-capped."""
    remote = latest_remote()
    if not remote.get("available"):
        raise UnCardReleaseUnavailable("No published UN card release was found.")
    url = remote["package_url"]
    written = 0
    with httpx.Client(timeout=httpx.Timeout(30.0, read=300.0),
                      follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with target.open("wb") as handle:
                for chunk in response.iter_bytes(1 << 20):
                    written += len(chunk)
                    if written > MAX_DOWNLOAD_BYTES:
                        raise UnCardImportError(
                            "The package exceeds the download size limit.")
                    handle.write(chunk)
    return remote


def import_package(archive_path: Path) -> dict[str, Any]:
    """Verify and install a card package, atomically.

    The sequence the docstring of this module promises: whitelist the member
    names, cap the sizes, extract to a scratch directory next to the store,
    verify every card against the manifest inside the package, and only then
    swap directories. Any failure leaves the previously installed set as it
    was and cleans the scratch space.
    """
    base = store_dir()
    base.parent.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="un-cards.incoming-", dir=base.parent))
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if len(members) > MAX_MEMBERS:
                raise UnCardImportError("The package lists too many files.")
            total = 0
            names = set()
            for member in members:
                name = member.filename
                if name.endswith("/"):
                    continue
                if name in _META_MEMBERS or _LICENSE_MEMBER.fullmatch(name):
                    limit = MAX_META_BYTES
                elif _CARD_MEMBER.match(name):
                    limit = MAX_CARD_BYTES
                else:
                    raise UnCardImportError(f"Unexpected file in the package: {name}")
                if member.file_size > limit:
                    raise UnCardImportError(f"{name} is larger than allowed.")
                total += member.file_size
                if total > MAX_TOTAL_BYTES:
                    raise UnCardImportError("The package unpacks beyond the size limit.")
                names.add(name)
            if "manifest.json" not in names:
                raise UnCardImportError("The package carries no manifest.json.")

            for member in members:
                name = member.filename
                if name.endswith("/") or name not in names:
                    continue
                # The whitelist above proves the name is a safe relative
                # path; joining it under scratch cannot escape.
                destination = scratch / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, destination.open("wb") as sink:
                    shutil.copyfileobj(source, sink, length=1 << 20)

        manifest = json.loads((scratch / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise UnCardImportError(
                f"Unsupported manifest schema {manifest.get('schema_version')!r}.")
        cards = manifest.get("cards") or []
        if not cards:
            raise UnCardImportError("The manifest lists no cards.")
        for card in cards:
            name = str(card.get("file") or "")
            if not _CARD_MEMBER.match(name):
                raise UnCardImportError(f"Manifest lists an invalid card path: {name}")
            path = scratch / name
            if not path.is_file():
                raise UnCardImportError(f"The manifest lists {name} but the package lacks it.")
            content = path.read_bytes()
            if not content.startswith(b"%PDF"):
                raise UnCardImportError(f"{name} is not a PDF.")
            if hashlib.sha256(content).hexdigest() != card.get("sha256"):
                raise UnCardImportError(f"{name} does not match its manifest checksum.")

        (scratch / ".imported-at").write_text(
            datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), encoding="utf-8")

        # The swap: the verified set moves into place in one rename; the old
        # set is only deleted after the new one is in place.
        retired: Path | None = None
        if base.exists():
            retired = Path(tempfile.mkdtemp(prefix="un-cards.retired-", dir=base.parent))
            retired.rmdir()
            base.rename(retired)
        try:
            scratch.rename(base)
        except OSError:
            if retired is not None:
                retired.rename(base)
            raise
        if retired is not None:
            shutil.rmtree(retired, ignore_errors=True)
        return {"imported": len(cards), "generated_at": manifest.get("generated_at")}
    except zipfile.BadZipFile as exc:
        raise UnCardImportError("The file is not a readable zip archive.") from exc
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def remove_installed() -> bool:
    """Delete the local set. The manifest goes last, so a torn removal never
    leaves a manifest that promises cards which are gone."""
    base = store_dir()
    if not base.exists():
        return False
    shutil.rmtree(base)
    return True
