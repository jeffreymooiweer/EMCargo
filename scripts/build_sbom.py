#!/usr/bin/env python3
"""Inventory installed Python distributions and copy their actual license files.

Run this with the clean runtime interpreter, not the test environment. Source
assets are recorded separately from installed packages; an environment snapshot
does not pretend to be the SBOM of a container's operating system.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as metadata
import json
import re
from pathlib import Path
from urllib.parse import quote


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--licenses", type=Path, required=True)
    args = parser.parse_args()
    args.licenses.mkdir(parents=True, exist_ok=True)
    components = []
    for dist in sorted(metadata.distributions(), key=lambda d: d.metadata["Name"].lower()):
        name, version = dist.metadata["Name"], dist.version
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", f"{name}-{version}")
        copied = []
        for file in dist.files or []:
            if re.search(r"(?:^|/)(?:licen[cs]es?|copying|notice|copyright)(?:[./_-]|$)", str(file), re.I):
                path = dist.locate_file(file)
                if path.is_file():
                    content = path.read_bytes()
                    digest = hashlib.sha256(content).hexdigest()
                    target = args.licenses / safe / f"{digest[:12]}-{path.name}"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(content)
                    copied.append(str(target.relative_to(args.licenses)))
        expression = dist.metadata.get("License-Expression")
        declared = dist.metadata.get("License") or "NOASSERTION"
        components.append({"type": "library", "name": name, "version": version,
                           "purl": f"pkg:pypi/{quote(name.lower())}@{quote(version)}",
                           "licenses": [{"expression": expression}] if expression else [{"license": {"name": declared}}],
                           "properties": [{"name": "emcargo:license-files", "value": json.dumps(copied)},
                                          {"name": "emcargo:requires-dist", "value": json.dumps(dist.requires or [])}]})
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
           "metadata": {"component": {"type": "application", "name": "EMCargo Python runtime environment"}},
           "components": components}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bom, indent=2) + "\n")
    print(f"Recorded {len(components)} installed distributions and their available license files")


if __name__ == "__main__":
    main()
