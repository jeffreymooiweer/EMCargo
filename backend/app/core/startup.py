import json
import logging
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.auth import PasswordResetToken
from app.models.two_factor import (
    TwoFactorCode,
    TwoFactorEnrolment,
    TwoFactorRecoveryCode,
)
from app.models.settings import InstanceSetting, UserPreference
from app.models.address import Address
from app.models.article import Article
from app.models.audit import AuditEvent
from app.models.dgsa_report import DgsaReport
from app.models.dg_review import DgReview
from app.models.shipment import Shipment
from app.models.trip import Trip
from app.models.user import Equipment, Job, Profile, ReferenceItem, User
from app.services import audit, history
from app.services.catalog_sync import sync_catalogs
from app.services.settings_store import instance_settings

logger = logging.getLogger(__name__)

TEMPORARY_EXPORT_SUFFIXES = {".pdf", ".zip", ".xlsx", ".tmp"}

#: ``Base.metadata.create_all`` only creates the tables whose model class has
#: actually been imported. The settings models are used nowhere else in this
#: module, so naming them here is what keeps the import — and with it the
#: tables — from quietly disappearing. Without it the app starts fine and the
#: settings screen fails on "no such table: user_preferences".
#: The reset tokens are here for the same reason: nothing else in the
#: start-up path imports them, and a missing table would only show up when
#: somebody actually forgets their password.
SETTINGS_TABLES = (InstanceSetting, UserPreference, PasswordResetToken,
                   TwoFactorEnrolment, TwoFactorRecoveryCode, TwoFactorCode,
                   AuditEvent, DgReview)
#: Same reason: the history's table is created by ``create_all`` on a fresh
#: database only because its model was imported here.
HISTORY_TABLES = (Shipment, Address, DgsaReport, Article, Trip)


def ensure_directories() -> None:
    settings = get_settings()
    for path in [settings.data_dir, settings.templates_dir, settings.exports_dir, settings.logs_dir]:
        path.mkdir(parents=True, exist_ok=True)


def purge_export_files(exports_dir: Path) -> int:
    """Remove known generated artifacts left behind by interrupted downloads."""
    if not exports_dir.exists():
        return 0

    removed_files = 0
    for path in exports_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in TEMPORARY_EXPORT_SUFFIXES:
            continue
        try:
            path.unlink()
            removed_files += 1
        except OSError as exc:
            logger.warning("Could not delete export file %s: %s", path, exc)
    return removed_files


def purge_sensitive_data(db: Session) -> None:
    """Remove stored document data: jobs in the database and temporary exports."""
    settings = get_settings()
    deleted_jobs = db.query(Job).delete()
    db.commit()
    removed_files = purge_export_files(settings.exports_dir)
    if deleted_jobs or removed_files:
        logger.info("Purged sensitive data: %s jobs, %s export files", deleted_jobs, removed_files)


def purge_legacy_equipment(db: Session) -> None:
    """Remove pre-seeded operational equipment data (privacy)."""
    deleted = db.query(Equipment).filter(Equipment.source == "overzicht_materieel").delete()
    db.commit()
    if deleted:
        logger.info("Removed legacy seeded equipment (%s items)", deleted)


def migrate_equipment_columns(db: Session) -> None:
    """Bring an existing equipment table in line with the model.

    ``create_all`` creates missing *tables* and never touches the columns of
    one that already exists, so a library filled before v1.116.0 would keep
    its SAP material number and miss the wall thickness that replaced it.
    Both steps are done here, and both are safe to run on every start: the
    column is only added when absent, and the old one only dropped when
    present. A SQLite too old for DROP COLUMN keeps the dead column — it is
    nullable, so nothing breaks; it is simply no longer read or written.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.get_bind())
    if "equipment_items" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("equipment_items")}

    if "wall_thickness_mm" not in columns:
        db.execute(text("ALTER TABLE equipment_items ADD COLUMN wall_thickness_mm FLOAT"))
        db.commit()
        logger.info("Equipment library: added the wall thickness column")

    if "sap_code" in columns:
        try:
            db.execute(text("ALTER TABLE equipment_items DROP COLUMN sap_code"))
            db.commit()
            logger.info("Equipment library: dropped the retired SAP code column")
        except Exception as exc:  # pragma: no cover - old SQLite without DROP COLUMN
            db.rollback()
            logger.warning("Could not drop the retired SAP code column: %s", exc)


def seed_catalogs(db: Session) -> None:
    settings = get_settings()
    # Bundled additions also reach existing installations with online sync off.
    # An upgrade never overwrites an installation's own edits or disabled rows.
    from app.services.catalog_sync.materials import load_seed_material_records, upsert_materials

    upsert_materials(db, load_seed_material_records(settings.seed_dir / "materials.json"), only_missing=True)
    if db.query(Profile).count() == 0:
        for item in json.loads((settings.seed_dir / "profiles.json").read_text(encoding="utf-8")):
            db.add(
                Profile(
                    profile_type=item["profile_type"],
                    size_label=item["size_label"],
                    kg_per_meter=item["kg_per_meter"],
                    material=item.get("material", "steel"),
                    standard=item.get("standard"),
                    aliases_json=json.dumps(item.get("aliases", [])),
                    source=item.get("source"),
                    notes=item.get("notes"),
                )
            )
    if db.query(ReferenceItem).count() == 0:
        for item in json.loads((settings.seed_dir / "reference_items.json").read_text(encoding="utf-8")):
            db.add(
                ReferenceItem(
                    canonical_name=item["canonical_name"],
                    category=item.get("category", "electrical"),
                    reference_weight_kg=item["reference_weight_kg"],
                    reference_volume_m3=item.get("reference_volume_m3"),
                    aliases_json=json.dumps(item.get("aliases", [])),
                    language_labels_json=json.dumps(item.get("language_labels", {})),
                    notes=item.get("notes"),
                )
            )
    db.commit()


def sync_catalogs_on_startup(db: Session) -> None:
    # The administrator setting wins over CATALOG_AUTO_SYNC, and falls back to
    # it when nothing has ever been saved. Startup is the only moment this is
    # read, so a change takes effect on the next restart — which is what the
    # settings screen says.
    if not instance_settings(db).catalog_auto_sync:
        logger.info("Catalog auto-sync disabled by settings")
        return
    try:
        sync_catalogs(db)
    except Exception:
        logger.exception("Catalog sync failed during startup")


def bootstrap_admin(db: Session) -> bool:
    settings = get_settings()
    admin = db.query(User).filter(User.role == "admin").first()
    if admin:
        return True
    if settings.admin_username and settings.admin_email and settings.admin_password:
        db.add(
            User(
                username=settings.admin_username,
                email=settings.admin_email,
                password_hash=hash_password(settings.admin_password),
                role="admin",
                active=True,
            )
        )
        db.commit()
        logger.info("Bootstrap admin created: %s", settings.admin_username)
        return True
    logger.warning("No admin exists and ADMIN_* env vars are not set")
    return False


def init_app() -> bool:
    ensure_directories()
    # A database with no tables at all is fresh: create_all makes every table
    # in its current shape and the schema steps are stamped rather than run.
    # Anything else is an upgrade, and the steps bring it up to date.
    fresh = not inspect(engine).has_table(User.__tablename__)
    Base.metadata.create_all(bind=engine)
    migrations.run(engine, fresh=fresh)
    db = SessionLocal()
    try:
        # Before anything reads the equipment table: an existing one predates
        # the model it is queried with.
        migrate_equipment_columns(db)
        # Shipments the setting does not cover: switch it on, never hide them.
        history.adopt_kept_data(db)
        seed_catalogs(db)
        purge_legacy_equipment(db)
        # The audit log keeps as long as an administrator said, and no longer.
        audit.prune(db, instance_settings(db).audit_retention_days)
        sync_catalogs_on_startup(db)
        purge_sensitive_data(db)
        return bootstrap_admin(db)
    finally:
        db.close()
