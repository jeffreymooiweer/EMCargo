"""Office tasks must retain shipment privacy and the real specialist gate.

These HTTP regressions exercise the existing persistence/review routes together
with the overview, rather than manufacturing statuses that could never occur.
"""
from copy import deepcopy

import pytest
from sqlalchemy import event, text

from app.models.shipment import Shipment
from app.models.user import Department, User
from app.schemas.history import ShipmentIn
from app.schemas.settings import InstanceSettings
from app.services import history, settings_store, work_queue
from tests.test_dg_review_permissions import setup, shipment, release  # noqa: F401


def plain(reference="PL-100", due="2026-09-14"):
    data = shipment()
    data["dangerous_goods"] = []
    data["lines"][0]["description"] = "Boxes of bolts"
    data["values"].update(shipment_reference=reference, loading_date=due)
    data["bundle"]["dangerous_goods"] = []
    document = data["bundle"]["documents"][0]
    document.update(dangerous_goods=[], values=deepcopy(data["values"]), lines=deepcopy(data["lines"]))
    data["snapshot"]["docValues"] = deepcopy(data["values"])
    return data


def queue(client, **parameters):
    response = client.get("/api/work", params={"day": "2026-09-14", "bucket": "all", **parameters})
    assert response.status_code == 200, response.text
    return response.json()


def enabled(db):
    settings_store.save_instance_settings(db, InstanceSettings(history_enabled=True))


def test_private_drafts_and_department_counts_use_the_same_scope(setup):
    db, as_role = setup
    enabled(db)
    db.add_all([Department(id=1, name="Factory"), Department(id=2, name="Office")])
    db.get(User, 1).department_id = 1
    db.get(User, 2).department_id = 2
    db.commit()
    private = as_role("user").put("/api/shipments/draft", json=plain("PRIVATE")).json()
    saved = as_role("user").post("/api/shipments", json=plain()).json()
    assert queue(as_role("user"))["total"] == 2
    for role in ("super_user", "dg_specialist", "admin"):
        result = queue(as_role(role))
        assert result["total"] == result["counts"]["today"] == result["counts"]["ready"] == 1
        assert result["items"][0]["id"] == str(saved["id"])
        assert as_role(role).patch(f"/api/work/shipments/{private['id']}", json={"version": 1, "completed": True}).status_code == 404
    db.get(User, 2).role = "user"
    db.commit()
    assert queue(as_role("super_user"))["total"] == 0


def test_loading_dates_search_pagination_and_totals_are_server_side(setup):
    db, as_role = setup
    enabled(db)
    client = as_role("user")
    for reference, due in [("literal_100%", "2026-09-13"), ("literalX100Z", "2026-09-14"), ("undated", "")]:
        response = client.post("/api/shipments", json=plain(reference, due))
        assert response.status_code == 200, response.text
    result = queue(client, per_page=1)
    assert result["total"] == 3 and len(result["items"]) == 1
    assert result["items"][0]["reference"] == "literal_100%"
    assert result["counts"]["today"] == 1 and result["counts"]["attention"] == 1
    assert queue(client, q="_100%")["total"] == 1
    undated = queue(client, q="undated")["items"][0]
    assert undated["due_date"] is None and undated["overdue"] is False
    assert client.get("/api/work?day=bad").status_code == 422


def test_assignment_uses_visible_people_and_rejects_stale_writes(setup):
    db, as_role = setup
    enabled(db)
    client = as_role("user")
    saved = client.post("/api/shipments", json=plain()).json()
    task = queue(client)["items"][0]
    path = f"/api/work/shipments/{saved['id']}"
    assert client.patch(path, json={"version": task["version"], "owner_id": 2}).status_code == 200
    assert queue(client, mine=True)["total"] == 0
    assert queue(as_role("super_user"), mine=True)["total"] == 1
    assert client.patch(path, json={"version": task["version"], "completed": True}).status_code == 409
    db.get(User, 3).active = False
    db.commit()
    assert 3 not in [user["id"] for user in client.get(f"/api/work/people?shipment_id={saved['id']}").json()]
    task = queue(client)["items"][0]
    assert client.patch(path, json={"version": task["version"], "owner_id": 3}).status_code == 422
    assert client.patch(path, json={"version": task["version"], "completed": True}).status_code == 200
    assert queue(client)["total"] == 0
    closed = queue(client, bucket="closed")["items"][0]
    assert closed["completed_at"] and closed["status"] == "ready"
    assert client.patch(path, json={"version": closed["version"], "completed": False}).status_code == 200
    assert queue(client)["total"] == 1


def test_specialist_actions_survive_history_off_and_admin_cannot_approve(setup):
    _, as_role = setup
    client = as_role("user")
    review_id = client.post("/api/dg-reviews", json=shipment()).json()["id"]
    assert queue(client)["items"][0]["status"] == "waiting"
    assert queue(client)["history_enabled"] is False
    assert queue(as_role("super_user"))["total"] == 0
    assert queue(as_role("admin"))["items"][0]["status"] == "waiting"
    assert queue(as_role("dg_specialist"), mine=True)["items"][0]["status"] == "review"
    path = f"/api/dg-reviews/{review_id}/decision"
    assert as_role("admin").post(path, json={"status": "approved"}).status_code == 403
    assert as_role("dg_specialist").post(path, json={"status": "changes_requested", "comment": "Check packaging"}).status_code == 200
    assert queue(as_role("user"))["items"][0]["status"] == "changes"
    assert queue(as_role("dg_specialist"))["total"] == 0
    assert as_role("user").patch("/api/work/shipments/1", json={"version": 0, "completed": True}).status_code == 404


def test_review_replaces_matching_draft_then_kept_shipment_replaces_review(setup):
    db, as_role = setup
    enabled(db)
    data = shipment()
    draft = deepcopy(data)
    draft["bundle"] = None
    assert as_role("user").put("/api/shipments/draft", json=draft).status_code == 200
    review_id = release(as_role, data)
    task = queue(as_role("user"))
    assert task["total"] == 1 and task["items"][0]["status"] == "approved"
    response = as_role("user").post("/api/shipments", json=data)
    assert response.status_code == 200, response.text
    task = queue(as_role("user"))
    assert task["total"] == 1 and task["items"][0]["kind"] == "shipment"
    item = task["items"][0]
    assert as_role("user").delete(f"/api/dg-reviews/{review_id}").status_code == 200
    assert queue(as_role("user"))["items"][0]["status"] == "review_required"
    assert as_role("user").patch(f"/api/work/shipments/{item['id']}", json={"version": item["version"], "completed": True}).status_code == 409


def test_changed_submission_closes_only_the_owners_superseded_task(setup):
    db, as_role = setup
    data = shipment()
    first = as_role("user").post("/api/dg-reviews", json=data).json()["id"]
    as_role("dg_specialist").post(f"/api/dg-reviews/{first}/decision", json={"status": "changes_requested", "comment": "Fix reference"})
    data["values"]["reference"] = "updated"
    data["bundle"]["documents"][0]["values"]["reference"] = "updated"
    data["dg_review_id"] = first
    second = as_role("user").post("/api/dg-reviews", json=data)
    assert second.status_code == 200, second.text
    assert queue(as_role("user"))["total"] == 1
    assert queue(as_role("user"), bucket="closed")["items"][0]["id"] == first
    assert as_role("user").get(f"/api/dg-reviews/{first}").json()["status"] == "changes_requested"


def test_backfill_reads_old_bundle_without_snapshot_lines_and_commits(setup):
    db, as_role = setup
    enabled(db)
    saved = as_role("user").post("/api/shipments", json=plain()).json()
    db.execute(text("UPDATE shipments SET work_version=0, work_status='prepare', work_due_date=NULL"))
    db.commit()
    with db.get_bind().begin() as conn:
        work_queue.backfill(conn)
    db.expire_all()
    record = db.get(Shipment, saved["id"])
    assert record.work_status == "ready" and record.work_due_date == "2026-09-14"
    assert record.work_version == 1 and record.work_owner_id == 1
    statements = []
    def capture(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(db.get_bind(), "before_cursor_execute", capture)
    try:
        assert queue(as_role("user"))["total"] == 1
    finally:
        event.remove(db.get_bind(), "before_cursor_execute", capture)
    assert not any(column in sql for sql in statements for column in ("snapshot_json", "bundle_json", "export_json", "payload_json"))


def test_changed_content_reopens_completed_work_and_deleted_accounts_leave_no_private_draft(setup):
    db, as_role = setup
    enabled(db)
    data = plain()
    record = history.keep(db, db.get(User, 1), ShipmentIn(**data))
    work_queue.change(db, db.get(User, 1), record, version=record.work_version, completed=True)
    data["values"]["shipment_reference"] = "changed"
    history.keep(db, db.get(User, 1), ShipmentIn(**data), existing=record)
    assert record.work_completed_at is None
    draft = as_role("user").put("/api/shipments/draft", json=plain("PRIVATE")).json()
    assert as_role("super_user").delete("/api/users/1").status_code == 200
    db.expire_all()
    assert db.get(Shipment, draft["id"]) is None
    assert db.get(Shipment, record.id).work_owner_id is None


@pytest.mark.parametrize("value", ["2026-09-14T10:30:00", "14-09-2026", "2026-02-30", "yesterday", ""])
def test_only_an_explicit_valid_loading_date_is_a_deadline(value):
    assert work_queue.loading_date({"loading_date": value}) is None
