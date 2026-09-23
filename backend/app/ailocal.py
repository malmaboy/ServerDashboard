import logging
import os

import httpx

GPU_AGENT_URL = os.getenv("GPU_AGENT_URL", "http://192.168.0.212:9092")
ODYSSEUS_CONTAINERS = [
    "odysseus-odysseus-1",
    "odysseus-searxng-1",
    "odysseus-chromadb-1",
    "odysseus-ntfy-1",
]

logger = logging.getLogger(__name__)

_NOT_FOUND = {
    "key": "odysseus",
    "displayName": "odysseus",
    "category": "Media & AI",
    "enabled": False,
    "running": False,
    "found": False,
}


async def get_odysseus_autostart() -> dict:
    """Reads container state via the gpu-agent HTTP control endpoint on
    ai-local — this backend's docker.sock only sees docker-host, and
    odysseus runs on a different machine entirely."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{GPU_AGENT_URL}/containers")
            r.raise_for_status()
            containers = {c["name"]: c for c in r.json().get("containers", [])}
    except Exception as exc:
        logger.warning("ai-local agent unavailable: %s", exc)
        return _NOT_FOUND

    found = [containers[name] for name in ODYSSEUS_CONTAINERS if name in containers]
    if not found:
        return _NOT_FOUND

    return {
        "key": "odysseus",
        "displayName": "odysseus",
        "category": "Media & AI",
        "enabled": found[0]["restartPolicy"] in ("unless-stopped", "always"),
        "running": any(c["status"] == "running" for c in found),
        "found": True,
    }


async def toggle_odysseus_autostart() -> dict:
    current = await get_odysseus_autostart()
    turning_on = not current["enabled"]
    policy = "unless-stopped" if turning_on else "no"

    async with httpx.AsyncClient(timeout=10.0) as client:
        for name in ODYSSEUS_CONTAINERS:
            try:
                r = await client.post(
                    f"{GPU_AGENT_URL}/containers/{name}/restart-policy",
                    json={"policy": policy},
                )
                if r.status_code == 404:
                    continue
                r.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Failed to set restart policy for %s: %s", name, exc)

    return {"key": "odysseus", "enabled": turning_on}
