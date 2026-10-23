import logging
import os

import httpx

RASPBERRY_PI_URL = os.getenv("RASPBERRY_PI_URL", "http://192.168.0.130:9090")
RASPBERRY_PI_2_URL = os.getenv("RASPBERRY_PI_2_URL", "http://192.168.0.183:9090")

logger = logging.getLogger(__name__)


async def _get_pi_stats(url: str, label: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{url}/stats")
            r.raise_for_status()
            data = r.json()
            return {
                "cpu": data.get("cpu", 0),
                "ram_used_gb": data.get("ram_used_gb", 0),
                "ram_total_gb": data.get("ram_total_gb", 0),
                "uptime_seconds": data.get("uptime_seconds", 0),
                "containers": data.get("containers", []),
            }
    except Exception as exc:
        logger.warning("%s stats unavailable: %s", label, exc)
        return None


async def fetch_pi_stats_payload(url: str, timeout: float = 3.0) -> object:
    """GET ``{url}/stats`` and return the decoded JSON as-is.

    Unlike ``_get_pi_stats`` this does not swallow errors or fill in defaults, so
    callers can tell "unreachable" apart from "reported zero". Read-only: only
    the /stats endpoint is ever requested.
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{url}/stats")
        r.raise_for_status()
        return r.json()


async def get_raspberry_pi_stats() -> dict | None:
    return await _get_pi_stats(RASPBERRY_PI_URL, "Raspberry Pi")


async def get_raspberry_pi_2_stats() -> dict | None:
    return await _get_pi_stats(RASPBERRY_PI_2_URL, "Raspberry Pi 2")


async def control_pi_container(name: str, action: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{RASPBERRY_PI_URL}/containers/{name}/{action}")
        r.raise_for_status()


async def control_pi_2_container(name: str, action: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{RASPBERRY_PI_2_URL}/containers/{name}/{action}")
        r.raise_for_status()
