"""The export bundle: one archive, and nothing in it silently missing.

"Download all" used to fire one download per document; since v1.130.0 it is
one archive that also carries the UN cards and the instructions in writing
for the journey's regimes. The rules these tests hold to:

* every document in the archive is rendered by the same code path as the
  per-document button — the bundle can never contain a different paper;
* a document that is still incomplete stays out, and the archive says so in
  its README instead of hiding the gap;
* the UN cards come only from the installed store, the instructions only as
  the edition prints them; what is not there is named, never substituted.
"""
import io
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.main import app
from app.services.documents import un_card_store

from test_un_card_store import make_package


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def client():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="test", role="admin", active=True)
    return TestClient(app)


def release():
    app.dependency_overrides.pop(get_current_user, None)


CONSIGNMENT = {
    "consignor_name": "Afzender BV",
    "consignor_address": "Havenweg 1, 3011 Rotterdam, Nederland",
    "consignee_name": "Ontvanger GmbH",
    "consignee_address": "Hafenstrasse 4, 47119 Duisburg, Duitsland",
    "loading_point": "Rotterdam",
    "discharge_point": "Duisburg",
    "freight_payment": "Franco",
    "established_place": "Rotterdam",
    "established_date": "2026-08-15",
    "vehicle_registration": "12-BXG-3",
    "reference": "CP-2026-100",
    "emergency_contact": "+31 10 123 4567",
}

PRODUCT = {
    "un_number": "1203", "proper_shipping_name": "Benzine", "class": "3",
    "classification_code": "F1", "packing_group": "II", "labels": "3",
    "hazard_number": "33", "tunnel_code": "(D/E)", "transport_category": "2",
    "quantity_packages": "4", "type_of_package": "vaten",
    "adr_total_quantity": "800 kg",
}

DG = [{"line_id": "1", "vehicle": "UNIT-1", "products": [PRODUCT]}]
LINES = [{"line_id": 1, "include": True, "description": "Vaten benzine",
          "quantity": 4, "unit": "vat", "weight_total_kg": 800}]


def doc(key, **overrides):
    payload = {"document_key": key, "values": dict(CONSIGNMENT),
               "lines": [dict(line) for line in LINES], "dangerous_goods": DG, "output_language": "nl"}
    payload.update(overrides)
    return payload


def bundle(payload):
    with client() as api:
        response = api.post("/api/documents/export/bundle", json=payload)
    release()
    return response


@pytest.mark.parametrize("lines", [[], [{"description": "Chairs", "quantity": 8}],
                                    [{"description": "Chairs", "quantity": 8, "weight_total_kg": 0}]])
def test_unweighed_cargo_cannot_bypass_the_wizard(lines):
    """The novice could download an empty-weight CMR; enforce this at HTTP too."""
    with client() as api:
        response = api.post("/api/documents/export", json=doc("cmr", lines=lines, dangerous_goods=[]))
    release()
    assert response.status_code == 422
    assert response.json()["detail"]["errors"][0]["code"] == "documents.goods_incomplete"


def names_in(response) -> list[str]:
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        return archive.namelist()


def read_member(response, name) -> bytes:
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        return archive.read(name)


def test_the_bundle_holds_every_document_once(data_dir):
    response = bundle({
        "documents": [doc("cmr"), doc("placarding_sheet")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    assert response.status_code == 200, response.text
    names = names_in(response)
    assert sum(1 for n in names if n.startswith("cmr_")) == 1
    assert sum(1 for n in names if n.startswith("placarding_sheet_")) == 1
    for name in names:
        if name.endswith(".pdf"):
            assert read_member(response, name)[:5] == b"%PDF-"


def test_the_instructions_ride_along_in_the_document_language(data_dir):
    response = bundle({
        "documents": [doc("cmr")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "de",
    })
    names = names_in(response)
    assert "instructions/adr-instructions-de.pdf" in names
    assert read_member(response, "instructions/adr-instructions-de.pdf")[:5] == b"%PDF-"


def test_the_un_cards_come_from_the_installed_store(data_dir, tmp_path):
    package = make_package(tmp_path / "p.zip", cards=(("1203", "ADR"),))
    un_card_store.import_package(package)
    response = bundle({
        "documents": [doc("cmr")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    names = names_in(response)
    assert "un-cards/UN1203_ADR.pdf" in names


def test_without_a_card_set_the_readme_says_so(data_dir):
    response = bundle({
        "documents": [doc("cmr")],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    names = names_in(response)
    assert not any(n.startswith("un-cards/") for n in names)
    assert "README.txt" in names
    assert b"no card set is installed" in read_member(response, "README.txt")


def test_an_incomplete_document_stays_out_and_is_named(data_dir):
    incomplete = doc("cmr", values={})
    response = bundle({
        "documents": [doc("placarding_sheet"), incomplete],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    assert response.status_code == 200, response.text
    names = names_in(response)
    assert not any(n.startswith("cmr_") for n in names)
    assert b"cmr" in read_member(response, "README.txt")


def test_nothing_bundleable_refuses_instead_of_an_empty_archive(data_dir):
    response = bundle({
        "documents": [doc("cmr", values={})],
        "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
    })
    assert response.status_code == 422
    assert bundle({"documents": []}).status_code == 422


def test_without_dangerous_goods_no_cards_and_no_instructions(data_dir):
    response = bundle({
        "documents": [doc("cmr", dangerous_goods=None)],
        "output_language": "nl",
    })
    assert response.status_code == 200, response.text
    names = names_in(response)
    assert not any(n.startswith(("un-cards/", "instructions/")) for n in names)


# --- the same bundle, mailed ------------------------------------------------
#
# Mailing must never become a second way of producing documents. These pin
# that the attachment is the bundle the download produces, that a consignment's
# papers are not kept on the server afterwards, and that a shipment without a
# mail server is told so rather than left wondering.


def mail_bundle(payload, db=None):
    with client() as api:
        response = api.post("/api/documents/export/bundle/mail", json=payload)
    release()
    return response


@pytest.fixture
def mail_server(monkeypatch):
    """A configured mail server, and a record of what was handed to it."""
    from app.api.routes import documents as documents_route
    from app.schemas.settings import InstanceSettings

    sent = {}
    settings = InstanceSettings(
        mail_enabled=True, mail_host="smtp.example.com",
        mail_from="emcargo@example.com")
    monkeypatch.setattr(documents_route, "instance_settings", lambda db: settings)

    def fake_send(config, to, subject, body, attachments=None, html=None):
        sent.update(to=to, subject=subject, body=body,
                    attachments=attachments or [])

    monkeypatch.setattr(documents_route.mail, "send", fake_send)
    return sent


def test_the_mailed_attachment_is_the_bundle_itself(data_dir, mail_server):
    payload = {
        "bundle": {
            "documents": [doc("cmr"), doc("placarding_sheet")],
            "dangerous_goods": DG, "profiles": ["ADR"], "output_language": "nl",
        },
        "to": ["planning@vervoerder.nl"],
        "subject": "",
        "message": "",
    }
    response = mail_bundle(payload)
    assert response.status_code == 200, response.text
    assert response.json()["to"] == ["planning@vervoerder.nl"]

    filename, content, mimetype = mail_server["attachments"][0]
    assert filename.endswith(".zip") and mimetype == "application/zip"
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
    assert sum(1 for n in names if n.startswith("cmr_")) == 1
    assert sum(1 for n in names if n.startswith("placarding_sheet_")) == 1


def test_several_recipients_travel_on_one_message(data_dir, mail_server):
    response = mail_bundle({
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "to": ["vervoerder@example.com", "ontvanger@example.com"],
        "subject": "Zending CP-2026-100", "message": "Bijgaand de papieren.",
    })
    assert response.status_code == 200, response.text
    assert mail_server["to"] == ["vervoerder@example.com", "ontvanger@example.com"]
    assert mail_server["subject"] == "Zending CP-2026-100"
    # What the sender wrote is the message; the standard sentence steps
    # aside. Their name is added below it, because the reader — a carrier or
    # a consignee — has to know who sent them a consignment's papers.
    assert "Bijgaand de papieren." in mail_server["body"]
    assert "test" in mail_server["body"]


def test_without_a_subject_or_message_both_are_written_for_you(data_dir, mail_server):
    mail_bundle({
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "to": ["vervoerder@example.com"], "subject": "", "message": "",
    })
    # Written for them, in the language the documents themselves carry.
    assert mail_server["subject"].startswith("Vervoerdocumenten")
    # Named, not anonymous: the recipient has to know who sent them papers.
    assert "test" in mail_server["body"]


def test_the_archive_is_not_left_behind_on_the_server(data_dir, mail_server,
                                                      tmp_path, monkeypatch):
    """A download hands the file to the browser and deletes it afterwards; a
    mailed bundle has no such moment, so it has to be deleted on the way out.
    Consignment papers are not EMCargo's to keep."""
    import tempfile

    scratch = tmp_path / "scratch"
    scratch.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(scratch))
    mail_bundle({
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "to": ["vervoerder@example.com"], "subject": "", "message": "",
    })
    assert mail_server["attachments"], "nothing was sent, so nothing is proven"
    assert list(scratch.iterdir()) == []


def test_a_bad_address_is_refused_before_anything_is_rendered(data_dir, mail_server):
    response = mail_bundle({
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "to": ["smtp.example.com"], "subject": "", "message": "",
    })
    assert response.status_code == 422
    assert not mail_server


def test_without_a_mail_server_the_answer_says_where_to_set_one(data_dir, monkeypatch):
    from app.api.routes import documents as documents_route
    from app.schemas.settings import InstanceSettings

    monkeypatch.setattr(documents_route, "instance_settings",
                        lambda db: InstanceSettings())
    response = mail_bundle({
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "to": ["vervoerder@example.com"], "subject": "", "message": "",
    })
    assert response.status_code == 400
    assert "Mail server" in response.json()["detail"]


def test_a_refusal_from_the_mail_server_is_passed_on(data_dir, monkeypatch):
    from app.api.routes import documents as documents_route
    from app.schemas.settings import InstanceSettings

    monkeypatch.setattr(
        documents_route, "instance_settings",
        lambda db: InstanceSettings(mail_enabled=True, mail_host="smtp.example.com",
                                    mail_from="emcargo@example.com"))

    def refusing(*args, **kwargs):
        raise documents_route.mail.MailError("Could not reach smtp.example.com:587")

    monkeypatch.setattr(documents_route.mail, "send", refusing)
    response = mail_bundle({
        "bundle": {"documents": [doc("cmr")], "dangerous_goods": DG,
                   "profiles": ["ADR"], "output_language": "nl"},
        "to": ["vervoerder@example.com"], "subject": "", "message": "",
    })
    assert response.status_code == 400
    assert "smtp.example.com:587" in response.json()["detail"]


# These fixtures exercise document/retention behaviour with optional review off.
pytestmark = pytest.mark.usefixtures("dg_review_disabled", "synthetic_templates")
