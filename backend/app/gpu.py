import logging
import os

import httpx

GPU_AGENT_URL = os.getenv("GPU_AGENT_URL", "http://192.168.0.212:9092")

logger = logging.getLogger(__name__)


async def get_gpu_stats() -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{GPU_AGENT_URL}/gpu/stats")
            r.raise_for_status()
            data = r.json()
            return {
                "name": data.get("name", ""),
                "gpuUtilPercent": data.get("gpuUtilPercent", 0),
                "memUtilPercent": data.get("memUtilPercent", 0),
                "vramUsedMb": data.get("vramUsedMb", 0),
                "vramTotalMb": data.get("vramTotalMb", 0),
                "temperatureC": data.get("temperatureC", 0),
                "powerW": data.get("powerW", 0),
            }
    except Exception as exc:
        logger.warning("GPU stats unavailable: %s", exc)
        return None
