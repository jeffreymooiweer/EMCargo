"""Generate EMCargo UN cards: UN####_<MODALITY>.pdf, manifest and package.

Usage (from the repository root):

    # one UN number, for review
    python scripts/un_cards/generate.py --scope single --un 1203 --out /tmp/cards

    # the complete current set, manifest and downloadable package
    python scripts/un_cards/generate.py --scope all --out /tmp/cards \
        --zip /tmp/emcargo-un-cards.zip

Each UN number × modality yields one PDF named ``UN####_<MODALITY>.pdf`` in a
per-modality directory; a UN number with several transport entries in the
same table yields several pages inside that one PDF. In ``--scope all`` each
modality generates exactly the UN numbers its own measured table assigns —
nothing is borrowed across modalities. A modality whose source table this
repository does not hold **fails** for that combination (single mode) or is
reported ``not_applicable`` for the whole run (all mode, where asking RID for
2,345 cards it cannot honestly answer would only bury the report) — because
an invented card is worse than an absent one.

Every run writes ``generation-report.json``; ``--manifest`` (implied by
``--zip``) writes the ``manifest.json`` the application's import validates
against, with a SHA-256 per card and the edition read from each seed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from un_cards.render import render_card_pdf
from un_cards.sources import adn, adr, icao, imdg, rid
from un_cards.sources.base import MODALITIES, REPO, SourceUnavailable

ADAPTERS = {
    "ADR": adr,
    "RID": rid,
    "ADN": adn,
    "IMDG": imdg,
    "ICAO": icao,
}

MANIFEST_SCHEMA_VERSION = 1


def _config() -> dict:
    path = Path(__file__).resolve().parent / "generator_config.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _editions() -> dict[str, str | None]:
    """Per modality, the edition its seed records — or None without a seed."""
    editions: dict[str, str | None] = {}
    for modality, spec in _config()["modalities"].items():
        seed = spec.get("seed")
        if not seed:
            editions[modality] = None
            continue
        data = json.loads((REPO / seed).read_text(encoding="utf-8"))
        editions[modality] = data.get("edition") or data.get("amendment") or data.get("source")
    return editions


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
            text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def generate(un_numbers: list[str] | None, modalities: list[str],
             out_dir: Path) -> dict:
    """Generate cards; ``un_numbers=None`` means every number per modality."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report: dict = {
        "generated_at": generated_at,
        "generator_version": _config()["generator_version"],
        "git_commit": _git_commit(),
        "results": [],
        "not_applicable": {},
        "summary": {"generated": 0, "failed": 0, "not_applicable": 0},
    }
    for modality in modalities:
        adapter = ADAPTERS[modality]
        if un_numbers is None:
            targets = adapter.available_un_numbers()
            if not targets:
                # The whole modality has no measured table; one honest line
                # beats thousands of identical failures.
                try:
                    adapter.cards("0000")
                except SourceUnavailable as exc:
                    report["not_applicable"][modality] = str(exc)
                report["summary"]["not_applicable"] += 1
                continue
        else:
            targets = [u.strip().upper().removeprefix("UN").strip() for u in un_numbers]

        directory = out_dir / modality
        for un in targets:
            entry: dict = {"un_number": un, "modality": modality}
            try:
                pages = adapter.cards(un)
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / f"UN{un}_{modality}.pdf"
                render_card_pdf(path, pages, generated_at)
                content = path.read_bytes()
                if not content.startswith(b"%PDF"):
                    raise RuntimeError("output is not a PDF")
                entry.update(
                    status="generated",
                    file=f"{modality}/{path.name}",
                    pages=len(pages),
                    size=len(content),
                    sha256=hashlib.sha256(content).hexdigest(),
                    regulation=pages[0].regulation,
                )
                report["summary"]["generated"] += 1
            except SourceUnavailable as exc:
                entry.update(status="failed", reason=str(exc))
                report["summary"]["failed"] += 1
            report["results"].append(entry)

    (out_dir / "generation-report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def build_manifest(out_dir: Path, report: dict) -> dict:
    editions = _editions()
    cards = []
    per_modality: dict[str, int] = {}
    total_size = 0
    for row in report["results"]:
        if row["status"] != "generated":
            continue
        cards.append({
            "un_number": row["un_number"],
            "modality": row["modality"],
            "file": row["file"],
            "pages": row["pages"],
            "size": row["size"],
            "sha256": row["sha256"],
            "status": "available",
            "source": editions.get(row["modality"]),
        })
        per_modality[row["modality"]] = per_modality.get(row["modality"], 0) + 1
        total_size += row["size"]
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": report["generated_at"],
        "generator_version": report["generator_version"],
        "git_commit": report["git_commit"],
        "editions": editions,
        "counts": per_modality,
        "total_cards": len(cards),
        "total_size": total_size,
        "unavailable_modalities": report.get("not_applicable", {}),
        "cards": cards,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def build_zip(out_dir: Path, manifest: dict, zip_path: Path) -> None:
    """One coherent package: manifest, report, and every card it lists."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(out_dir / "manifest.json", arcname="manifest.json")
        archive.write(out_dir / "generation-report.json",
                      arcname="generation-report.json")
        archive.write(REPO / "THIRD_PARTY_NOTICES.md", arcname="THIRD_PARTY_NOTICES.md")
        for license_name in ("CalSans-LICENSE.txt", "DejaVu-LICENSE.txt"):
            archive.write(REPO / "backend/app/assets/fonts" / license_name,
                          arcname=f"licenses/{license_name}")
        for card in manifest["cards"]:
            archive.write(out_dir / card["file"], arcname=card["file"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("all", "single"), default="single")
    parser.add_argument("--un", default="",
                        help="comma-separated UN numbers (scope=single)")
    parser.add_argument("--modalities", default=",".join(MODALITIES),
                        help="comma-separated subset of ADR,RID,ADN,IMDG,ICAO")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--manifest", action="store_true",
                        help="write manifest.json for the generated set")
    parser.add_argument("--zip", type=Path, default=None,
                        help="also package manifest + cards into this zip")
    args = parser.parse_args()

    modalities = [m.strip().upper() for m in args.modalities.split(",") if m.strip()]
    unknown = [m for m in modalities if m not in ADAPTERS]
    if unknown:
        parser.error(f"unknown modalities: {', '.join(unknown)}")
    if args.scope == "single" and not args.un:
        parser.error("--scope single needs --un")

    args.out.mkdir(parents=True, exist_ok=True)
    un_numbers = None if args.scope == "all" else args.un.split(",")
    report = generate(un_numbers, modalities, args.out)
    print(json.dumps({**report["summary"],
                      "not_applicable_modalities": list(report["not_applicable"])},
                     indent=2))
    failures = [r for r in report["results"] if r["status"] == "failed"]
    for row in failures[:20]:
        print(f"  [FAIL] UN{row['un_number']} {row['modality']}: {row['reason']}")
    if len(failures) > 20:
        print(f"  ... and {len(failures) - 20} more failures, see generation-report.json")

    if args.manifest or args.zip:
        manifest = build_manifest(args.out, report)
        print(f"manifest: {manifest['total_cards']} cards, "
              f"{manifest['total_size'] / 1e6:.1f} MB, editions {manifest['editions']}")
        if args.zip:
            build_zip(args.out, manifest, args.zip)
            print(f"package: {args.zip} ({args.zip.stat().st_size / 1e6:.1f} MB)")

    # A partial set must never pass the publishing workflow. Entirely
    # unavailable modalities are recorded separately in all mode.
    return 0 if report["summary"]["generated"] > 0 and not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
