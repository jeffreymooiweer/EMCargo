"""A restart must load the current UI instead of a cached pre-update observer.

The update-loop fix lives in the frontend. Serving an old HTML entry point
can keep loading old JavaScript after deployment, including when the browser
reloads a nested settings route. Hashed assets can retain their normal caching.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings


@pytest.mark.parametrize("route", ["/", "/index.html", "/admin/settings/updates"])
def test_entry_point_is_not_cached_across_an_update(tmp_path, monkeypatch, route):
    from app.main import create_app

    static = tmp_path / "static"
    (static / "assets").mkdir(parents=True)
    index = static / "index.html"
    index.write_text('<script src="/assets/old.js"></script>')
    (static / "assets" / "old.js").write_text("/* old release */")
    monkeypatch.setattr(Settings, "static_dir", property(lambda self: static))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        # No lifespan is needed: entry-point delivery must not depend on seed
        # data or an authenticated session before the browser can load the UI.
        client = TestClient(create_app())
        first = client.get(route)
        assert first.status_code == 200
        assert first.headers["cache-control"] == "no-store"
        assert "/assets/old.js" in first.text

        index.write_text('<script src="/assets/new.js"></script>')
        current = client.get(route, headers={"If-None-Match": first.headers["etag"]})
        assert current.status_code == 200
        assert current.headers["cache-control"] == "no-store"
        assert "/assets/new.js" in current.text
        assert client.get("/assets/old.js").status_code == 200
    finally:
        get_settings.cache_clear()
