"""The UN card store: nothing enters it unverified, and imports are atomic.

The archive an administrator imports is the one untrusted input this feature
has, so the tests attack it the way an attacker would: a path that tries to
climb out of the store, a card whose checksum does not match its manifest, a
member the generator would never produce, an oversized file. Every one of
those must be refused — and, just as important, a refused import must leave
the previously working set exactly as it was.
"""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
import httpx
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.main import app
from app.services.documents import un_card_store


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def _card_bytes(un, modality):
    return b"%PDF-1.4\n% card UN" + un.encode() + b" " + modality.encode() + b"\n%%EOF\n"


def make_package(path: Path, cards=(("1203", "ADR"),), tamper=None,
                 extra_member=None, drop_manifest=False):
    """A package exactly as the generator builds one, unless told to lie."""
    entries = []
    blobs = {}
    for un, modality in cards:
        content = _card_bytes(un, modality)
        name = f"{modality}/UN{un}_{modality}.pdf"
        blobs[name] = content
        entries.append({
            "un_number": un, "modality": modality, "file": name, "pages": 1,
            "size": len(content), "sha256": hashlib.sha256(content).hexdigest(),
            "status": "available", "source": "test",
        })
    manifest = {
        "schema_version": 1, "generated_at": "2026-08-19T12:00:00Z",
        "generator_version": "1.0.0", "git_commit": "test",
        "editions": {"ADR": "ADR 2025"}, "counts": {}, "total_cards": len(entries),
        "total_size": sum(e["size"] for e in entries),
        "unavailable_modalities": {}, "cards": entries,
    }
    if tamper:
        tamper(manifest, blobs)
    with zipfile.ZipFile(path, "w") as archive:
        if not drop_manifest:
            archive.writestr("manifest.json", json.dumps(manifest))
        archive.writestr("generation-report.json", "{}")
        for name, content in blobs.items():
            archive.writestr(name, content)
        if extra_member:
            archive.writestr(extra_member, b"whatever")
    return path


def test_a_valid_package_installs_and_serves(data_dir, tmp_path):
    package = make_package(tmp_path / "p.zip", cards=(("1203", "ADR"), ("1017", "ADR")))
    result = un_card_store.import_package(package)
    assert result["imported"] == 2
    assert un_card_store.card_path("1203", "ADR") is not None
    assert un_card_store.status()["total_cards"] == 2
    assert un_card_store.status()["imported_at"]


def test_a_path_that_climbs_out_is_refused(data_dir, tmp_path):
    package = make_package(tmp_path / "p.zip", extra_member="../../evil.pdf")
    with pytest.raises(un_card_store.UnCardImportError, match="Unexpected file"):
        un_card_store.import_package(package)
    assert not un_card_store.store_dir().exists()
    assert not (data_dir.parent / "evil.pdf").exists()


def test_an_unexpected_member_is_refused_even_without_dots(data_dir, tmp_path):
    package = make_package(tmp_path / "p.zip", extra_member="ADR/extra.exe")
    with pytest.raises(un_card_store.UnCardImportError, match="Unexpected file"):
        un_card_store.import_package(package)


def test_a_checksum_mismatch_is_refused(data_dir, tmp_path):
    def lie(manifest, blobs):
        manifest["cards"][0]["sha256"] = "0" * 64
    package = make_package(tmp_path / "p.zip", tamper=lie)
    with pytest.raises(un_card_store.UnCardImportError, match="checksum"):
        un_card_store.import_package(package)


def test_a_package_without_manifest_is_refused(data_dir, tmp_path):
    package = make_package(tmp_path / "p.zip", drop_manifest=True)
    with pytest.raises(un_card_store.UnCardImportError, match="manifest"):
        un_card_store.import_package(package)


def test_a_card_that_is_not_a_pdf_is_refused(data_dir, tmp_path):
    def lie(manifest, blobs):
        name = manifest["cards"][0]["file"]
        blobs[name] = b"MZ not a pdf"
        manifest["cards"][0]["sha256"] = hashlib.sha256(blobs[name]).hexdigest()
        manifest["cards"][0]["size"] = len(blobs[name])
    package = make_package(tmp_path / "p.zip", tamper=lie)
    with pytest.raises(un_card_store.UnCardImportError, match="not a PDF"):
        un_card_store.import_package(package)


def test_an_oversized_member_is_refused_before_extraction(data_dir, tmp_path):
    def lie(manifest, blobs):
        name = manifest["cards"][0]["file"]
        blobs[name] = b"%PDF" + b"0" * (un_card_store.MAX_CARD_BYTES + 1)
        manifest["cards"][0]["sha256"] = hashlib.sha256(blobs[name]).hexdigest()
        manifest["cards"][0]["size"] = len(blobs[name])
    package = make_package(tmp_path / "p.zip", tamper=lie)
    with pytest.raises(un_card_store.UnCardImportError, match="larger than allowed"):
        un_card_store.import_package(package)


def test_garbage_that_is_not_a_zip_is_refused(data_dir, tmp_path):
    path = tmp_path / "p.zip"
    path.write_bytes(b"this is no archive")
    with pytest.raises(un_card_store.UnCardImportError, match="not a readable zip"):
        un_card_store.import_package(path)


def test_a_failed_import_keeps_the_working_set(data_dir, tmp_path):
    good = make_package(tmp_path / "good.zip", cards=(("1203", "ADR"),))
    un_card_store.import_package(good)
    before = un_card_store.card_path("1203", "ADR").read_bytes()

    def lie(manifest, blobs):
        manifest["cards"][0]["sha256"] = "0" * 64
    bad = make_package(tmp_path / "bad.zip", cards=(("1017", "ADR"),), tamper=lie)
    with pytest.raises(un_card_store.UnCardImportError):
        un_card_store.import_package(bad)

    # The old set is still there, byte for byte, and no scratch dirs linger.
    assert un_card_store.card_path("1203", "ADR").read_bytes() == before
    assert un_card_store.card_path("1017", "ADR") is None
    leftovers = [p for p in data_dir.iterdir() if p.name.startswith("un-cards.")]
    assert leftovers == []


def test_a_new_import_replaces_the_old_set_completely(data_dir, tmp_path):
    un_card_store.import_package(
        make_package(tmp_path / "one.zip", cards=(("1203", "ADR"),)))
    un_card_store.import_package(
        make_package(tmp_path / "two.zip", cards=(("1017", "ADR"),)))
    assert un_card_store.card_path("1017", "ADR") is not None
    # The replaced set's card is gone: no stale mix of two generations.
    assert un_card_store.card_path("1203", "ADR") is None


def test_remove_deletes_the_set(data_dir, tmp_path):
    un_card_store.import_package(make_package(tmp_path / "p.zip"))
    assert un_card_store.remove_installed() is True
    assert un_card_store.status()["installed"] is False
    assert un_card_store.remove_installed() is False


def test_card_path_never_guesses(data_dir, tmp_path):
    un_card_store.import_package(make_package(tmp_path / "p.zip"))
    assert un_card_store.card_path("1203", "ADR") is not None
    assert un_card_store.card_path("1203", "IMDG") is None
    assert un_card_store.card_path("12030", "ADR") is None
    assert un_card_store.card_path("../etc", "ADR") is None


def _published_release(**overrides):
    return {
        "tag_name": "un-cards-2026.09.12-1", "draft": False,
        "prerelease": False, "published_at": "2026-09-12T12:00:00Z",
        "assets": [{"name": un_card_store.PACKAGE_NAME, "size": 123,
                    "browser_download_url": "https://github.com/jeffreymooiweer/emcargo/releases/download/un-cards-2026.09.12-1/emcargo-un-cards.zip"}],
        **overrides,
    }


def _release_transport(monkeypatch, handler):
    client_type = httpx.Client
    monkeypatch.setattr(un_card_store.httpx, "Client", lambda **kwargs: client_type(
        transport=httpx.MockTransport(handler), **kwargs))


def test_app_releases_do_not_hide_an_older_card_set(monkeypatch):
    """A still-current card set must remain downloadable after more than
    one page of app releases; the two products share one release feed."""
    seen = []

    def respond(request):
        seen.append(request.url.params["page"])
        assert request.url.host == "api.github.com"
        assert request.url.params["per_page"] == "100"
        rows = ([{"tag_name": f"v2.{i}.0"} for i in range(100)]
                if seen[-1] == "1" else [_published_release()])
        return httpx.Response(200, json=rows)

    _release_transport(monkeypatch, respond)
    assert un_card_store.latest_remote()["tag"] == "un-cards-2026.09.12-1"
    assert seen == ["1", "2"]


def test_unpublished_or_incomplete_sets_are_not_download_candidates(monkeypatch):
    """A draft, prerelease or package still being uploaded is not an
    available set, even when its tag already looks like a card release."""
    rows = [_published_release(draft=True), _published_release(prerelease=True),
            _published_release(assets=[]), _published_release()]
    _release_transport(monkeypatch, lambda request: httpx.Response(200, json=rows))
    assert un_card_store.latest_remote()["available"] is True
    rows.pop()
    assert un_card_store.latest_remote() == {"available": False}


def test_missing_release_has_its_own_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(un_card_store, "latest_remote", lambda: {"available": False})
    with pytest.raises(un_card_store.UnCardReleaseUnavailable):
        un_card_store.download_latest_package(tmp_path / "cards.zip")
    assert not (tmp_path / "cards.zip").exists()


def test_missing_release_and_network_failure_remain_distinct(data_dir, monkeypatch):
    """The screenshot showed an English error after a known-empty lookup.
    A missing publication now has its own translated message; a broken
    connection must never be presented as proof that no set exists."""
    from types import SimpleNamespace
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="ada", role="admin", active=True)
    try:
        with TestClient(app) as client:
            monkeypatch.setattr(un_card_store, "latest_remote", lambda: {"available": False})
            response = client.post("/api/un-cards/download-latest")
            assert response.status_code == 404
            assert response.json()["detail"]["code"] == "un_cards.no_release"

            def disconnected():
                raise httpx.ConnectError("offline")

            monkeypatch.setattr(un_card_store, "latest_remote", disconnected)
            remote = client.get("/api/un-cards/status?remote=true").json()["remote"]
            assert remote["reachable"] is False
            response = client.post("/api/un-cards/download-latest")
            assert response.status_code == 502
            assert response.json()["detail"]["code"] == "un_cards.download_failed"
    finally:
        app.dependency_overrides.clear()


# --- the endpoints are the administrator's only -------------------------------


def test_the_store_endpoints_require_admin(data_dir):
    from types import SimpleNamespace
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2, username="bob", role="user", active=True)
    try:
        with TestClient(app) as client:
            assert client.get("/api/un-cards/status").status_code == 403
            assert client.post("/api/un-cards/download-latest").status_code == 403
            assert client.post("/api/un-cards/remove").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_status_and_upload_import_through_the_api(data_dir, tmp_path):
    from types import SimpleNamespace
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="ada", role="admin", active=True)
    try:
        with TestClient(app) as client:
            assert client.get("/api/un-cards/status").json()["local"]["installed"] is False
            package = make_package(tmp_path / "p.zip")
            response = client.post(
                "/api/un-cards/import",
                files={"file": ("emcargo-un-cards.zip",
                                package.read_bytes(), "application/zip")})
            assert response.status_code == 200, response.text
            assert response.json()["imported"] == 1
            local = client.get("/api/un-cards/status").json()["local"]
            assert local["installed"] is True and local["total_cards"] == 1

            # A tampered upload is refused with the reason, and the set stays.
            def lie(manifest, blobs):
                manifest["cards"][0]["sha256"] = "0" * 64
            bad = make_package(tmp_path / "bad.zip", tamper=lie)
            response = client.post(
                "/api/un-cards/import",
                files={"file": ("x.zip", bad.read_bytes(), "application/zip")})
            assert response.status_code == 422
            assert "checksum" in response.json()["detail"]
            assert client.get("/api/un-cards/status").json()["local"]["installed"] is True

            assert client.post("/api/un-cards/remove").json()["removed"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("name", ["source.cdx.json", "cards.cdx.json",
                                 "licenses/python/reportlab-4.2.5/LICENSE"])
def test_published_package_metadata_is_preserved(data_dir, tmp_path, name):
    """The workflow appends source inventories and notices to the ZIP.
    Accepting only manifest/report made that published ZIP unimportable,
    even though a package generated locally passed the import test.
    """
    package = make_package(tmp_path / "p.zip", extra_member=name)
    assert un_card_store.import_package(package)["imported"] == 1
    assert (un_card_store.store_dir() / name).read_bytes() == b"whatever"


@pytest.mark.parametrize("name", ["licenses/../outside.txt", "licenses/a/../../outside.txt",
                                 "licenses//absolute.txt", "licenses/./hidden.txt",
                                 "licenses/..\\outside.txt", "licenses/.hidden.txt"])
def test_notice_paths_cannot_escape_their_metadata_directory(data_dir, tmp_path, name):
    """Allowing nested notices must not widen the archive traversal surface."""
    package = make_package(tmp_path / "p.zip", extra_member=name)
    with pytest.raises(un_card_store.UnCardImportError, match="Unexpected file"):
        un_card_store.import_package(package)
    assert not un_card_store.store_dir().exists()
