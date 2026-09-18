"""Multi-recipient preparation must survive planning without quantity or privacy drift.

One source goods line deliberately belongs to two receivers. Shipment-level
permissions and reservations cannot distinguish them, which is the defect these
regressions exercise through the real storage and document projection services.
"""
import copy
import json
from datetime import timedelta

import pytest

from test_deliveries import db
from app.core.messages import ApiError
from app.models.delivery import Delivery, DeliveryGrant
from app.models.user import User
from app.schemas.history import ShipmentIn
from app.schemas.deliveries import DeliveryIn, ActionIn
from app.services import history, deliveries as d, shipment_routing as routing


def shipment():
    locations = []
    for pid, kind, name in [("p", "pickup", "Warehouse"), ("a", "delivery", "Alice"), ("b", "delivery", "Bob")]:
        party = dict(name=name, address=f"{name} street 1", country="NL", contact="")
        locations.append(dict(**party, id=pid, kind=kind, party=party))
    return ShipmentIn.model_validate({"lines": [{"cargo_goods_id": 0, "line_id": 1, "include": True, "description": "Bolts", "quantity": 10, "unit": "pcs", "weight_total_kg": 100}],
        "routing": {"locations": locations, "distributions": [dict(id=pid, goods_id="0", quantity=quantity, pickup_id="p", delivery_id=pid) for pid, quantity in [("a", "6"), ("b", "4")]]}})


def planned_source(db):
    user = db.get(User, 1)
    source = history.keep(db, user, shipment())
    return user, source


def delivery(source):
    locations = json.loads(source.export_json)["routing"]["locations"]
    stops = [{k: v for k, v in p.items() if k != "party"} | {"shipment_id": source.id, "location_id": p["id"]} for p in locations]
    return DeliveryIn(name="Two recipients", stops=stops,
        legs=[dict(id="pa", origin_stop_id="p", destination_stop_id="a", carrier="Carrier", max_mass_tonnes="30"), dict(id="ab", origin_stop_id="a", destination_stop_id="b", carrier="Carrier", max_mass_tonnes="30")],
        allocations=[dict(id="a", shipment_id=source.id, goods_id="0", source_distribution_id="a", quantity="6", leg_ids=["pa"], unit_ids=[]), dict(id="b", shipment_id=source.id, goods_id="0", source_distribution_id="b", quantity="4", leg_ids=["pa", "ab"], unit_ids=[])])


def test_exact_distribution_and_incomplete_private_draft(db):
    payload = shipment()
    assert routing.issues(payload) == []
    payload.routing.distributions[0].quantity = d.decimal(5)
    assert "routing.quantities" in routing.issues(payload)
    user = db.get(User, 1)
    saved = history.keep(db, user, payload.model_copy(update={"draft": True}))
    assert saved.is_draft
    with pytest.raises(ApiError) as caught:
        history.keep(db, user, payload, existing=saved)
    assert caught.value.code == "routing.quantities"


def test_finalized_goods_ready_without_document_bundle(db):
    _, source = planned_source(db)
    assert source.work_status == "ready"
    assert history.summary(source).work_status == "ready"
    assert source.bundle_json is None
    exported = json.loads(source.export_json)
    assert exported["format_version"] == "3.0"
    assert len(exported["routing"]["distributions"]) == 2


def test_route_allocation_ends_at_its_own_receiver(db):
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    assert {a["id"] for a in d.selected(value, "ab")} == {"b"}
    broken = delivery(source)
    broken.allocations[0].leg_ids = ["pa", "ab"]
    with pytest.raises(ApiError) as caught:
        d.create(db, user, broken)
    assert caught.value.code == "delivery.itinerary"


def test_distribution_overbooking_cannot_use_other_receiver_balance(db):
    user, source = planned_source(db)
    payload = delivery(source)
    payload.allocations = payload.allocations[:1]
    payload.allocations[0].quantity = d.decimal(4)
    one = d.create(db, user, payload)
    two = d.create(db, user, payload)
    for result in [one]:
        record = db.get(Delivery, result["id"])
        d.action(db, user, record, "pa", ActionIn(version=record.version, action="plan"))
    record = db.get(Delivery, two["id"])
    with pytest.raises(ApiError) as caught:
        d.action(db, user, record, "pa", ActionIn(version=record.version, action="plan"))
    assert caught.value.code == "delivery.overallocated"


def test_address_override_requires_reason_and_records_original(db):
    user, source = planned_source(db)
    payload = delivery(source)
    payload.stops[1].address = "Different street 9"
    with pytest.raises(ApiError) as caught:
        d.create(db, user, payload)
    assert caught.value.code == "routing.override"
    payload.stops[1].override_reason = "Receiver requested alternate entrance"
    result = d.create(db, user, payload)
    stop = result["stops"][1]
    assert stop["original"]["address"] == "Alice street 1"
    assert stop["changes"][0]["actor"] == user.id


def test_recipient_cannot_read_sibling_distribution_or_files(db):
    from app.services.delivery_documents import store
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    record = db.get(Delivery, value["id"])
    db.add(DeliveryGrant(id="grant", delivery_id=record.id, user_id=4, leg_id="pa", role="recipient", shipment_ids_json=json.dumps([source.id]), allocation_ids_json='["a"]', expires_at=d.now() + timedelta(days=1)))
    own = store(db, record, value["legs"][0], [source.id], b"own", "a.pdf", "application/pdf", "proof", allocation_ids=["a"])
    store(db, record, value["legs"][0], [source.id], b"other", "b.pdf", "application/pdf", "proof", allocation_ids=["b"])
    db.commit()
    result = d.view(db, db.get(User, 4), record)
    assert [a["id"] for a in result["allocations"]] == ["a"]
    assert [f["id"] for f in result["files"]] == [own.id]
    assert "Bob" not in json.dumps(result)


def test_documents_cannot_combine_receivers(db):
    from app.services.delivery_documents import payload_for
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    with pytest.raises(ApiError) as caught:
        payload_for(value, value["legs"][0], source.id, "cmr", "en", {"a", "b"})
    assert caught.value.code == "delivery.document_scope"
    doc = payload_for(value, value["legs"][0], source.id, "cmr", "en", {"b"})
    assert doc.values["consignee_name"] == "Bob"
    assert doc.lines[0]["quantity"] == 4
    assert "Bob street" in doc.values["place_of_delivery"]


def test_dangerous_goods_split_requires_new_confirmation():
    payload = shipment()
    payload.lines[0]["dangerous_goods"] = True
    assert "routing.dg" in routing.issues(payload)
    payload.dangerous_goods = [{"line_id": 1, "products": [{"un_number": "1203", "proper_shipping_name": "GASOLINE", "class": "3"}]}]
    assert "routing.dg_split" in routing.issues(payload)
    for allocation in payload.routing.distributions:
        allocation.dangerous_goods = copy.deepcopy(payload.dangerous_goods)
        allocation.dangerous_goods[0]["products"][0].update(quantity_packages=str(allocation.quantity), type_of_package="drum", net_mass_liters_per_package="10 L")
        allocation.dg_confirmation = routing.confirmation(payload, allocation)
    assert routing.issues(payload) == []
    payload.lines[0]["weight_total_kg"] = 120
    assert "routing.dg_split" in routing.issues(payload)


def test_retention_cannot_be_disabled_by_settings_or_environment(db, monkeypatch):
    from app.services import settings_store
    from app.schemas.settings import InstanceSettings
    monkeypatch.setenv("EMCARGO_HISTORY", "false")
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=False))
    assert settings_store.public_settings(db).history_enabled is True


def test_legacy_adapter_does_not_invent_missing_addresses():
    assert routing.legacy({"goods": [{"quantity": 1}]}).distributions == []


def test_closed_box_cannot_cross_address_pairs_or_be_replaced_with_loose_stock(db):
    from app.schemas.cargo import CargoManifest
    from tests.test_cargo import unit, manifest, allocation
    payload = shipment()
    box = unit()
    payload.cargo = CargoManifest.model_validate(manifest([box], [allocation(0, box, 6)]))
    payload.routing.distributions[0].unit_ids = [box["id"]]
    assert routing.issues(payload) == []
    user = db.get(User, 1)
    source = history.keep(db, user, payload)
    request = delivery(source)
    request.allocations[0].quantity = d.decimal(4)
    with pytest.raises(ApiError) as caught:
        d.create(db, user, request)
    assert caught.value.code == "routing.packing"
    payload.routing.distributions[1].unit_ids = [box["id"]]
    assert "routing.packing" in routing.issues(payload)


def test_address_edit_invalidates_dg_split_confirmation():
    payload = shipment()
    payload.dangerous_goods = [{"line_id": 1, "products": [{"un_number": "1203", "proper_shipping_name": "GASOLINE", "class": "3"}]}]
    for item in payload.routing.distributions:
        item.dangerous_goods = copy.deepcopy(payload.dangerous_goods)
        item.dangerous_goods[0]["products"][0].update(quantity_packages=str(item.quantity), type_of_package="drum", net_mass_liters_per_package="10 L")
        item.dg_confirmation = routing.confirmation(payload, item)
    payload.routing.locations[1].address = "New destination"
    assert "routing.dg_split" in routing.issues(payload)


def test_return_documents_use_reverse_parties_even_after_an_intermediate_stop(db):
    from app.services.delivery_documents import payload_for
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    # A return after the second leg only retains that leg's two physical stops.
    value["followup"] = {"kind": "return"}
    value["stops"] = list(reversed(value["stops"][1:]))
    part = {**value["legs"][1], "origin": "Bob street 1", "destination": "Alice street 1"}
    doc = payload_for(value, part, source.id, "cmr", "en", {"b"})
    assert doc.values["consignor_name"] == "Bob"
    assert doc.values["consignee_name"] == "Warehouse"
    assert doc.values["place_of_receipt"] == "Bob street 1"
    assert doc.values["place_of_delivery"] == "Alice street 1"


def test_frozen_address_requires_unplanning(db):
    user, source = planned_source(db)
    result = d.create(db, user, delivery(source))
    record = db.get(Delivery, result["id"])
    d.action(db, user, record, "pa", ActionIn(version=record.version, action="plan"))
    request = delivery(source)
    request.version = record.version
    request.stops[1].address = "Changed entrance"
    request.stops[1].override_reason = "Receiver requested another entrance"
    with pytest.raises(ApiError) as caught:
        d.edit(db, user, record, request)
    assert caught.value.code == "delivery.frozen"


def test_migration_keeps_old_snapshots_and_document_bytes(db):
    from app.core.migrations import _013_shipment_routing
    from app.services.delivery_documents import store
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    record = db.get(Delivery, value["id"])
    evidence = store(db, record, value["legs"][0], [source.id], b"frozen-pdf-bytes", "old.pdf", "application/pdf", "issued", allocation_ids=["a"])
    before = (source.export_json, source.snapshot_json, record.data_json, evidence.content)
    db.commit()
    with db.get_bind().begin() as conn:
        _013_shipment_routing(conn)
    db.expire_all()
    assert (source.export_json, source.snapshot_json, record.data_json, evidence.content) == before


def test_malformed_routed_dg_returns_validation_error():
    payload = shipment()
    payload.dangerous_goods = [{"line_id": 1, "products": ["invalid"]}]
    assert "routing.dg" in routing.issues(payload)


def test_source_dg_review_needs_no_document_and_binds_addresses(db):
    from app.services import dg_review
    payload = shipment()
    payload.routing.distributions = payload.routing.distributions[:1]
    payload.routing.distributions[0].quantity = d.decimal(10)
    payload.dangerous_goods = [{"line_id": 1, "products": [{"un_number": "1203", "proper_shipping_name": "GASOLINE", "class": "3"}]}]
    user = db.get(User, 1)
    review = dg_review.submit(db, user, payload)
    assert payload.bundle is None
    with pytest.raises(ApiError):
        dg_review.enforce_shipment(db, user, payload)
    review.status = "approved"
    review.reviewed_by = "specialist"
    db.commit()
    payload.dg_review_id = review.id
    dg_review.enforce_shipment(db, user, payload)
    payload.routing.locations[1].address = "Changed after review"
    with pytest.raises(ApiError) as caught:
        dg_review.enforce_shipment(db, user, payload)
    assert caught.value.code == "review.required"


def test_document_inputs_are_isolated_per_address_pair(db):
    """A sender instruction for Alice must never appear in Bob's issued document."""
    from app.services.delivery_documents import payload_for
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    part = value["legs"][0]
    part["document_values"] = {
        str(source.id): {"sender_instructions": "Unsafe shipment-wide fallback"},
        "route:" + json.dumps([str(source.id), "p", "a"], separators=(",", ":")): {
            "sender_instructions": "Alice gate code", "consignee_name": "Forged receiver"},
    }
    own = payload_for(value, part, source.id, "cmr", "en", {"a"})
    other = payload_for(value, part, source.id, "cmr", "en", {"b"})
    assert own.values["sender_instructions"] == "Alice gate code"
    assert own.values["consignee_name"] == "Alice"
    assert not other.values.get("sender_instructions")
    assert other.values["consignee_name"] == "Bob"


def test_intermediate_operator_can_receive_only_its_onward_goods(db):
    """Filtering the visible itinerary must not turn an intermediate stop into final delivery."""
    user, source = planned_source(db)
    value = d.create(db, user, delivery(source))
    record = db.get(Delivery, value["id"])
    db.add(DeliveryGrant(id="operator", delivery_id=record.id, user_id=3, leg_id="pa", role="operator", shipment_ids_json=json.dumps([source.id]), allocation_ids_json='["a", "b"]', expires_at=d.now() + timedelta(days=1)))
    db.commit()
    result = d.view(db, db.get(User, 3), record)
    allocations = {a["id"]: a for a in result["allocations"]}
    assert allocations["a"]["receivable_leg_ids"] == []
    assert allocations["b"]["receivable_leg_ids"] == ["pa"]
