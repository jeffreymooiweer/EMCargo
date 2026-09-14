import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session

from app.api.routes.addresses import router as addresses_router
from app.api.routes.articles import router as articles_router
from app.api.routes.assistant import admin_router as assistant_admin_router
from app.api.routes.assistant import router as assistant_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import router as auth_router
from app.api.routes.branding import admin_router as branding_admin_router
from app.api.routes.branding import public_router as branding_public_router
from app.api.routes.cards import router as cards_router
from app.api.routes.catalog import reference_router
from app.api.routes.catalog_search import router as catalog_search_router
from app.api.routes.units import router as units_router
from app.api.routes.equipment import equipment_router
from app.api.routes.import_files import router as import_files_router
from app.api.routes.dangerous_goods import router as dangerous_goods_router
from app.api.routes.departments import router as departments_router
from app.api.routes.documents import mail_router as documents_mail_router
from app.api.routes.documents import router as documents_router
from app.api.routes.geo import router as geo_router
from app.api.routes.history import router as history_router
from app.api.routes.work_queue import router as work_queue_router
from app.api.routes.document_intake import router as document_intake_router
from app.api.routes.dg_reviews import router as dg_reviews_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.meta import router as meta_router
from app.api.routes.nhm import router as nhm_router
from app.api.routes.settings import public_router as settings_public_router
from app.api.routes.settings import router as settings_router
from app.api.routes.trips import router as trips_router
from app.api.routes.un_cards_admin import router as un_cards_admin_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_history
from app.core.ratelimit import limiter
from app.core.security_checks import apply_security_configuration
from app.core.startup import init_app
from app.services.regulatory_manifest import build_manifest, summary
from app.services.settings_store import history_enabled
from app.version import get_version

logger = logging.getLogger(__name__)

#: Authenticated document work, reference data and shared settings.
WORK_ROUTERS = (
    assistant_router,
    jobs_router,
    dangerous_goods_router,
    documents_router,
    dg_reviews_router,
    work_queue_router,
    document_intake_router,
    geo_router,
    nhm_router,
    reference_router,
    import_files_router,
    catalog_search_router,
    units_router,
    settings_public_router,
)

#: Account services retain their additional administrator checks.
ACCOUNT_ROUTERS = (
    users_router,
    settings_router,
    equipment_router,
    documents_mail_router,
    un_cards_admin_router,
    assistant_admin_router,
    branding_admin_router,
    meta_router,
    # Who did what: written by the account routes, read by an administrator.
    audit_router,
)

#: Retention stays opt-in, with authentication checked before the setting.
HISTORY_ROUTERS = (history_router, departments_router, addresses_router, articles_router,
                   trips_router)


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    # Before anything else: a published signing key is an app that can be used
    # without logging in. One is made and stored for it here — refusing to start
    # left the user with nothing but a dead container.
    apply_security_configuration(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        # Before the first request: the schema, the seeds, the first
        # administrator. Starlette's ``on_event`` did this until v1.191.0 and
        # is gone from Starlette 1.x; a lifespan is the same moment.
        application.state.has_admin = init_app()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    # A wildcard origin never travels with credentials. Starlette answers
    # "*" plus credentials by reflecting whatever origin asked, which is the
    # one combination the CORS specification exists to forbid: any website
    # could then call the API with the visitor's cookie. Named origins keep
    # the cookie; the wildcard gets the anonymous access it stands for.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials="*" not in settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    @app.get("/api/health")
    def health(db: Session = Depends(get_db)):
        return {
            "status": "ok",
            "app": settings.app_name,
            "version": get_version(),
            # Retained for older clients; it can no longer select guest access.
            "mode": "organisation",
            "history": history_enabled(db),
            # Which editions this installation uses, compactly. Whoever reports a
            # bug passes on straight away what their app computes with.
            "regulatory": summary(),
        }

    @app.get("/api/regulatory", dependencies=[Depends(get_current_user)])
    def regulatory():
        """Per rule set: edition, source, validity, errata and checksum."""
        return build_manifest()

    @app.get("/api/setup-status")
    def setup_status():
        return {"has_admin": getattr(app.state, "has_admin", False),
                "mode": "organisation"}

    # Sign-in/recovery, login branding and the optional QR card routes are
    # public. Account-bound API routes always enforce authentication, even
    # when an old deployment still contains EMCARGO_MODE=open.
    app.include_router(auth_router, prefix="/api")
    app.include_router(branding_public_router, prefix="/api")
    for router in (*WORK_ROUTERS, *ACCOUNT_ROUTERS):
        app.include_router(router, prefix="/api")
    for router in HISTORY_ROUTERS:
        app.include_router(router, prefix="/api",
                           dependencies=[Depends(get_current_user), Depends(require_history)])
    app.include_router(cards_router, prefix="/api")

    @app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(get_current_user)])
    def openapi_schema():
        return JSONResponse(app.openapi(), headers={"Cache-Control": "private, no-store"})

    @app.get("/docs", include_in_schema=False, dependencies=[Depends(get_current_user)])
    def api_docs(request: Request):
        root = request.scope.get("root_path", "").rstrip("/")
        return get_swagger_ui_html(openapi_url=f"{root}/openapi.json", title=f"{settings.app_name} API")

    @app.get("/redoc", include_in_schema=False, dependencies=[Depends(get_current_user)])
    def api_reference(request: Request):
        root = request.scope.get("root_path", "").rstrip("/")
        return get_redoc_html(openapi_url=f"{root}/openapi.json", title=f"{settings.app_name} API")

    static_dir = settings.static_dir
    if static_dir.exists():
        app.mount("/assets", StaticFiles(directory=static_dir / "assets"), name="assets")

        static_root = static_dir.resolve()

        @app.get("/{full_path:path}")
        async def spa(full_path: str):
            if full_path.startswith("api/"):
                return JSONResponse({"detail": "Not found"}, status_code=404)
            if full_path:
                candidate = (static_dir / full_path).resolve()
                if candidate.is_file() and candidate.is_relative_to(static_root):
                    headers = {"Cache-Control": "no-store"} if candidate == static_root / "index.html" else None
                    return FileResponse(candidate, headers=headers)
            index = static_dir / "index.html"
            if index.exists():
                # Every post-update navigation must load the entry point that
                # references this release's hashed JavaScript and stylesheets.
                return FileResponse(index, headers={"Cache-Control": "no-store"})
            return JSONResponse({"detail": "Frontend not built"}, status_code=404)

    return app


app = create_app()
