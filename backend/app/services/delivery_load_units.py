"""A delivery-owned transport unit can contain cargo from several shipments."""
import json
from decimal import Decimal
from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5

from app.core.messages import error
from app.models.cargo import CargoIdentity, CargoUse
from app.models.shipment import Shipment
from app.schemas.cargo import CargoManifest, CargoUnit


def hydrate(db, value):
    for part in value["legs"]:
        uid = part.get("load_unit_id")
        if not uid:
            continue
        identity = db.get(CargoIdentity, uid)
        if not identity or not identity.reusable:
            raise error(404, "equipment.not_found")
        unit = CargoUnit.model_validate(json.loads(identity.unit_json))
        if unit.kind != "ctu" or unit.parent_id or unit.legacy_goods_id is not None:
            raise error(422, "delivery.unpack")
        part["load_unit"] = unit.model_dump(mode="json")


def available(db, value, part):
    from app.services.delivery_inventory import physical_unit_completed
    from app.services import deliveries as d
    unit = part.get("load_unit")
    if not unit:
        return
    source_ids = {a["shipment_id"] for a in d.selected(value, part["id"])}
    for use in db.query(CargoUse).filter_by(unit_id=unit["id"]).all():
        source = db.get(Shipment, use.shipment_id)
        if source and not source.is_draft and source.id not in source_ids and not physical_unit_completed(db, source.id, unit["id"]):
            raise error(409, "cargo.unit_in_use")


def project(cargo, value, part, shipment_id):
    from app.services import deliveries as d
    unit = part.get("load_unit")
    if not unit:
        return cargo
    if cargo is None:
        cargo = CargoManifest(shipment_id=str(uuid5(NAMESPACE_URL, f"delivery-source:{shipment_id}"))).model_dump(mode="json")
    if unit["id"] in {u["id"] for u in cargo["units"]}:
        return cargo
    cargo["units"].append(dict(unit))
    for child in cargo["units"]:
        if child["id"] != unit["id"] and child.get("parent_id") is None:
            child["parent_id"] = unit["id"]
    goods = d.source_goods(value["sources"][str(shipment_id)]["export"])
    quantities = defaultdict(Decimal)
    for allocation in d.selected(value, part["id"]):
        if allocation["shipment_id"] == shipment_id:
            quantities[allocation["goods_id"]] += d.decimal(allocation["quantity"])
    for gid, quantity in quantities.items():
        packed = sum((d.decimal(a["quantity"]) for a in cargo["allocations"] if str(a["goods_id"]) == gid), Decimal(0))
        loose = quantity - packed
        if loose <= 0 or any(str(u.get("legacy_goods_id")) == gid for u in cargo["units"]):
            continue
        numeric_id = goods[gid].get("cargo_goods_id", goods[gid].get("line_id"))
        if type(numeric_id) is not int:
            raise error(422, "cargo.goods_missing")
        cargo["allocations"].append({"id": str(uuid5(NAMESPACE_URL, f"delivery-load:{part['id']}:{shipment_id}:{gid}")), "goods_id": numeric_id, "unit_id": unit["id"], "quantity": float(loose)})
    return cargo
