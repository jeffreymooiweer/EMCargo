#!/usr/bin/env python3
"""Hash actual source or generated artifact files into a separate CycloneDX BOM."""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    root = args.directory or ROOT
    if args.directory:
        names = [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]
    else:
        names = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    components = []
    for name in sorted(set(names)):
        path = root / name
        if not name or not path.is_file() or path.is_symlink() or path.resolve() == args.out.resolve():
            continue
        components.append({"type": "file", "name": name,
                           "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(path.read_bytes()).hexdigest()}]})
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.6", "version": 1,
           "metadata": {"component": {"type": "application", "name": "EMCargo artifact files"}},
           "components": components}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bom, indent=2) + "\n")
    print(f"Recorded {len(components)} actual files")


if __name__ == "__main__":
    main()
