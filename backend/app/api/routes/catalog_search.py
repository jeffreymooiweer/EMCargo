from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.catalog_search import search_catalog
from app.services.density_references import list_density_references

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/densities")
def catalog_densities(
    q: str = Query("", max_length=200),
    offset: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    language: str = Query("nl", max_length=10),
    category: str = Query("", max_length=40),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_density_references(db, q, offset=offset, limit=limit, language=language, category=category)


@router.get("/search")
def catalog_search(
    q: str = Query("", min_length=0, max_length=200),
    limit: int = Query(25, ge=1, le=50),
    # The suggestion the user clicks becomes the description on their document;
    # it belongs in the language they are working in.
    language: str = Query("nl", max_length=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"results": search_catalog(db, q, limit=limit, language=language)}
