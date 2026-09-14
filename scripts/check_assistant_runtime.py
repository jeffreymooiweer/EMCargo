"""Start the pinned model server inside the built container, without weights.

Unit tests cannot detect absent system libraries or archive SONAME links.
Downloading only the verified server (about 16 MB) exercises the production
installer and dynamic loader without putting a model or test data in the image.
"""
from pathlib import Path
import os
import subprocess
import tempfile

from app.services.assistant import runtime


def main() -> None:
    languages = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, check=True, timeout=10)
    assert {"nld", "eng", "deu", "fra"}.issubset(set(languages.stdout.splitlines()))
    pin = runtime.sources()["server"][runtime._arch()]
    with tempfile.TemporaryDirectory(prefix="assistant-runtime-") as folder:
        server = runtime.install_server(pin, Path(folder))
        subprocess.run(
            [str(server), "--version"], check=True, timeout=30,
            env={**os.environ, "LD_LIBRARY_PATH": str(server.parent)},
        )


if __name__ == "__main__":
    main()
