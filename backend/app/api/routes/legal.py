"""Public attribution and the exact distributed ODbL database, without a login."""
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/legal", tags=["legal"])
ROOT = Path(__file__).resolve().parents[4]
FILES = {
    "third-party-notices": ("THIRD_PARTY_NOTICES.md", "text/markdown"),
    "stations": ("backend/seed/locations/stations.json", "application/json"),
    "odbl": ("licenses/ODbL-1.0.txt", "text/plain"),
}


@router.get("/{document}")
def legal_download(document: str):
    if document not in FILES:
        raise HTTPException(404, "Not found")
    name, media_type = FILES[document]
    path = ROOT / name
    if not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type=media_type, filename=path.name)
