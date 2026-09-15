#!/usr/bin/env python3
"""Require explicit review of every package in an actual distribution SBOM.

License detection is evidence, not a redistribution grant. Approval records
bind a package URL/version and the detected license expression(s) to a channel,
and point to a real, reviewed evidence file. Unknown packages fail publishing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(bom: dict, policy: dict, channel: str, root: Path = ROOT) -> list[str]:
    if bom.get("bomFormat") != "CycloneDX" or not isinstance(bom.get("components"), list) or not bom["components"]:
        return ["Missing or empty CycloneDX component inventory"]
    approved = {record["purl"]: record for record in policy.get("approvals", [])}
    errors = []
    for item in bom["components"]:
        purl = item.get("purl")
        record = approved.get(purl)
        if not record or channel not in record.get("channels", []):
            errors.append(f"Unreviewed {channel} component: {purl or item.get('name', '<unnamed>')}")
            continue
        if item.get("licenses", []) != record.get("detected_licenses"):
            errors.append(f"Changed license metadata requires review: {purl}")
        evidence = record.get("evidence", "")
        path = root / evidence
        if not evidence or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            errors.append(f"Missing review evidence: {purl}")
        if not record.get("obligations") or not record.get("reviewer"):
            errors.append(f"Missing obligations or reviewer: {purl}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sbom", type=Path)
    parser.add_argument("--channel", choices=["source", "image", "native", "cards"], required=True)
    parser.add_argument("--policy", type=Path, default=ROOT / "compliance/package-approvals.json")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(json.loads(args.sbom.read_text()), json.loads(args.policy.read_text()), args.channel)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Cannot read SBOM/review policy: {exc}")
        return 1
    report = {"channel": args.channel, "publication_ready": not errors, "issues": errors}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(f"{args.channel}: {len(errors)} package review issue(s)")
    if args.publish:
        for issue in errors:
            print(issue)
    return int(args.publish and bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
