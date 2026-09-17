"""Authenticated QR card lookup and its limits.

The real-session regression tests live in test_authenticated_installation.
These focused tests use a signed-in account to pin each card-store promise:

* it is **closed until an administrator opens it**, and closed means invisible;
* it answers about **UN numbers only** — there is no consignment to look up, so
  there is nothing about a shipment that could leak through it;
* it **never substitutes a card from another modality**, because the regimes
  print different obligations and a card answering for the wrong one is worse
  than no card;
* it **reports what is missing** rather than handing back a shorter list;
* it is **bounded**: a capped number of UN numbers, and a rate limit.

And the printing half: a code is only put on paper when it will still work when
the paper is read, which needs both the switch and an address.
"""

import pytest

from tests import route_table
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.deps import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.settings import InstanceSettings
from app.services import settings_store


@pytest.fixture
def data(tmp_path, monkeypatch):
    """A fresh installation: its own database and its own card store."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{data_dir / 'test.db'}")
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    get_settings.cache_clear()

    engine = create_engine(f"sqlite:///{data_dir / 'test.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session, data_dir
    session.close()
    get_settings.cache_clear()


@pytest.fixture
def db(data):
    return data[0]


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, username="card-reader", email="reader@example.com", role="user", active=True)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def open_the_door(db, **extra):
    settings_store.save_instance_settings(
        db, InstanceSettings(card_links_enabled=True, **extra))


def install_card(data_dir, un, modality):
    """One card in the store, with enough of a PDF to be served as one."""
    directory = data_dir / "un-cards" / modality
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"UN{un}_{modality}.pdf"
    path.write_bytes(b"%PDF-1.4\n% a card\n")
    return path


# --- closed until somebody opens it ---


def test_the_door_is_shut_on_a_fresh_installation(client):
    """Signing in alone does not enable the administrator's disabled feature."""
    assert client.get("/api/cards/lookup?un=1263").status_code == 404
    assert client.get("/api/cards/1263/ADR.pdf").status_code == 404


def test_a_shut_door_does_not_announce_itself(client, data):
    """404 rather than 403, even with the card sitting right there.

    A disabled feature stays unavailable even to an authenticated account.
    """
    install_card(data[1], "1263", "ADR")
    response = client.get("/api/cards/1263/ADR.pdf")
    assert response.status_code == 404
    assert "1263" not in response.text


def test_it_answers_once_an_administrator_turns_it_on(client, db, data):
    install_card(data[1], "1263", "ADR")
    open_the_door(db)
    body = client.get("/api/cards/lookup?un=1263").json()
    assert body == {"modality": "ADR",
                    "cards": [{"un_number": "1263", "available": True}]}


# --- what it will and will not say ---


def test_a_missing_card_is_reported_missing_and_not_left_out(client, db, data):
    """The failure this exists to prevent: a shorter list read as a complete one.

    Somebody standing at a vehicle counting cards against the document needs to
    be told that one is absent. Omitting it looks exactly like a document with
    fewer substances on it.
    """
    install_card(data[1], "1263", "ADR")
    open_the_door(db)
    body = client.get("/api/cards/lookup?un=1263,1203").json()
    assert body["cards"] == [
        {"un_number": "1263", "available": True},
        {"un_number": "1203", "available": False},
    ]


def test_a_card_is_never_borrowed_from_another_modality(client, db, data):
    """The road card exists; the sea card is asked for. The regimes are not
    interchangeable — IMDG prints segregation and an EmS number that ADR has
    no equivalent of — so this is absent, not approximately right."""
    install_card(data[1], "1263", "ADR")
    open_the_door(db)
    body = client.get("/api/cards/lookup?un=1263&modality=IMDG").json()
    assert body == {"modality": "IMDG",
                    "cards": [{"un_number": "1263", "available": False}]}
    assert client.get("/api/cards/1263/IMDG.pdf").status_code == 404


def test_an_unknown_modality_is_refused_rather_than_guessed(client, db):
    open_the_door(db)
    assert client.get("/api/cards/lookup?un=1263&modality=ADR-2025") \
        .status_code == 400


def test_it_says_nothing_about_a_consignment(client, db, data):
    """There is no shipment in the request and none in the answer.

    The link addresses UN numbers, which the document that carries it already
    prints in plain text and larger. That is the whole reason this may be
    public, and the whole reason nothing here needs to expire.
    """
    install_card(data[1], "1263", "ADR")
    open_the_door(db)
    body = client.get("/api/cards/lookup?un=1263").json()
    assert set(body) == {"modality", "cards"}
    assert set(body["cards"][0]) == {"un_number", "available"}


# --- bounded ---


def test_the_number_of_un_numbers_one_link_may_ask_about_is_capped(client, db):
    """A transport document does not carry fifty. A cap keeps a public route
    from being turned into a bulk reader of the whole store."""
    from app.api.routes.cards import MAX_NUMBERS

    open_the_door(db)
    asked = ",".join(f"{1000 + i}" for i in range(MAX_NUMBERS + 15))
    body = client.get(f"/api/cards/lookup?un={asked}").json()
    assert len(body["cards"]) == MAX_NUMBERS


def test_rubbish_in_the_parameter_is_dropped_not_echoed(client, db):
    """Only four-digit numbers survive, so nothing a caller writes into the
    query string comes back out of it."""
    open_the_door(db)
    body = client.get("/api/cards/lookup?un=UN1263,<script>,12,abcd").json()
    assert [c["un_number"] for c in body["cards"]] == ["1263"]


def test_the_same_number_twice_is_one_line(client, db):
    open_the_door(db)
    body = client.get("/api/cards/lookup?un=1263,1263,UN 1263").json()
    assert [c["un_number"] for c in body["cards"]] == ["1263"]


def test_the_file_route_serves_only_from_the_store(client, db, data):
    """The path is a UN number, not a filename. Traversal has nowhere to go."""
    install_card(data[1], "1263", "ADR")
    open_the_door(db)
    assert client.get("/api/cards/1263/ADR.pdf").status_code == 200
    for attempt in ("..%2f..%2fetc%2fpasswd", "12634", "abc"):
        assert client.get(f"/api/cards/{attempt}/ADR.pdf").status_code == 404


def test_a_served_card_is_the_file_that_was_installed(client, db, data):
    path = install_card(data[1], "1263", "ADR")
    open_the_door(db)
    response = client.get("/api/cards/1263/ADR.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == path.read_bytes()


# --- and the printing half ---


def test_no_code_is_printed_unless_it_will_still_work_later(db):
    """Both halves are needed, and the reason is the paper, not the request.

    Nobody is making a request when the driver scans the sheet three days
    later, so the address cannot be taken from the request the way a mail
    link's can — only an administrator knows what the outside world calls this
    installation. A code printed without one leads nowhere, and the person
    holding the paper cannot tell that from a code that failed to scan.
    """
    from app.api.routes.documents import _card_link_base

    assert _card_link_base(db) is None                       # neither
    open_the_door(db, public_url="https://cargo.example.com")
    assert _card_link_base(db) == "https://cargo.example.com"

    settings_store.save_instance_settings(
        db, InstanceSettings(card_links_enabled=False,
                             public_url="https://cargo.example.com"))
    assert _card_link_base(db) is None                       # address, no switch

    settings_store.save_instance_settings(
        db, InstanceSettings(card_links_enabled=True, public_url="   "))
    assert _card_link_base(db) is None                       # switch, no address


def test_the_document_carries_no_code_when_there_is_no_base():
    """A document rendered anywhere else is byte-for-byte what it always was."""
    from app.services.documents.pdf_render import _card_qr_block

    goods = [{"products": [{"un_number": "1263"}]}]
    assert _card_qr_block(None, goods, {}, "en", "ADR") == []
    assert _card_qr_block("https://cargo.example.com", [], {}, "en", "ADR") == []


def test_the_code_carries_the_un_numbers_and_the_regime_and_nothing_else():
    """Read back out of the drawn widget, not out of the string that built it.

    The regime matters as much as the numbers: a code on a sea document that
    opened the road card would answer the wrong question quietly.
    """
    from app.services.documents.pdf_render import _card_qr_block

    goods = [{"products": [
        {"un_number": "UN 1263", "name": "PAINT", "adr_total_quantity": "300"},
        {"un_number": "1203"},
    ]}]
    styles = _document_styles()
    block = _card_qr_block("https://cargo.example.com/", goods, styles, "en", "IMDG")
    drawing = block[0]._cellvalues[0][0]
    url = drawing.contents[0].value

    assert url == "https://cargo.example.com/cards?un=1263,1203&m=IMDG"
    assert "PAINT" not in url and "300" not in url


def test_the_code_stays_readable_on_the_documents_that_carry_the_most():
    """A fixed printed size would have failed exactly backwards.

    A QR is read by its module, the single square. One UN number encodes to a
    33-module symbol; thirty need 57, and at a fixed 24 mm those squares shrink
    to a third of a millimetre — under the floor a scanner needs. So the code
    that stopped working would have been the one on the document with the most
    substances on it, which is the one somebody most needs to scan.

    The module size is fixed instead and the printed size follows from it,
    measured here across the whole range one link can carry.
    """
    from reportlab.lib.units import mm

    from app.services.documents.pdf_render import (
        CARD_QR_MAX_MM, CARD_QR_MODULE_MM, _card_qr_block, _styles)

    styles = _styles()
    sizes = []
    for count in (1, 2, 5, 12, 30):
        goods = [{"products": [{"un_number": f"{1000 + i}"} for i in range(count)]}]
        block = _card_qr_block("https://emcargo.example.com", goods, styles,
                               "en", "ADR")
        drawing = block[0]._cellvalues[0][0]
        widget = drawing.contents[0]
        across = widget.qr.getModuleCount() + 2 * widget.barBorder
        side_mm = drawing.width / mm
        sizes.append(side_mm)
        # Held to the module size the code is built for, with only the printed
        # ceiling allowed to trim it — and even at thirty numbers, the most one
        # link may carry, it barely does.
        assert 0.5 <= side_mm / across <= CARD_QR_MODULE_MM + 0.01, \
            (count, across, side_mm)
        assert side_mm <= CARD_QR_MAX_MM

    # It grows with the data rather than being one size for everything.
    assert sizes == sorted(sizes) and sizes[-1] > sizes[0]


def test_an_air_document_asks_for_the_icao_card_not_for_all_of_them():
    """``IATA_DGR`` is the profile the wizard sends. It was absent from the
    profile-to-modality map, and an unmapped profile does not fall through to
    nothing — it falls through to *every* modality."""
    from app.services.documents.un_cards import _modalities_for

    assert _modalities_for(["IATA_DGR"]) == ["ICAO"]


def _document_styles():
    from app.services.documents.pdf_render import _styles

    return _styles()


def test_the_card_route_is_rate_limited(client, db):
    """Authentication does not replace limits on repeated card-store requests.
    The number is in ``test_ratelimit_key``'s one table; what
    matters here is that the limit is reached rather than merely declared."""
    import logging

    from app.core import ratelimit

    open_the_door(db)
    allowed = int(ratelimit.CARD_LINKS.split("/")[0])
    logging.disable(logging.WARNING)
    try:
        seen = [client.get("/api/cards/lookup?un=1263").status_code
                for _ in range(allowed + 1)]
    finally:
        logging.disable(logging.NOTSET)
    assert 429 not in seen[:allowed], seen
    assert seen[allowed] == 429


def test_cards_do_not_add_anonymous_application_routes(client):
    """A sweep catches a route that accidentally loses its session dependency.

    Every route the application serves either needs a signed-in user, is one of
    the handful that has always been open (health, the setup probe, the login
    endpoints themselves and the static frontend).
    """
    from app.core.deps import get_current_user, require_admin

    known_open = {
        # The application's own status, which carries no data about anybody.
        "/api/health", "/api/regulatory", "/api/setup-status",
        # Exact public attribution/database downloads contain no tenant data.
        "/api/legal/{document}",
        # Getting in, and getting back in. These cannot require a session:
        # they are how a session is obtained. All six are rate limited.
        "/api/auth/login", "/api/auth/login/two-factor",
        "/api/auth/2fa/send-code", "/api/auth/forgot-password",
        "/api/auth/reset-password", "/api/auth/reset-password/check",
        "/api/auth/setup", "/api/auth/setup-status",
        # Signing out clears a cookie and nothing else; requiring a valid
        # session to drop one is how you strand somebody on an expired token.
        "/api/auth/logout",
        # The handful of settings the sign-in screen itself must render with.
        "/api/settings/public", "/api/meta/version",
        # The built frontend and FastAPI's own documentation.
        "/{full_path:path}", "/openapi.json", "/docs", "/docs/oauth2-redirect",
        "/redoc",
    }
    guards = {get_current_user, require_admin}

    open_routes = []
    for address in route_table.addresses(app):
        if not address.operation or address.path in known_open:
            continue
        if not guards & address.guards:
            open_routes.append(address.path)
    # The walk must have seen the table: an empty one passes for the wrong
    # reason, which is what FastAPI 0.141's included routers first produced.
    assert any(a.path == "/api/auth/login" for a in route_table.addresses(app))

    # Since v1.172.0 the door itself is public too: the installation's name
    # and its pictures are what the sign-in page shows, so they cannot sit
    # behind the sign-in. They are read-only here; changing them is on the
    # admin router, which test_branding.py checks is guarded and absent from
    # the open application.
    the_door = {"/api/branding", "/api/branding/logo", "/api/branding/modality/{key}"}
    assert set(open_routes) <= the_door, \
        sorted(open_routes)
