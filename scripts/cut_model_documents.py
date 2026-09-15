#!/usr/bin/env python3
"""Cut the prescribed model documents out of the editions in the store.

ADR/RID/ADN 5.4.3.4 print the instructions in writing as a four-page model
that must "correspond in form and content" to what the book shows, and ADN
8.6.3 prints the loading/unloading checklist the same way. The application
serves those models as the edition prints them (``app/services/regulations``)
— but only when the edition is in the installation's regulations store, and a
fresh installation has an empty store. This script produces the models once,
so they can be bundled with the application and every installation can hand
a driver or boatmaster the paper without first collecting gigabytes of books.

For every register entry with ``model_of`` and ``cut_from`` it:

1. locates the source edition in the store (default path, then the CI cache
   fallback), and **verifies its SHA-256 against the pin in the register** —
   a book that does not hash to the recorded edition is not cut, because the
   page range was measured on that edition and no other;
2. selects every page by its registered content fingerprint with pypdf;
   historical MuPDF page numbers are search hints, not permission to copy
   unchecked pages from a different parser's page tree;
3. writes the cut under its registered filename into ``backend/seed/models/``
   and records the provenance (source id, source hash, pages, cut hash) in
   ``manifest.json`` beside it.

A missing or mismatching source fails the run by name; ``--lenient`` cuts
what is there and reports the rest, for a store that holds only some books.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.pdf_pages import verified_model_writer  # noqa: E402

REGISTER = ROOT / "backend" / "seed" / "dg" / "sources.json"
DEFAULT_OUT = ROOT / "backend" / "seed" / "models"
STORES = (Path("/data/regulations"), Path("/tmp/emcargo-regulations"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate(filename: str, extra: list[Path]) -> Path | None:
    for base in [*extra, *STORES]:
        candidate = base / filename
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--store", type=Path, action="append", default=[],
                        help="Additional directory to look for source books in")
    parser.add_argument("--lenient", action="store_true",
                        help="Cut what is present; report the rest without failing")
    args = parser.parse_args()

    register = json.loads(REGISTER.read_text(encoding="utf-8"))
    documents = {doc["id"]: doc for doc in register["documents"]}
    models = [doc for doc in register["documents"]
              if doc.get("model_of") and doc.get("cut_from")]
    if not models:
        print("The register holds no cuttable models; nothing to do.")
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    problems: list[str] = []
    verified: dict[str, Path] = {}

    for doc in models:
        cut = doc["cut_from"]
        source_doc = documents[cut["document"]]
        pin = source_doc.get("sha256")
        if not pin:
            problems.append(f"{doc['id']}: source {source_doc['id']} has no "
                            "pinned sha256 — the page range has no identity to hold on to")
            continue
        source = verified.get(source_doc["id"])
        if source is None:
            found = locate(source_doc["filename"], args.store)
            if found is None:
                problems.append(f"{doc['id']}: source {source_doc['id']} "
                                f"({source_doc['filename']}) is not in the store")
                continue
            actual = sha256(found)
            if actual != pin:
                problems.append(f"{doc['id']}: {found} hashes to {actual[:12]}…, "
                                f"the register pins {pin[:12]}… — another edition, not cut")
                continue
            verified[source_doc["id"]] = found
            source = found

        first, last = cut["pages"]
        target = args.out / doc["filename"]
        try:
            pages = verified_model_writer(source, cut, pin)
        except ValueError as exc:
            problems.append(f"{doc['id']}: {exc}")
            continue
        pages.write(target)
        page_count = len(pages.pages)
        entries.append({
            "id": doc["id"],
            "file": doc["filename"],
            "provision": doc["model_of"].get("provision", "5.4.3"),
            "regime": doc["model_of"]["regime"],
            "language": doc["model_of"]["language"],
            "source_document": source_doc["id"],
            "source_sha256": pin,
            "source_pages": [first, last],
            "pages": page_count,
            "size": target.stat().st_size,
            "sha256": sha256(target),
        })
        print(f"cut {doc['id']}: pages {first}-{last} of {source_doc['id']} "
              f"-> {target.name} ({page_count} pages, {target.stat().st_size / 1e3:.0f} kB)")

    manifest = {
        "_comment": ("Prescribed model documents (instructions in writing 5.4.3, "
                     "ADN checklist 8.6.3), cut verbatim from the pinned editions "
                     "by scripts/cut_model_documents.py. Nothing here is written "
                     "or summarised: each file is the pages the book prints."),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "models": sorted(entries, key=lambda e: (e["provision"], e["regime"],
                                                 e["language"])),
        "missing": sorted(problems),
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=1) + "\n", encoding="utf-8")

    print(f"\n{len(entries)} model(s) cut, {len(problems)} problem(s)")
    for problem in problems:
        print(f"  - {problem}")
    if problems and not args.lenient:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
