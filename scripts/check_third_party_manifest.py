#!/usr/bin/env python3
"""Validate recorded rights and stop publishing unresolved third-party content.

This is an evidence/packaging gate, not a legal opinion. Validation can pass
while a publication is blocked: keeping an honest inventory must be possible
before the rights holder has answered the corresponding question.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = {"source", "image", "native", "cards", "regulations"}
STATUSES = {"documented", "project", "unresolved", "retired"}
REQUIRED = {"id", "paths", "version", "source_url", "copyright_holder",
            "license_expression", "rights_status", "redistribution_basis",
            "evidence_reference", "sha256", "distribution_channels",
            "reviewed_at", "reviewer"}


def tracked_assets(root: Path) -> set[str]:
    """Check actual tracked files, not just the manifest's list of known files."""
    names = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    prefixes = ("backend/seed/", "templates/forms/", "frontend/public/",
                "scripts/un_cards/assets/", "backend/app/config/")
    extensions = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico",
                  ".ttf", ".woff", ".woff2", ".otf", ".csv", ".tsv", ".xlsx"}
    return {name for name in names if name and (name.startswith(prefixes)
            or Path(name).suffix.lower() in extensions)}


def expected_channels(name: str) -> set[str]:
    """Minimum packaging routes derived from files, not editable status rows."""
    channels = {"source"}
    if name.startswith(("backend/seed/", "backend/app/config/", "backend/app/assets/", "templates/", "frontend/public/", "licenses/")):
        channels |= {"image", "native"}
    if name.startswith(("backend/seed/dg/", "scripts/un_cards/assets/", "backend/app/assets/fonts/")) or name in {
        "backend/app/config/dg_compliance.json", "backend/app/assets/logo.png", "frontend/public/shipping.png"}:
        channels.add("cards")
    return channels


def validate(root: Path, manifest: dict, publish: str | None = None,
             assets: set[str] | None = None) -> list[str]:
    errors = []
    if manifest.get("schema_version") != 1:
        errors.append("Unsupported third-party manifest schema")
    components = manifest.get("components")
    if not isinstance(components, list):
        return errors + ["components must be an array"]
    owners: dict[str, str] = {}
    identifiers: set[str] = set()
    for component in components:
        if not isinstance(component, dict):
            errors.append("Every component must be an object")
            continue
        identifier = str(component.get("id", "<missing id>"))
        missing = REQUIRED - component.keys()
        if missing:
            errors.append(f"{identifier}: missing {', '.join(sorted(missing))}")
            continue
        if identifier in identifiers:
            errors.append(f"Duplicate component: {identifier}")
        identifiers.add(identifier)
        status = component["rights_status"]
        channels = component["distribution_channels"]
        paths = component["paths"]
        if not isinstance(status, str) or status not in STATUSES:
            errors.append(f"{identifier}: invalid rights status")
            continue
        if not isinstance(channels, list) or not all(isinstance(c, str) for c in channels) or not set(channels) <= CHANNELS:
            errors.append(f"{identifier}: invalid distribution channels")
            channels = []
        if (not isinstance(paths, list) or not all(isinstance(p, str) for p in paths)
                or not isinstance(component["sha256"], dict)):
            errors.append(f"{identifier}: paths and sha256 have invalid types")
            continue
        if set(paths) != set(component["sha256"]):
            errors.append(f"{identifier}: hashes must cover exactly the recorded paths")
        if status in {"documented", "project"}:
            for key in ("license_expression", "redistribution_basis", "evidence_reference"):
                if not component[key]:
                    errors.append(f"{identifier}: documented rights need {key}")
            evidence = component["evidence_reference"]
            if evidence and not str(evidence).startswith("https://"):
                evidence_path = root / str(evidence)
                if not evidence_path.is_file() or not evidence_path.resolve().is_relative_to(root.resolve()):
                    errors.append(f"{identifier}: recorded evidence file is missing")
        if status == "retired" and (paths or channels):
            errors.append(f"{identifier}: retired content cannot have active paths or channels")
        if publish in channels and status not in {"documented", "project"}:
            errors.append(f"{identifier}: {publish} publication blocked ({status}); "
                          f"{component['redistribution_basis']}")
        for name in paths:
            omitted = expected_channels(name) - set(channels)
            if omitted:
                errors.append(f"{identifier}: omitted distribution channels for {name}: {', '.join(sorted(omitted))}")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                errors.append(f"{identifier}: unsafe path {name}")
                continue
            if name in owners:
                errors.append(f"{name}: assigned to both {owners[name]} and {identifier}")
            owners[name] = identifier
            target = root / name
            if not target.is_file() or target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
                errors.append(f"{identifier}: missing or symbolic file {name}")
                continue
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if component["sha256"].get(name) != digest:
                errors.append(f"{identifier}: changed content requires review: {name}")
    for name in sorted((tracked_assets(root) if assets is None else assets) - owners.keys()):
        errors.append(f"Unregistered asset: {name}")
    if publish and not any(publish in c.get("distribution_channels", [])
                           for c in components if isinstance(c, dict)):
        errors.append(f"No content registered for publication channel {publish}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--publish", choices=sorted(CHANNELS))
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    path = args.manifest or args.root / "compliance/third-party-manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        errors = validate(args.root, manifest, args.publish)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        errors = [f"Cannot validate rights inventory: {exc}"]
        manifest = {}
    report = {"publication_channel": args.publish, "passed": not errors,
              "components": len(manifest.get("components", [])), "errors": errors}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for error in errors:
        print(error)
    print(f"Rights inventory: {report['components']} components, {len(errors)} issue(s)")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
