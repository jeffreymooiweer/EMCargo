"""In-app updating: ready when the installation supports it, honest always.

The swap itself needs a real Docker daemon and is exercised in life; what
these tests hold is everything around it — the capability answer for every
way of not being able, the refusal paths of the API, the exact requests
the update sends to the daemon, and the helper's successor payload and
rollback, all against a scripted Docker API.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.core.config import get_settings
from app.services import updater
from app import update_helper


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler),
                        base_url="http://docker")


@pytest.mark.parametrize("legacy_switch", [None, "false", "true"])
def test_capability_is_ready_without_an_environment_opt_in(data_dir, tmp_path, monkeypatch, legacy_switch):
    """Installed Unraid templates carried an explicit false value. Merely
    changing a default would leave those administrators blocked after updating.
    Capability must now depend on the real Docker prerequisites, and observing
    it must never start an update by itself.
    """
    if legacy_switch is None:
        monkeypatch.delenv("UPDATE_APPLY_ENABLED", raising=False)
    else:
        monkeypatch.setenv("UPDATE_APPLY_ENABLED", legacy_switch)
    get_settings.cache_clear()
    _socket(tmp_path, monkeypatch)
    monkeypatch.setattr(updater, "own_container_id", lambda client: "a" * 64)

    def handler(request):
        assert request.method == "GET"
        return httpx.Response(200, json={"Config": {"Image": updater.IMAGE_REPOSITORY + ":latest"}})

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    ability = updater.capability()
    assert ability["apply_enabled"] is True
    assert ability["available"] is True
    assert ability["reason"] is None


def test_capability_reports_a_missing_socket(data_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "DOCKER_SOCKET", tmp_path / "no-socket")
    ability = updater.capability()
    assert ability["available"] is False
    assert ability["reason"] == "no_socket"


def _socket(tmp_path, monkeypatch):
    # Keep the fake bind path free of Windows drive-letter separators.
    monkeypatch.chdir(tmp_path)
    socket = Path("docker.sock")
    socket.write_bytes(b"")
    monkeypatch.setattr(updater, "DOCKER_SOCKET", socket)


def test_capability_refuses_a_foreign_image(data_dir, tmp_path, monkeypatch):
    _socket(tmp_path, monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "Id": "a" * 64, "Config": {"Image": "somebody/else:latest"}})

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    monkeypatch.setattr(updater, "own_container_id", lambda client: "a" * 64)
    ability = updater.capability()
    assert ability["available"] is False
    assert ability["reason"] == "foreign_image"


def test_capability_names_a_socket_it_may_not_open(data_dir, tmp_path, monkeypatch):
    """The Unraid case: socket mounted, but the socket is owned
    by root and the app runs as uid 1000. That must come back as its own
    reason — it used to surface as container_not_found, which sent the
    operator looking in the wrong place."""
    _socket(tmp_path, monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Permission denied")

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    ability = updater.capability()
    assert ability["available"] is False
    assert ability["reason"] == "socket_permission"


def test_own_container_id_verifies_against_the_daemon(monkeypatch):
    known = "b" * 64

    def handler(request: httpx.Request) -> httpx.Response:
        if known in request.url.path:
            return httpx.Response(200, json={"Id": known})
        return httpx.Response(404)

    monkeypatch.setenv("HOSTNAME", "not-a-container-id")
    monkeypatch.setattr(
        updater, "Path",
        lambda p: SimpleNamespace(read_text=lambda **k: f"0::/docker/{known}\n"))
    with make_client(handler) as client:
        assert updater.own_container_id(client) == known


def test_start_update_pulls_and_hands_over(data_dir, tmp_path, monkeypatch):
    _socket(tmp_path, monkeypatch)
    own_id = "c" * 64
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if path == "/_ping":
            return httpx.Response(200, text="OK")
        if path == "/images/create":
            # The published tag carries no "v": pulling :v1.133.0 is a 404.
            assert request.url.params["fromImage"] == updater.IMAGE_REPOSITORY
            assert request.url.params["tag"] == "1.133.0"
            return httpx.Response(200, text=json.dumps({"status": "ok"}) + "\n")
        if path.startswith("/images/") and path.endswith("/json"):
            return httpx.Response(200, json={"Id": "sha256:new"})
        if path == f"/containers/{own_id}/json":
            return httpx.Response(200, json={
                "Id": own_id,
                "Config": {"Image": updater.IMAGE_REPOSITORY + ":1.132.0"},
                "HostConfig": {"Binds": ["/srv/data:/data"]},
            })
        if path == "/containers/create":
            body = json.loads(request.read())
            assert body["Image"] == updater.IMAGE_REPOSITORY + ":1.133.0"
            assert body["Entrypoint"] == ["python", "-m", "app.update_helper"]
            assert body["Cmd"] == [own_id, body["Image"]]
            assert "/srv/data:/data" in body["HostConfig"]["Binds"]
            assert any(b.endswith("docker.sock") or "docker.sock" in b
                       for b in body["HostConfig"]["Binds"])
            return httpx.Response(201, json={"Id": "helper123"})
        if path == "/containers/helper123/start":
            return httpx.Response(204)
        return httpx.Response(404)

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    monkeypatch.setattr(updater, "own_container_id", lambda client: own_id)
    result = updater.start_update("1.133.0")
    assert result["to"] == "1.133.0"
    assert "POST /images/create" in calls
    assert "POST /containers/create" in calls
    state = json.loads((tmp_path / "update-state.json").read_text())
    assert state["phase"] == "handed_over"


def test_the_socket_is_not_mounted_twice(data_dir, tmp_path, monkeypatch):
    """The operator already mounted the socket, and Unraid records it with a
    mode: ``/var/run/docker.sock:/var/run/docker.sock:rw``. Adding the plain
    form next to it gives two mounts on one destination, and the daemon
    refuses that with 400 "Duplicate mount point"."""
    _socket(tmp_path, monkeypatch)
    own_id = "d" * 64
    seen: list[str] = []
    # The fixture puts the socket in a temporary directory; what matters here
    # is the mode Unraid appends, not the path it lives at.
    sock = str(updater.DOCKER_SOCKET)
    mounted = f"{sock}:{sock}:rw"

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/_ping":
            return httpx.Response(200, text="OK")
        if path == "/images/create":
            return httpx.Response(200, text=json.dumps({"status": "ok"}) + "\n")
        if path.startswith("/images/") and path.endswith("/json"):
            return httpx.Response(200, json={"Id": "sha256:new"})
        if path == f"/containers/{own_id}/json":
            return httpx.Response(200, json={
                "Id": own_id,
                "Config": {"Image": updater.IMAGE_REPOSITORY + ":1.135.0"},
                "HostConfig": {"Binds": [
                    "/mnt/user/appdata/emcargo:/data:rw",
                    mounted,
                ]},
            })
        if path == "/containers/create":
            seen.extend(json.loads(request.read())["HostConfig"]["Binds"])
            return httpx.Response(201, json={"Id": "helper456"})
        if path == "/containers/helper456/start":
            return httpx.Response(204)
        return httpx.Response(404)

    monkeypatch.setattr(updater, "docker_client", lambda: make_client(handler))
    monkeypatch.setattr(updater, "own_container_id", lambda client: own_id)
    updater.start_update("1.138.0")

    sockets = [b for b in seen if updater._bind_destination(b) == sock]
    assert sockets == [mounted]
    assert "/mnt/user/appdata/emcargo:/data:rw" in seen


def test_bind_destination_reads_every_shape_docker_writes():
    assert updater._bind_destination("/srv/data:/data") == "/data"
    assert updater._bind_destination("/srv/data:/data:rw") == "/data"
    assert updater._bind_destination("/srv/data:/data:ro,z") == "/data"
    assert updater._bind_destination("named-volume:/data") == "/data"
    assert updater._bind_destination("/data") == "/data"


def test_start_update_refuses_a_non_version(data_dir, tmp_path, monkeypatch):
    _socket(tmp_path, monkeypatch)
    monkeypatch.setattr(updater, "capability", lambda: {
        "available": True, "container": "c" * 64,
        "image": updater.IMAGE_REPOSITORY + ":v1"})
    with pytest.raises(updater.UpdateError):
        updater.start_update("latest")
    with pytest.raises(updater.UpdateError):
        updater.start_update("1.2.3; rm -rf /")


def test_the_successor_keeps_the_configuration():
    old = {
        "Id": "d" * 64,
        "Config": {"Env": ["A=1"], "Labels": {"x": "y"},
                   "ExposedPorts": {"8000/tcp": {}}},
        "HostConfig": {"Binds": ["/srv:/data"], "RestartPolicy":
                       {"Name": "unless-stopped"}, "LogConfig": {"Type": "json-file"},
                       "OomScoreAdj": 123},
        "NetworkSettings": {"Networks": {"bridge": {"Aliases": None}}},
    }
    payload = update_helper.successor_payload(old, "repo:v2")
    assert payload["Image"] == "repo:v2"
    assert payload["Env"] == ["A=1"]
    assert payload["HostConfig"]["Binds"] == ["/srv:/data"]
    assert payload["HostConfig"]["RestartPolicy"]["Name"] == "unless-stopped"
    assert "OomScoreAdj" not in payload["HostConfig"]


def test_the_helper_rolls_back_when_the_successor_will_not_start(tmp_path, monkeypatch):
    monkeypatch.setattr(update_helper, "DATA_DIR", tmp_path)
    old_id = "e" * 64
    log: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        log.append(f"{method} {path} {dict(request.url.params)}")
        if path == f"/containers/{old_id}/json":
            return httpx.Response(200, json={
                "Id": old_id, "Name": "/emcargo",
                "Config": {"Env": ["A=1"]},
                "HostConfig": {"Binds": ["/srv:/data"]},
                "NetworkSettings": {"Networks": {}},
                "State": {"Running": False},
            })
        if path == f"/containers/{old_id}/stop":
            return httpx.Response(204)
        if path == f"/containers/{old_id}/rename":
            return httpx.Response(204)
        if path == "/containers/create":
            return httpx.Response(201, json={"Id": "newbie"})
        if path == "/containers/newbie/start":
            return httpx.Response(500, text="no")
        if path == "/containers/newbie" and method == "DELETE":
            return httpx.Response(204)
        if path == f"/containers/{old_id}/start":
            return httpx.Response(204)
        return httpx.Response(404)

    real_client = httpx.Client
    monkeypatch.setattr(
        update_helper.httpx, "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler),
                                     base_url="http://docker"))
    monkeypatch.setattr(update_helper, "sys",
                        SimpleNamespace(argv=["x", old_id, "repo:v2"]))
    assert update_helper.main() == 1
    state = json.loads((tmp_path / "update-state.json").read_text())
    assert state["phase"] == "failed"
    # The rollback renamed the old container back and started it again.
    assert any("rename" in line and "emcargo" in line for line in log)
    assert f"POST /containers/{old_id}/start {{}}" in log


def test_the_api_refuses_without_capability(data_dir, monkeypatch):
    from types import SimpleNamespace as NS
    from fastapi.testclient import TestClient
    from app.core.deps import get_current_user
    from app.main import app

    monkeypatch.setattr(updater, "DOCKER_SOCKET", data_dir / "missing-socket")
    app.dependency_overrides[get_current_user] = lambda: NS(
        id=1, username="admin", role="admin", active=True)
    try:
        with TestClient(app) as client:
            ability = client.get("/api/update-capability")
            assert ability.status_code == 200
            assert ability.json()["available"] is False
            response = client.post("/api/update-apply")
            assert response.status_code == 409
            assert response.json()["detail"]["params"]["reason"] == "no_socket"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize("role", ["user", "super_user", "dg_specialist"])
def test_updates_stay_admin_only_when_enabled_by_default(data_dir, monkeypatch, role):
    """Removing the environment gate must not grant update access to an
    operational role. The real route dependencies must reject the request
    before probing Docker or starting a container replacement.
    """
    from fastapi.testclient import TestClient
    from app.core.deps import get_current_user
    from app.main import app

    def unexpected_capability():
        pytest.fail("A non-admin request reached the Docker capability probe")

    monkeypatch.setattr(updater, "capability", unexpected_capability)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="operator", role=role, active=True)
    try:
        with TestClient(app) as client:
            assert client.get("/api/update-capability").status_code == 403
            assert client.get("/api/update-state").status_code == 403
            assert client.post("/api/update-apply").status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_named_mounts_and_custom_data_dir_survive_handover(data_dir, monkeypatch):
    """Compose can describe volumes in HostConfig.Mounts instead of Binds.
    Losing those mounts leaves the helper writing progress into its own image,
    while adding the socket again makes Docker reject the helper entirely.
    Completion written by a fast helper must also win over the parent state.
    """
    own_id = 'f' * 64
    socket = str(updater.DOCKER_SOCKET)
    mounts = [
        {"Type": "volume", "Source": "emcargo-data", "Target": str(data_dir)},
        {"Type": "bind", "Source": socket, "Target": socket},
    ]
    monkeypatch.setattr(updater, "capability", lambda: {"available": True, "container": own_id})
    monkeypatch.setattr(updater, "_pull", lambda *args: None)

    def handler(request):
        if request.url.path == f'/containers/{own_id}/json':
            return httpx.Response(200, json={"Id": own_id, "HostConfig": {"Mounts": mounts}})
        if request.url.path == '/containers/create':
            payload = json.loads(request.read())
            assert payload['HostConfig']['Mounts'] == mounts
            assert not payload['HostConfig']['Binds']
            assert payload['Env'] == [f'DATA_DIR={data_dir}']
            assert payload['User'] == '0'
            return httpx.Response(201, json={'Id': 'helper'})
        if request.url.path == '/containers/helper/start':
            assert updater.read_state()['phase'] == 'handed_over'
            updater.write_state({'phase': 'done', 'to': '2.2.0'})
            return httpx.Response(204)
        return httpx.Response(404)

    monkeypatch.setattr(updater, 'docker_client', lambda: make_client(handler))
    updater.start_update('2.2.0')
    assert updater.read_state()['phase'] == 'done'


@pytest.mark.parametrize('reference', [
    updater.IMAGE_REPOSITORY + '@sha256:' + 'a' * 64,
    updater.IMAGE_REPOSITORY + ':2.1.1@sha256:' + 'b' * 64,
])
def test_capability_accepts_our_repository_pinned_by_digest(data_dir, tmp_path, monkeypatch, reference):
    """A digest pins an image; it does not change which repository owns it.
    Previously splitting at the digest colon classified official images as foreign.
    """
    _socket(tmp_path, monkeypatch)
    monkeypatch.setattr(updater, 'own_container_id', lambda client: 'abc')
    monkeypatch.setattr(updater, 'docker_client', lambda: make_client(
        lambda request: httpx.Response(200, json={'Config': {'Image': reference}})))
    assert updater.capability()['available'] is True


@pytest.mark.parametrize('health,expected', [('healthy', True), ('unhealthy', False)])
def test_running_is_not_enough_to_commit_an_update(monkeypatch, health, expected):
    """Docker starts the process before FastAPI finishes booting. An unhealthy
    running replacement must not cause the working previous container to be deleted.
    """
    statuses = iter(['starting', health])
    monkeypatch.setattr(update_helper.time, 'sleep', lambda _: None)
    with make_client(lambda request: httpx.Response(200, json={
        'State': {'Running': True, 'ExitCode': 0, 'Health': {'Status': next(statuses)}}
    })) as client:
        assert update_helper.wait_until_running(client, 'new') is expected


def test_apply_refuses_a_second_request_before_handover(data_dir, monkeypatch):
    """Two browser tabs must not start two helper containers. The recent state
    also protects the short period after the pull thread hands over and exits.
    """
    from app.api.routes import meta
    from fastapi import HTTPException
    monkeypatch.setattr(updater, 'capability', lambda: {'available': True})
    monkeypatch.setattr(meta, 'update_status', lambda **kwargs: {'update_available': True, 'latest': '2.2.0'})
    updater.write_state({'phase': 'handed_over', 'to': '2.2.0'})
    with pytest.raises(HTTPException) as failure:
        meta.update_apply(admin=SimpleNamespace(role='admin'), db=None)
    assert failure.value.status_code == 409
    assert failure.value.detail['code'] == 'update.in_progress'
    assert not meta._apply_lock.locked()


def test_apply_records_unexpected_worker_failure_and_releases_lock(data_dir, monkeypatch):
    """A transport exception is different from UpdateError, but the operator
    still needs a terminal failure and must be able to retry the update.
    """
    from app.api.routes import meta
    monkeypatch.setattr(updater, 'capability', lambda: {'available': True})
    monkeypatch.setattr(meta, 'update_status', lambda **kwargs: {'update_available': True, 'latest': '2.2.0'})
    def fail(*args):
        raise OSError('socket disconnected')
    monkeypatch.setattr(updater, 'start_update', fail)
    monkeypatch.setattr(meta.threading, 'Thread', lambda *, target, **kwargs: SimpleNamespace(start=target))
    meta.update_apply(admin=SimpleNamespace(role='admin'), db=None)
    assert updater.read_state()['phase'] == 'failed'
    assert 'socket disconnected' in updater.read_state()['error']
    assert not meta._apply_lock.locked()


@pytest.mark.parametrize("phase", ["done", "failed"])
def test_progress_is_fresh_and_survives_multiple_readers(data_dir, monkeypatch, phase):
    """The refresh loop reported since v2.8.0 depended on progress surviving
    navigation. All administrators must see the same uncached operation; one
    browser must not consume completion before another browser reconnects.
    Failure details must likewise remain available after a restart.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api.routes import meta
    from app.core.deps import require_admin

    app = FastAPI()
    app.include_router(meta.router, prefix="/api")
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    monkeypatch.setattr(meta, "get_version", lambda: "2.9.2")
    updater.write_state({"phase": phase, "to": "2.9.2", **({"error": "Health check failed"} if phase == "failed" else {})})
    recorded = updater.read_state()
    with TestClient(app) as client:
        for _ in range(3):
            response = client.get("/api/update-state")
            assert response.status_code == 200
            assert response.headers["cache-control"] == "private, no-store"
            assert response.json() == {"state": recorded, "current": "2.9.2"}
    assert updater.read_state() == recorded


def test_reading_completion_cannot_erase_a_concurrent_update(data_dir, monkeypatch):
    """Clearing a done record on GET used to unlink the progress file even
    when a newly accepted update had replaced it between the read and unlink.
    Observing an old snapshot must leave the next operation intact.
    """
    from fastapi import Response
    from app.api.routes import meta

    read_state = updater.read_state
    updater.write_state({"phase": "done", "to": "2.9.1"})

    def accept_next_update_during_read():
        previous = read_state()
        updater.write_state({"phase": "pulling", "to": "2.9.2"})
        return previous

    monkeypatch.setattr(updater, "read_state", accept_next_update_during_read)
    answer = meta.update_state(Response(), admin=SimpleNamespace(role="admin"))
    assert answer["state"]["phase"] == "done"
    assert read_state()["phase"] == "pulling"
    assert read_state()["to"] == "2.9.2"
