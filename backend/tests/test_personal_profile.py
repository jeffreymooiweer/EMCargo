"""A self-service profile must not become an account-administration endpoint.

Real route and database tests keep ownership, field limits, private contact
details and upgrades covered together. Old installations must gain profiles
without replacing accounts, and reused IDs must not inherit deleted details.
"""
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.deps import get_current_user
from app.models.audit import AuditEvent
from app.models.user import User, UserProfile
from app.schemas.users import UserOut
from tests.test_avatars import setup  # Shared real users router and isolated SQLite.


DETAILS = {"display_name": "  Ada L.  ", "first_name": "Ada", "last_name": "Lovelace",
           "job_title": "Planner", "phone_number": "+31 20 123 4567"}


def test_profile_is_persistent_and_only_contact_fields_are_private(setup):
    client, db, acting, _ = setup
    assert set(client.get("/api/users/me/profile").json().values()) == {""}
    saved = client.put("/api/users/me/profile", json=DETAILS)
    assert saved.status_code == 200, saved.text
    assert saved.json()["display_name"] == "Ada L."
    assert "phone_number" not in saved.json()
    db.expire_all()
    assert client.get("/api/users/me/profile").json() == {**DETAILS, "display_name": "Ada L."}
    assert db.get(User, 2).username == "person2"
    assert db.get(User, 2).password_hash == "unused"
    assert db.get(User, 2).role == "user"
    assert all("123 4567" not in event.summary for event in db.query(AuditEvent).all())
    acting["id"] = 3
    assert client.get("/api/users/me/profile").json()["display_name"] == ""
    assert client.get("/api/users/2/profile").status_code == 404
    acting["id"] = 1
    other = next(user for user in client.get("/api/users").json() if user["id"] == 2)
    assert other["display_name"] == "Ada L."
    assert not {"first_name", "last_name", "job_title", "phone_number"}.intersection(other)


@pytest.mark.parametrize("field,value", [("user_id", 1), ("role", "admin"), ("email", "changed@example.com"),
                                        ("password_hash", "replaced"), ("display_name", "x" * 81),
                                        ("phone_number", "x" * 41), ("job_title", "x" * 121)])
def test_rejects_privilege_changes_and_unbounded_fields_without_mutation(setup, field, value):
    client, db, _, _ = setup
    assert client.put("/api/users/me/profile", json={field: value}).status_code == 422
    assert db.get(UserProfile, 2) is None
    assert db.get(User, 2).role == "user"


def test_clearing_display_name_uses_full_name_and_deletion_removes_details(setup):
    client, db, acting, _ = setup
    assert client.put("/api/users/me/profile", json={**DETAILS, "display_name": " "}).json()["display_name"] == "Ada Lovelace"
    assert client.put("/api/users/me/profile", json={}).json()["display_name"] == ""
    client.put("/api/users/me/profile", json=DETAILS)
    acting["id"] = 1
    assert client.delete("/api/users/2").status_code == 200
    assert db.get(UserProfile, 2) is None
    db.add(User(id=2, username="replacement", email="replacement@example.com", password_hash="unused"))
    db.commit()
    assert db.get(User, 2).display_name == ""


def test_anonymous_profile_reads_and_writes_require_a_session(setup):
    client, _, _, app = setup
    app.dependency_overrides.pop(get_current_user)
    assert client.get("/api/users/me/profile").status_code == 401
    assert client.put("/api/users/me/profile", json=DETAILS).status_code == 401


def test_create_all_upgrades_existing_accounts_without_column_changes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    UserProfile.__table__.drop(engine)
    with engine.begin() as connection:
        connection.execute(User.__table__.insert().values(id=5, username="existing", email="existing@example.com", password_hash="unchanged", role="user", active=True))
    old_columns = inspect(engine).get_columns("users")
    Base.metadata.create_all(engine)
    assert inspect(engine).has_table("user_profiles")
    assert [column["name"] for column in inspect(engine).get_columns("users")] == [column["name"] for column in old_columns]
    with sessionmaker(bind=engine)() as db:
        user = db.get(User, 5)
        assert user.password_hash == "unchanged"
        assert UserOut.model_validate(user).display_name == ""
    engine.dispose()
