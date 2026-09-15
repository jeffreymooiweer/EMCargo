"""The hands of the in-app update: swap the application container.

Started by :mod:`app.services.updater` as a short-lived container **from
the freshly pulled image**, with the Docker socket and the application's
own binds mounted. Being a separate container is the whole point: the
application cannot replace itself while running, but this helper can
stop it, rename it aside, create its successor with the identical
configuration on the new image, start that, and only then remove the
old one. If the successor will not start, the old container is renamed
back and restarted — an update that fails must leave a working
installation, not a stopped one.

    python -m app.update_helper <old-container-id> <new-image-reference>

Everything it does is reported into ``<data-dir>/update-state.json``,
which it reaches through the same bind the application uses; the new
instance reads that file to say "updated to vX", the old one (after a
rollback) to say what went wrong.
"""
from __future__ import annotations

import json
import io
import os
import sys
import time
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import httpx

DOCKER_SOCKET = "/var/run/docker.sock"
DATA_DIR = Path(os.environ.get("DATA_DIR") or "/data")

#: HostConfig keys carried over to the successor. Deliberately a list of
#: the common ones rather than the whole inspect blob: the blob mixes
#: configuration with runtime state, and an exotic setup (device mappings,
#: custom seccomp) is better served by the operator's own tooling than by
#: a partial imitation of it.
HOST_CONFIG_KEYS = (
    "Binds", "Mounts", "PortBindings", "RestartPolicy", "NetworkMode",
    "ExtraHosts", "Dns", "DnsSearch", "LogConfig", "Memory", "NanoCpus",
    "CapAdd", "CapDrop", "SecurityOpt", "Devices", "GroupAdd", "ShmSize",
)

CONFIG_KEYS = ("Env", "Cmd", "Entrypoint", "ExposedPorts", "Labels",
               "WorkingDir", "User", "Healthcheck")


def write_state(state: dict) -> None:
    payload = {**state,
               "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        destination = DATA_DIR / "update-state.json"
        temporary = DATA_DIR / f".update-state.{os.getpid()}.{time.time_ns()}.tmp"
        temporary.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
        temporary.replace(destination)
    except OSError:
        pass


def wait_until_stopped(client: httpx.Client, container_id: str,
                       timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/containers/{container_id}/json")
        if response.status_code != 200:
            return False
        if not response.json()["State"]["Running"]:
            return True
        time.sleep(1.0)
    return False


def wait_until_running(client: httpx.Client, container_id: str,
                       timeout: float = 180.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/containers/{container_id}/json")
        if response.status_code == 200:
            state = response.json()["State"]
            health = (state.get("Health") or {}).get("Status")
            if state["Running"] and health in (None, "healthy"):
                return True
            if health == "unhealthy":
                return False
            if state.get("ExitCode") not in (None, 0) and not state.get("Restarting"):
                return False
        time.sleep(1.0)
    return False


def successor_payload(old: dict, new_image: str) -> dict:
    config = old.get("Config") or {}
    host_config = old.get("HostConfig") or {}
    payload: dict = {key: config[key] for key in CONFIG_KEYS if config.get(key)}
    payload["Image"] = new_image
    payload["HostConfig"] = {key: host_config[key] for key in HOST_CONFIG_KEYS
                             if host_config.get(key)}
    networks = (old.get("NetworkSettings") or {}).get("Networks") or {}
    endpoints = {}
    for name, endpoint in networks.items():
        aliases = [alias for alias in (endpoint.get("Aliases") or [])
                   if not old["Id"].startswith(alias)]
        endpoints[name] = {"Aliases": aliases} if aliases else {}
    if endpoints:
        payload["NetworkingConfig"] = {"EndpointsConfig": endpoints}
    return payload


def retain_templates(client: httpx.Client, old_id: str) -> None:
    """Keep existing compatible PDFs in the volume before removing their image.

    Only registered template paths are requested. Archive paths are never
    extracted, and the PDF must pass the same identity validation as an import.
    """
    from app.services.document_templates import MAX_BYTES, profiles, resolve, retain_legacy
    for key, profile in profiles().items():
        if resolve(key) is not None:
            continue
        base = "/app/templates/forms" if profile["kind"] == "form" else "/app/backend/seed/models"
        path = f"{base}/{profile['filename']}"
        with client.stream("GET", f"/containers/{old_id}/archive", params={"path": path}) as response:
            if response.status_code == 404:
                continue
            response.raise_for_status()
            content = bytearray()
            for block in response.iter_bytes():
                content.extend(block)
                if len(content) > MAX_BYTES + 1024 * 1024:
                    raise RuntimeError("Existing template archive exceeds the import limit")
        try:
            with tarfile.open(fileobj=io.BytesIO(content)) as archive:
                members = archive.getmembers()
                if len(members) != 1 or not members[0].isfile() or members[0].size > MAX_BYTES:
                    raise ValueError("Unexpected template archive")
                with archive.extractfile(members[0]) as handle:
                    retain_legacy(key, handle.read(MAX_BYTES + 1), f"Previous local container: {path}")
        except Exception as exc:
            raise RuntimeError(f"Could not preserve existing template {key}") from exc


def main() -> int:
    old_id, new_image = sys.argv[1], sys.argv[2]
    client = httpx.Client(
        transport=httpx.HTTPTransport(uds=DOCKER_SOCKET),
        base_url="http://docker", timeout=60.0)

    inspect = client.get(f"/containers/{old_id}/json")
    if inspect.status_code != 200:
        write_state({"phase": "failed", "error": "old container not found"})
        return 1
    old = inspect.json()
    name = (old.get("Name") or "").lstrip("/") or "emcargo"
    aside = f"{name}-previous-{int(time.time())}"
    new_id = None

    try:
        retain_templates(client, old_id)
        write_state({"phase": "stopping", "to_image": new_image})
        client.post(f"/containers/{old_id}/stop", params={"t": 30},
                    timeout=90.0)
        if not wait_until_stopped(client, old_id):
            raise RuntimeError("the running container would not stop")

        rename = client.post(f"/containers/{old_id}/rename",
                             params={"name": aside})
        if rename.status_code not in (204,):
            raise RuntimeError(f"rename failed: HTTP {rename.status_code}")

        create = client.post("/containers/create", params={"name": name},
                             json=successor_payload(old, new_image))
        if create.status_code not in (200, 201):
            raise RuntimeError(
                f"create failed: HTTP {create.status_code} {create.text[:300]}")
        new_id = create.json()["Id"]

        start = client.post(f"/containers/{new_id}/start")
        if start.status_code not in (204, 304):
            raise RuntimeError(f"start failed: HTTP {start.status_code}")
        if not wait_until_running(client, new_id):
            raise RuntimeError("the new container did not become healthy")

        client.delete(f"/containers/{old_id}")
        write_state({"phase": "done", "to_image": new_image,
                     "replaced": old_id[:12]})
        return 0

    except (RuntimeError, httpx.HTTPError) as exc:
        # Put the old container back: an update that fails must leave a
        # working installation.
        if new_id:
            client.delete(f"/containers/{new_id}", params={"force": "true"})
        client.post(f"/containers/{old_id}/rename", params={"name": name})
        client.post(f"/containers/{old_id}/start")
        write_state({"phase": "failed", "to_image": new_image,
                     "error": str(exc)})
        return 1


if __name__ == "__main__":  # pragma: no cover - the container entrypoint
    sys.exit(main())
