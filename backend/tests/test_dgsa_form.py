"""The annual report in the DVSA's shape: the form, the pre-fill, the kept
answers, the paper.

Pinned: the history proposes and never asserts (the pre-fill is separate
from the answers, and a class carried by both mass and volume gets no band
from the application); only the form's own keys survive a save, in the
form's shape; a user without a department answers for the unassigned pool
and an administrator for what they choose; the PDF carries the answers, the
counted appendix and the DGSA1–21 checklist with the section each item
lives in; and nothing of this exists without the history.
"""
from __future__ import annotations

import io
from datetime import datetime, timezone

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.core import migrations
from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import create_app
from app.models.user import Department, User
from app.services import dgsa_form, dgsa_report
from app.services.documents.dgsa_report_pdf import render_dgsa_report
from tests.test_dgsa_report import ACETONE, LITHIUM, PETROL, kept


@pytest.fixture
def db(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("CATALOG_AUTO_SYNC", "false")
    monkeypatch.setenv("EMCARGO_HISTORY", "true")
    monkeypatch.setenv("BRAND_NAME", "Mooiweer Logistics")
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(Department(id=1, name="Sales"))
    session.add_all([
        User(id=1, username="root", email="root@example.com", password_hash="x", role="admin"),
        User(id=2, username="ada", email="ada@example.com", password_hash="x", role="user",
             department_id=1),
        User(id=3, username="cyd", email="cyd@example.com", password_hash="x", role="user"),
    ])
    session.commit()
    yield session
    session.close()
    get_settings.cache_clear()


def client_as(db, user_id: int) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: db.get(User, user_id)
    return TestClient(app)


@pytest.fixture
def a_year(db):
    t = lambda m, d: datetime(2026, m, d, 10, 0, tzinfo=timezone.utc)  # noqa: E731
    kept(db, 2, t(1, 5), [PETROL, ACETONE], "S-1")     # class 3 by mass and volume
    kept(db, 1, t(11, 30), [LITHIUM], "N-2")           # class 9, 12 kg
    kept(db, 3, t(3, 3), [PETROL], "C-1")              # nobody's


def text_of(path) -> str:
    with fitz.open(path) as pdf:
        return "\n".join(page.get_text() for page in pdf)


# --- the definition and the pre-fill ---------------------------------------------


def test_the_form_follows_the_template_section_for_section():
    definition = dgsa_form.definition("en")
    assert [s["key"] for s in definition["sections"]] == [
        "company", "adviser", "risk", "summary", "activities", "incidents", "training",
        "hcdg", "transportation", "practices", "class7", "additional", "comments", "prepared"]
    keys = {q["key"] for q in definition["questions"]}
    # The thirteen duties of 1.8.3.3 are all questions, each tied to its checklist line.
    codes = {q.get("checklist") for q in definition["questions"]}
    assert {f"DGSA{n}" for n in range(3, 16)} <= codes
    assert {"accident_reports", "notifications_1_8_5", "risk_rating", "incident_list", "transport_table"} <= keys
    # The English is the template's own wording.
    by_key = {q["key"]: q for q in definition["questions"]}
    assert by_key["identification"]["text"].startswith("Do adequate procedures for compliance")
    assert dgsa_form.definition("de")["checklist"]["items"][2]["text"].startswith("Die Verfahren")
    assert len(definition["checklist"]["items"]) == 21


def test_the_history_proposes_and_does_not_assert(db, a_year):
    report = dgsa_report.build_report(db, db.get(User, 1), 2026, language="en")
    filled = dgsa_form.prefill(report, "Mooiweer Logistics")
    assert filled["company_name"] == "Mooiweer Logistics"
    table = filled["transport_table"]
    # Class 3 was carried by mass and by volume: figures shown, no band chosen.
    assert table["3"]["band"] == "" and table["3"]["quantity_kg"] == 1600.0 and table["3"]["quantity_l"] == 100.0
    # Class 9, 12 kg: under five tonnes.
    assert table["9"]["band"] == "<5"
    assert table["3"]["operations"] == ["consigning"]
    assert filled["method_of_carriage"] == ["package"]
    # Packaged petrol of packing group II is footnote b) in 1.10.3.1.2 — not
    # high consequence — so the pre-fill says no, with nothing to list.
    assert filled["hcdg_carried"] == {"answer": "no", "details": ""}
    assert filled["annual_tonnage"].startswith("1.612 t; 100 L")
    # And none of it is an answer until somebody saves it.
    assert dgsa_form.answers_of(dgsa_form.load(db, 2026, "")) == {}


# --- keeping the answers ----------------------------------------------------------


def test_only_the_forms_keys_survive_a_save_in_the_forms_shape(db, a_year):
    with client_as(db, 1) as root:
        saved = root.put("/api/shipments/report/answers?year=2026", json={"answers": {
            "identification": {"answer": "yes", "details": "Procedure DG-01"},
            "risk_rating": "partially",
            "company_type": ["consignor", "pilot"],
            "incident_list": [{"date": "2026-04-01", "place": "Rotterdam", "description": "Drum dented"}, "junk"],
            "transport_table": {"3": {"operations": ["consigning", "flying"], "band": "5-50", "designs": []},
                                "42": {"operations": ["consigning"]}},
            "hcdg_carried": {"answer": "maybe", "details": "?"},
            "made_up": "x",
        }})
        assert saved.status_code == 200, saved.text
        answers = saved.json()["answers"]
        assert answers["identification"] == {"answer": "yes", "details": "Procedure DG-01"}
        assert answers["risk_rating"] == "partially"
        assert answers["company_type"] == ["consignor"]
        assert answers["incident_list"] == [{"date": "2026-04-01", "place": "Rotterdam", "description": "Drum dented"}]
        assert answers["transport_table"] == {"3": {"operations": ["consigning"], "band": "5-50", "designs": [], "other": ""}}
        assert answers["hcdg_carried"] == {"answer": "", "details": "?"}
        assert "made_up" not in answers

        form = root.get("/api/shipments/report/form?year=2026&language=en").json()
        assert form["answers"]["risk_rating"] == "partially"
        assert form["scope"] == ""
        assert form["saved_at"]
        assert form["prefill"]["company_name"] == "Mooiweer Logistics"
        assert form["report"]["totals"]["shipments"] == 3
        assert form["definition"]["sections"][0]["title"] == "Company details"


def test_a_report_is_kept_per_year_and_scope(db, a_year):
    """Specialists can select an organisation-wide or department report.

    Report creation is no longer available to ordinary department users. The
    scope still names the same stored record for every authorised reviewer.
    """
    db.get(User, 2).role = "dg_specialist"
    db.get(User, 3).role = "dg_specialist"
    db.commit()
    with client_as(db, 1) as root, client_as(db, 2) as ada, client_as(db, 3) as cyd:
        root.put("/api/shipments/report/answers?year=2026", json={"answers": {"executive_summary": "all"}})
        root.put("/api/shipments/report/answers?year=2026&department=1", json={"answers": {"executive_summary": "sales by root"}})
        ada.put("/api/shipments/report/answers?year=2026&department=1", json={"answers": {"executive_summary": "sales by ada"}})
        cyd.put("/api/shipments/report/answers?year=2025&department=none", json={"answers": {"executive_summary": "pool 2025"}})
        assert root.get("/api/shipments/report/form?year=2026&department=1").json()["answers"]["executive_summary"] == "sales by ada"
        assert root.get("/api/shipments/report/form?year=2026").json()["answers"]["executive_summary"] == "all"
        assert cyd.get("/api/shipments/report/form?year=2025&department=none").json()["scope"] == "none"
        assert cyd.get("/api/shipments/report/form?year=2025&department=none").json()["answers"]["executive_summary"] == "pool 2025"
        assert cyd.get("/api/shipments/report/form?year=2026&department=none").json()["answers"] == {}


def test_an_oversized_answer_set_is_refused(db, a_year):
    with client_as(db, 1) as root:
        huge = {f"q{i}": "x" for i in range(10)}
        huge["executive_summary"] = "y" * 8000
        assert root.put("/api/shipments/report/answers?year=2026", json={"answers": huge}).status_code == 200
        assert len(root.get("/api/shipments/report/form?year=2026").json()["answers"]["executive_summary"]) == 8000


# --- the paper --------------------------------------------------------------------


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (200, 60), (0, 0, 120)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_the_pdf_carries_the_answers_the_figures_and_the_checklist(db, a_year):
    report = dgsa_report.build_report(db, db.get(User, 1), 2026, language="en")
    answers = dgsa_form.sanitise({
        "company_name": "Mooiweer Logistics",
        "adviser_full_name": "A. Adviser",
        "risk_rating": "fully",
        "identification": {"answer": "yes", "details": "Procedure DG-01"},
        "security_plan": {"answer": "no", "details": ""},
        "incident_list": [{"date": "2026-04-01", "place": "Rotterdam", "description": "Drum dented, no release"}],
        "transport_table": {"3": {"operations": ["consigning", "loading"], "band": "5-50"}},
        "executive_summary": "No findings of note.",
    })
    path = render_dgsa_report(report, dgsa_form.definition("en"), answers, signature_png=_png(),
                              brand_name="Mooiweer Logistics")
    text = text_of(path)
    for expected in ("DGSA Annual Report", "Company details", "Mooiweer Logistics", "A. Adviser",
                     "Fully Compliant", "Procedure DG-01", "Drum dented, no release",
                     "Consigning, Loading", "5-50", "No findings of note.",
                     "Appendix", "UN", "1203", "Checklist", "DGSA3", "DGSA21",
                     "Practises & procedures", "not answered"):
        assert expected in text, expected
    # The class 7 block is not drawn: nothing of class 7 was carried or answered.
    assert "radiation protection programme" not in text
    # The checklist names where each answered item lives, and what was answered.
    assert "Yes" in text and "No" in text


def test_the_pdf_route_and_the_missing_history(db, a_year, monkeypatch):
    with client_as(db, 1) as root:
        root.put("/api/shipments/report/answers?year=2026", json={"answers": {"executive_summary": "Route test"}})
        response = root.get("/api/shipments/report.pdf?year=2026&language=nl")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.headers["content-disposition"].endswith('emcargo-dgsa-report-2026.pdf"')
        with fitz.open(stream=response.content, filetype="pdf") as pdf:
            text = "\n".join(page.get_text() for page in pdf)
        assert "Route test" in text and "Jaarverslag veiligheidsadviseur" in text
        assert "Mooiweer Logistics" in text  # the brand on every page
    monkeypatch.setenv("EMCARGO_HISTORY", "false")
    get_settings.cache_clear()
    with client_as(db, 1) as root:
        assert root.get("/api/shipments/report/form?year=2026").status_code == 200
        assert root.put("/api/shipments/report/answers?year=2026", json={"answers": {}}).status_code == 200


# --- the schema step --------------------------------------------------------------


def test_step_four_makes_the_table_on_an_older_database(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(64), email VARCHAR(255), "
            "password_hash VARCHAR(255), role VARCHAR(16), active BOOLEAN, created_at DATETIME)")
    migrations.run(engine, fresh=False)
    assert inspect(engine).has_table("dgsa_reports")
    assert migrations.run(engine, fresh=False) == []
