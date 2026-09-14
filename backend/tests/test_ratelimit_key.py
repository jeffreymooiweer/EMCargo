"""Who a rate limit counts against, behind a proxy and in front of one.

The bug this covers was invisible in every test and in every direct-to-container
deployment: `slowapi`'s own key function reads `request.client.host`, which
behind a reverse proxy is the proxy, so all callers shared one bucket. Fifteen
colleagues behind one nginx shared ten sign-in attempts a minute.

The half-fix is worse than the bug and is what most of these tests are about. A
proxy *appends* to `X-Forwarded-For`, so a caller can put anything they like to
the left of what the proxy saw. Keying on the left of that list hands every
caller a fresh bucket per request, which is a rate limiter that does not limit.
"""
import pytest
from starlette.datastructures import Headers

from app.core.config import get_settings
from app.core.ratelimit import client_address


class _Client:
    def __init__(self, host):
        self.host = host


class _Request:
    """Only the two things the key function reads."""

    def __init__(self, peer="10.0.0.9", forwarded=None):
        self.client = _Client(peer) if peer else None
        self.headers = Headers(
            {"x-forwarded-for": forwarded} if forwarded is not None else {})


@pytest.fixture
def settings(monkeypatch):
    """The real Settings object, restored by the cache clear afterwards."""
    current = get_settings()
    yield current
    get_settings.cache_clear()


def configure(settings, monkeypatch, *, trust=True, count=1):
    monkeypatch.setattr(settings, "trusted_proxy_headers", trust)
    monkeypatch.setattr(settings, "trusted_proxy_count", count)


# --- the bug ---


def test_two_callers_behind_one_proxy_are_two_callers(settings, monkeypatch):
    """The whole point. Before this, both keyed on the proxy's address."""
    configure(settings, monkeypatch)
    first = client_address(_Request(peer="10.0.0.9", forwarded="203.0.113.7"))
    second = client_address(_Request(peer="10.0.0.9", forwarded="203.0.113.8"))
    assert first == "203.0.113.7"
    assert second == "203.0.113.8"
    assert first != second


# --- the half-fix, which is worse than the bug ---


def test_a_caller_cannot_choose_their_own_bucket(settings, monkeypatch):
    """The caller sent ``X-Forwarded-For: 1.2.3.4``; nginx appended what it saw.

    Reading the left of the list would give the caller a new bucket for every
    request they care to invent.
    """
    configure(settings, monkeypatch)
    key = client_address(_Request(
        peer="10.0.0.9", forwarded="1.2.3.4, 203.0.113.7"))
    assert key == "203.0.113.7"


def test_a_spoofed_header_cannot_frame_someone_else(settings, monkeypatch):
    """The other direction: claiming a victim's address to exhaust their budget."""
    configure(settings, monkeypatch)
    victim = client_address(_Request(peer="10.0.0.9", forwarded="203.0.113.5"))
    attacker = client_address(_Request(
        peer="10.0.0.9", forwarded="203.0.113.5, 203.0.113.9"))
    assert attacker == "203.0.113.9"
    assert attacker != victim


# --- how many proxies ---


def test_two_proxies_count_two_from_the_right(settings, monkeypatch):
    """client -> CDN -> nginx -> app. The CDN appended the client, nginx the CDN."""
    configure(settings, monkeypatch, count=2)
    key = client_address(_Request(
        peer="10.0.0.9", forwarded="203.0.113.7, 198.51.100.2"))
    assert key == "203.0.113.7"


def test_a_short_header_falls_back_to_the_peer(settings, monkeypatch):
    """Configured for two proxies, only one hop present: misconfigured.

    A limiter that counts everyone as one caller is useless. A limiter keyed on
    a value the caller chooses is worse, so this degrades to the useless one.
    """
    configure(settings, monkeypatch, count=2)
    assert client_address(_Request(
        peer="10.0.0.9", forwarded="1.2.3.4")) == "10.0.0.9"


def test_a_count_below_one_is_treated_as_one(settings, monkeypatch):
    """Zero would mean indexing from the wrong end of the list entirely."""
    configure(settings, monkeypatch, count=0)
    assert client_address(_Request(
        peer="10.0.0.9", forwarded="1.2.3.4, 203.0.113.7")) == "203.0.113.7"


# --- with no proxy in front ---


def test_the_header_is_ignored_when_it_is_not_trusted(settings, monkeypatch):
    """``TRUSTED_PROXY_HEADERS=false`` means exactly nobody is vouching."""
    configure(settings, monkeypatch, trust=False)
    assert client_address(_Request(
        peer="203.0.113.1", forwarded="1.2.3.4")) == "203.0.113.1"


def test_direct_deployments_ignore_forwarded_headers_by_default(monkeypatch):
    """A fresh deployment may expose its port directly. Changing a forged
    header must not provide a fresh password-guessing budget by default."""
    monkeypatch.delenv("TRUSTED_PROXY_HEADERS", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().trusted_proxy_headers is False
        assert client_address(_Request(peer="203.0.113.1", forwarded="1.2.3.4")) == "203.0.113.1"
        assert client_address(_Request(peer="203.0.113.1", forwarded="5.6.7.8")) == "203.0.113.1"
    finally:
        get_settings.cache_clear()


def test_no_header_means_the_peer(settings, monkeypatch):
    configure(settings, monkeypatch)
    assert client_address(_Request(peer="203.0.113.1")) == "203.0.113.1"


def test_an_empty_header_means_the_peer(settings, monkeypatch):
    configure(settings, monkeypatch)
    assert client_address(_Request(peer="203.0.113.1", forwarded="  ,  ")) \
        == "203.0.113.1"


def test_no_peer_at_all_matches_what_slowapi_did(settings, monkeypatch):
    """A test client or a unix socket has no peer. Unchanged behaviour."""
    configure(settings, monkeypatch)
    assert client_address(_Request(peer=None)) == "127.0.0.1"


def test_whitespace_around_the_entries_is_not_part_of_the_key(settings, monkeypatch):
    """Otherwise ``a, b`` and ``a,b`` are two different callers."""
    configure(settings, monkeypatch)
    assert client_address(_Request(forwarded=" 203.0.113.7 ")) == "203.0.113.7"


# --- and the limiter that enforces anything actually uses it ---


def test_there_is_exactly_one_limiter_in_the_application():
    """The trap this fix walked into, kept shut.

    ``main.py`` built a limiter and put it on ``app.state``; ``auth.py`` built a
    second one, and that second one carried all six ``@limiter.limit``
    decorators. Only the second enforced anything, so re-keying the first was a
    no-op that a unit test of the key function passes either way. One limiter
    now, and a source sweep so a third cannot appear quietly.
    """
    import pathlib
    app_dir = pathlib.Path(__file__).resolve().parents[1] / "app"
    built = [path for path in app_dir.rglob("*.py")
             if "Limiter(" in path.read_text()]
    assert [p.name for p in built] == ["ratelimit.py"]


def test_the_limiter_carrying_the_decorators_is_keyed_on_this():
    """Asserted through the route module, not through ``app.state``."""
    from app.api.routes import auth
    from app.core.ratelimit import limiter
    from app.main import app
    assert auth.limiter is limiter
    assert app.state.limiter is limiter
    assert limiter._key_func is client_address


def test_every_rate_limit_in_the_application_in_one_table():
    """The whole set, so a change to any of them is a change to this list.

    Half the limits sit in ``api/routes/auth.py`` and half are named in
    ``core/ratelimit.py``; this is the one place both halves are visible at
    once. Adding an endpoint to the limiter means adding a line here, which is
    the point — a limit nobody wrote down is a limit nobody can weigh.
    """
    import app.main  # noqa: F401  (importing registers the routes)

    from app.core.ratelimit import limiter

    actual = {
        name.split(".")[-1]: str(limits[0].limit)
        for name, limits in limiter._route_limits.items()
    }
    assert actual == {
        # Signing in and the ways around it.
        "login": "10 per 1 minute",
        "login_two_factor": "10 per 1 minute",
        "two_factor_send_code": "5 per 1 minute",
        "two_factor_confirm": "10 per 1 minute",
        "two_factor_new_recovery_codes": "10 per 1 minute",
        "two_factor_disable": "10 per 1 minute",
        "forgot_password": "5 per 1 minute",
        "reset_password_check": "30 per 1 minute",
        "reset_password": "10 per 1 minute",
        # What costs CPU, or somebody else's service, or somebody else's inbox.
        "export": "60 per 1 minute",
        "export_bundle": "10 per 1 minute",
        # The kept bundle rendered again from the history: the same work as
        # the bundle, so the same allowance.
        "shipment_documents": "10 per 1 minute",
        # The running entry, saved a few seconds after the typing stops.
        "save_draft": "60 per 1 minute",
        # Local OCR and model proposals have separate CPU budgets.
        "read_document": "6 per 1 minute",
        "propose_document": "30 per 1 minute",
        # The adviser's annual report reads every kept shipment of a year.
        "review_status": "60 per 1 minute",
        "submit_review": "60 per 1 minute",
        "shipment_report": "20 per 1 minute",
        "shipment_report_workbook": "20 per 1 minute",
        "shipment_report_form": "20 per 1 minute",
        "shipment_report_pdf": "20 per 1 minute",
        "mail_bundle": "5 per 1 minute",
        "export_un_cards": "10 per 1 minute",
        "read_carrier_confirmation": "20 per 1 minute",
        "assistant_step": "120 per 1 minute",
        "assistant_model": "3 per 1 minute",
        "geo_address": "60 per 1 minute",
        "geo_businesses": "60 per 1 minute",
        # Groupage: one points check per consignment plus one over the load.
        "dg_trip": "30 per 1 minute",
        # The two that answer a stranger. Everything above this line is a
        # colleague with a script at worst; these are the public card links.
        "card_lookup": "30 per 1 minute",
        "card_file": "30 per 1 minute",
    }


def test_mailing_is_held_tighter_than_the_bundle_it_sends():
    """The bundle costs this installation CPU; mailing it costs somebody else.

    Kept as a relation rather than two numbers, because the reason survives a
    retune and the numbers may not.
    """
    from app.core import ratelimit

    def per_minute(limit):
        return int(limit.split("/")[0])

    assert per_minute(ratelimit.DOCUMENT_BUNDLE_MAIL) \
        < per_minute(ratelimit.DOCUMENT_BUNDLE)


def test_two_callers_behind_one_proxy_get_their_own_budget_end_to_end(settings, monkeypatch):
    """The whole fix, measured where it matters: through a real request.

    Sign-in allows ten a minute. Eleven from one address is a 429; the eleventh
    from a different address behind the same proxy is not. Before the fix both
    counted against the proxy, and the second caller was refused for something
    the first did.
    """
    import logging

    from fastapi.testclient import TestClient

    from app.main import app

    configure(settings, monkeypatch, trust=True)

    def sign_in(client, address):
        return client.post(
            "/api/auth/login",
            json={"username": "nobody", "password": "wrong"},
            headers={"X-Forwarded-For": address},
        ).status_code

    logging.disable(logging.WARNING)
    try:
        with TestClient(app) as client:
            first = [sign_in(client, "198.51.100.10") for _ in range(11)]
            other = sign_in(client, "198.51.100.11")
    finally:
        logging.disable(logging.NOTSET)

    assert 429 not in first[:10], first
    assert first[10] == 429
    assert other != 429
