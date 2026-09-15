"""The document store, seen from the running application.

``scripts/regulations_store.py`` fills a directory with the editions the seeds
were read from; this is the half of that story the server needs. It answers two
questions: where a registered document is on this installation, and how to hand
a driver or a boatmaster the one regulatory document the application may not
paraphrase — the instructions in writing.

ADR 5.4.3.4 and ADN 5.4.3.4 print the instructions rather than describe them:
they must "correspond in form and content" to a model of four pages that the
book itself sets out. A document that has to correspond in *form* cannot be
rebuilt from a database, so what the application offers is the model itself,
taken out of the edition in the store, page range measured with
``scripts/find_instructions_pages.py`` and written into the register beside the
document it is cut from.

The instructions are not the only such model. ADN 8.6.3 prints the checklist
for loading and unloading a tank vessel the same way, and 8.6.4 the one for
degassing. So a model is addressed by its **provision** as well as by regime
and language, and everything below takes all three. Nothing here interprets a
model or fills one in: the application may hand over the form, and the form is
what the book prints.

Nothing here downloads anything. A model the store cannot produce is reported
as missing, with the document that would produce it named, because a carrier
who thinks they have the instructions and has not is worse off than one who
knows they still have to fetch them.
"""
from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path

_SEED_DIR = Path(__file__).resolve().parents[2] / "seed" / "dg"
MANIFEST = _SEED_DIR / "sources.json"

#: Compatibility location for an existing installation's original model PDFs.
#: Fresh releases do not bundle these files. Imports and the source volume
#: store supply locally authorised copies, validated against pinned metadata.
BUNDLED_MODELS = _SEED_DIR.parent / "models"

#: The languages the application speaks. A model is offered per language, and
#: the answer for a language the store cannot serve is "not here", never a
#: neighbouring language's model.
LANGUAGES = ("nl", "en", "de", "fr")
REGIMES = ("adr", "rid", "adn")


@lru_cache(maxsize=1)
def manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):  # pragma: no cover - register missing
        return {"store": {}, "documents": []}


def store_dir() -> Path:
    store = manifest().get("store", {})
    override = os.environ.get(store.get("environment_variable", ""), "")
    if override:
        return Path(override)
    default = Path(store.get("default_path", "/data/regulations"))
    if default.parent.is_dir():
        return default
    return Path(store.get("fallback_path", "/tmp/emcargo-regulations"))


def documents() -> dict[str, dict]:
    return {doc["id"]: doc for doc in manifest().get("documents", [])}


def locate(doc_id: str) -> Path | None:
    """The file of a registered document, or None if this store lacks it."""
    doc = documents().get(doc_id)
    if doc is None:
        return None
    if doc.get("model_of"):
        from app.services.document_templates import resolve
        return resolve(doc_id)
    bases = [store_dir(), BUNDLED_MODELS,
             Path(manifest().get("store", {})
                  .get("fallback_path", "/tmp/emcargo-regulations"))]
    for base in bases:
        candidate = base / doc["filename"]
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def instruction_documents(provision: str = "5.4.3") -> list[dict]:
    """Every model of one provision the register knows, in a fixed order."""
    found = []
    for doc in manifest().get("documents", []):
        model = doc.get("model_of")
        if model and model.get("provision", "5.4.3") == provision:
            found.append(doc)
    return sorted(found, key=lambda d: (REGIMES.index(d["model_of"]["regime"]),
                                        LANGUAGES.index(d["model_of"]["language"])))


def model_provisions() -> list[str]:
    """The provisions the register holds a model for, 5.4.3 first."""
    seen = []
    for doc in manifest().get("documents", []):
        model = doc.get("model_of")
        if model:
            provision = model.get("provision", "5.4.3")
            if provision not in seen:
                seen.append(provision)
    return sorted(seen, key=lambda p: (p != "5.4.3", p))


def instruction_status(regime: str, language: str,
                       provision: str = "5.4.3") -> dict:
    """What this installation can hand over for one regime and language."""
    doc = next((d for d in instruction_documents(provision)
                if d["model_of"]["regime"] == regime
                and d["model_of"]["language"] == language), None)
    if doc is None:
        return {"regime": regime, "language": language, "provision": provision,
                "available": False, "reason": "not_registered"}
    state = {"regime": regime, "language": language,
             "document_id": doc["id"], "edition": doc.get("edition", ""),
             "provision": doc["model_of"].get("provision", "5.4.3")}
    found = locate(doc["id"])
    if found is not None:
        bundled = BUNDLED_MODELS in found.parents
        return {**state, "available": True,
                "source": "bundled" if bundled else "stored"}
    cut = doc.get("cut_from")
    if cut and (source := locate(cut["document"])) is not None:
        from app.services.pdf_pages import verified_model_writer
        try:
            verified_model_writer(source, cut, documents()[cut["document"]].get("sha256"))
        except (OSError, ValueError):
            return {**state, "available": False, "reason": "source_mismatch",
                    "needs": cut["document"]}
        return {**state, "available": True, "source": "cut",
                "from_document": cut["document"]}
    return {**state, "available": False, "reason": "missing_in_store",
            "needs": cut["document"] if cut else doc["id"]}


def instructions_pdf(regime: str, language: str,
                     provision: str = "5.4.3") -> Path | None:
    """The complete registered model as a file, cut from the edition if need be.

    The source identity and complete page sequence are verified for every
    derivation. A writable store keeps the result; otherwise it uses a temporary
    file. Either way the caller gets a path to a PDF that holds
    the model and nothing the model does not have.
    """
    status = instruction_status(regime, language, provision)
    if not status.get("available"):
        return None
    ready = locate(status["document_id"])
    if ready is not None:
        return ready

    doc = documents()[status["document_id"]]
    cut = doc["cut_from"]
    source = locate(cut["document"])
    if source is None:  # pragma: no cover - status said it was there
        return None

    first, last = cut["pages"]
    # The kept cut is named after what it was cut from and where. A register
    # that comes to point at another edition, or at another range in the same
    # one, then asks for a file that does not exist yet instead of being handed
    # yesterday's pages under today's name.
    edition = (documents()[cut["document"]].get("sha256") or "unpinned")[:12]
    stem = Path(doc["filename"]).stem
    target = store_dir() / "derived" / f"{stem}-{edition}-{first}-{last}.pdf"
    from app.services.pdf_pages import verified_model_writer

    pages = verified_model_writer(source, cut, documents()[cut["document"]].get("sha256"))
    target = target.with_name(target.stem + "-pypdf.pdf")
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, suffix=".pdf", delete=False) as handle:
            temporary = Path(handle.name)
            try:
                pages.write(handle)
                handle.flush()
                os.fsync(handle.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        temporary.replace(target)
        return target
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        # A read-only document store still permits a verified temporary export.
        with tempfile.NamedTemporaryFile(suffix=".pdf", prefix="instructions-", delete=False) as handle:
            try:
                pages.write(handle)
            except BaseException:
                Path(handle.name).unlink(missing_ok=True)
                raise
            return Path(handle.name)
