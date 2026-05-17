import logging
import os

import httpx

RASPBERRY_PI_URL = os.getenv("RASPBERRY_PI_URL", "http://192.168.1.120:9090")

logger = logging.getLogger(__name__)


async def get_raspberry_pi_stats() -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{RASPBERRY_PI_URL}/stats")
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
        logger.warning("Raspberry Pi stats unavailable: %s", exc)
        return None


async def control_pi_container(name: str, action: str) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(f"{RASPBERRY_PI_URL}/containers/{name}/{action}")
        r.raise_for_status()
