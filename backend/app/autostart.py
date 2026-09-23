import docker
from docker.errors import NotFound
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from .ailocal import get_odysseus_autostart, toggle_odysseus_autostart

router = APIRouter()

AUTOSTART_ON_POLICY = "unless-stopped"
AUTOSTART_OFF_POLICY = "no"


AUTOSTART_SERVICES: list[dict] = [
    {"key": "zomboid", "displayName": "Project Zomboid", "category": "Game Servers", "containerNames": ["zomboid-server"]},
    {"key": "zomboid-b42", "displayName": "Project Zomboid B42", "category": "Game Servers", "containerNames": ["zomboid-b42-server"]},
    {"key": "palworld", "displayName": "Palworld", "category": "Game Servers", "containerNames": ["palworld-server"]},
    {"key": "jellyfin", "displayName": "Jellyfin", "category": "Media & AI", "containerNames": ["jellyfin"]},
    {"key": "immich", "displayName": "Immich", "category": "Media & AI", "containerNames": ["immich-server", "immich-machine-learning", "immich-redis", "immich-postgres"]},
    {"key": "n8n", "displayName": "n8n", "category": "Infraestrutura", "containerNames": ["n8n"]},
    {"key": "arr", "displayName": "Arr Stack", "category": "Downloads", "containerNames": ["gluetun", "qbittorrent", "prowlarr", "sonarr", "radarr", "flaresolverr"]},
    {"key": "paperless", "displayName": "Paperless", "category": "Infraestrutura", "containerNames": ["paperless-webserver", "paperless-broker", "paperless-gotenberg", "paperless-tika"]},
    {"key": "vaultwarden", "displayName": "Vaultwarden", "category": "Infraestrutura", "containerNames": ["vaultwarden"]},
    {"key": "uptime-kuma", "displayName": "Uptime Kuma", "category": "Infraestrutura", "containerNames": ["uptime-kuma"]},
    {"key": "pgadmin", "displayName": "PgAdmin", "category": "Infraestrutura", "containerNames": ["pgadmin"]},
    {"key": "seq", "displayName": "Seq", "category": "Infraestrutura", "containerNames": ["seq"]},
    {"key": "beszel", "displayName": "Beszel", "category": "Infraestrutura", "containerNames": ["beszel-hub"]},
    {"key": "homepage", "displayName": "Homepage", "category": "Infraestrutura", "containerNames": ["homepage"]},
]

_SERVICES_BY_KEY = {svc["key"]: svc for svc in AUTOSTART_SERVICES}


def _client() -> docker.DockerClient:
    try:
        return docker.from_env()
    except Exception as exc:
        raise HTTPException(503, f"Docker daemon unavailable: {exc}")


def _list_local_autostart_services() -> list[dict]:
    """Sync helper — safe to call from a thread pool. docker-host services only."""
    try:
        client = docker.from_env()
    except Exception:
        return []

    result = []
    for svc in AUTOSTART_SERVICES:
        containers = []
        for name in svc["containerNames"]:
            try:
                containers.append(client.containers.get(name))
            except NotFound:
                continue

        if not containers:
            result.append({
                "key": svc["key"],
                "displayName": svc["displayName"],
                "category": svc["category"],
                "enabled": False,
                "running": False,
                "found": False,
            })
            continue

        primary = containers[0]
        policy = primary.attrs.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "")
        result.append({
            "key": svc["key"],
            "displayName": svc["displayName"],
            "category": svc["category"],
            "enabled": policy in (AUTOSTART_ON_POLICY, "always"),
            "running": any(c.status == "running" for c in containers),
            "found": True,
        })
    return result


async def list_autostart_services() -> list[dict]:
    local = await run_in_threadpool(_list_local_autostart_services)
    remote = await get_odysseus_autostart()
    return local + [remote]


@router.get("/api/autostart")
async def get_autostart_services() -> dict:
    return {"services": await list_autostart_services()}


def _toggle_local(svc: dict, key: str) -> dict:
    client = _client()
    containers = []
    for name in svc["containerNames"]:
        try:
            containers.append(client.containers.get(name))
        except NotFound:
            continue

    if not containers:
        raise HTTPException(404, "No containers found for this service")

    current_policy = containers[0].attrs.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", "")
    turning_on = current_policy not in (AUTOSTART_ON_POLICY, "always")
    policy = AUTOSTART_ON_POLICY if turning_on else AUTOSTART_OFF_POLICY

    for container in containers:
        container.update(restart_policy={"Name": policy})

    return {"key": key, "enabled": turning_on}


@router.post("/api/autostart/{key}/toggle")
async def toggle_autostart(key: str) -> dict:
    if key == "odysseus":
        return await toggle_odysseus_autostart()

    svc = _SERVICES_BY_KEY.get(key)
    if svc is None:
        raise HTTPException(404, "Unknown service")

    return await run_in_threadpool(_toggle_local, svc, key)
