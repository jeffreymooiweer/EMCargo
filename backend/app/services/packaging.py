"""Small reusable packaging catalogue; ad-hoc shipment units need no master row."""
import json
from uuid import uuid4

from sqlalchemy.orm import Session
from app.core.messages import error
from app.models.cargo import PackagingTemplate
from app.schemas.cargo import PackagingTemplateIn

_LABELS = {
    "box": ("Doos", "Box", "Karton", "Carton"),
    "crate": ("Krat", "Crate", "Kiste", "Caisse"),
    "case": ("Kist", "Case", "Transportkiste", "Coffre"),
    "bag": ("Zak", "Bag", "Sack", "Sac"),
    "big_bag": ("Bigbag", "Big bag", "Bigbag", "Grand sac"),
    "drum": ("Vat", "Drum", "Fass", "Fût"),
    "jerrycan": ("Jerrycan", "Jerrycan", "Kanister", "Jerrican"),
    "ibc": ("IBC", "IBC", "IBC", "IBC"),
    "bundle": ("Bundel", "Bundle", "Bündel", "Fardeau"),
    "roll": ("Rol", "Roll", "Rolle", "Rouleau"),
    "reel": ("Haspel", "Reel", "Kabeltrommel", "Touret"),
    "pallet": ("Pallet", "Pallet", "Palette", "Palette"),
    "euro_pallet": ("Europallet", "Euro pallet", "Europalette", "Palette Europe"),
    "roll_cage": ("Rolcontainer", "Roll cage", "Rollbehälter", "Roll-conteneur"),
    "stillage": ("Transportbok", "Stillage", "Transportgestell", "Châssis de transport"),
    "mesh_box": ("Gaasbox", "Mesh box", "Gitterbox", "Caisse grillagée"),
    "custom": ("Eigen verpakking", "Custom packaging", "Eigene Verpackung", "Emballage personnalisé"),
}


def builtins() -> list[dict]:
    templates = []
    for category, names in _LABELS.items():
        properties = PackagingTemplateIn(name=names[1], category="pallet" if category == "euro_pallet" else category,
                                         language_labels=dict(zip(("nl", "en", "de", "fr"), names)),
                                         reusable=category in {"pallet", "euro_pallet", "roll_cage", "stillage", "mesh_box"})
        data = properties.model_dump(mode="json")
        if category == "euro_pallet":
            data["dimensions_mm"] = {"length": 1200, "width": 800, "height": 144}
        templates.append({**data, "id": f"builtin-{category}", "version": 1, "builtin": True})
    return templates


def serialize(record: PackagingTemplate) -> dict:
    return {**json.loads(record.data_json), "id": record.id, "name": record.name,
            "active": record.active, "version": record.version, "builtin": False}


def list_templates(db: Session, active_only: bool = True) -> list[dict]:
    query = db.query(PackagingTemplate)
    if active_only:
        query = query.filter(PackagingTemplate.active.is_(True))
    return builtins() + [serialize(record) for record in query.order_by(PackagingTemplate.name, PackagingTemplate.id)]


def save(db: Session, payload: PackagingTemplateIn, template_id: str | None = None) -> dict:
    values = payload.model_dump(mode="json", exclude={"version"})
    if template_id is None:
        record = PackagingTemplate(id=str(uuid4()), name=payload.name, active=payload.active,
                                   data_json=json.dumps(values), version=1)
        db.add(record)
    else:
        record = db.get(PackagingTemplate, template_id)
        if record is None:
            raise error(404, "cargo.template_missing")
        changed = db.query(PackagingTemplate).filter_by(id=template_id, version=payload.version).update(
            {"name": payload.name, "active": payload.active, "data_json": json.dumps(values),
             "version": PackagingTemplate.version + 1}, synchronize_session=False)
        if not changed:
            raise error(409, "cargo.conflict")
    db.commit()
    db.refresh(record)
    return serialize(record)
