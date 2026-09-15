"""Preserve compatible templates from an existing native release directory."""
from pathlib import Path
import argparse
import os
from app.services.document_templates import profiles, retain_legacy


def migrate(old: Path) -> None:
    for key, profile in profiles().items():
        base = "templates/forms" if profile["kind"] == "form" else "backend/seed/models"
        path = old / base / profile["filename"]
        if path.is_file() and not path.is_symlink():
            retain_legacy(key, path.read_bytes(), f"Previous local release: {old.name}/{base}/{path.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_release", type=Path)
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.env_file and args.env_file.is_file():
        # Parse only the needed setting, without executing a shell file or
        # logging credentials. The service environment is authoritative.
        from dotenv import dotenv_values
        configured = dotenv_values(args.env_file).get("DATA_DIR")
        if configured:
            os.environ["DATA_DIR"] = configured
    migrate(args.old_release.resolve())
