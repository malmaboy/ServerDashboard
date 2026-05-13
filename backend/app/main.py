import asyncio
import logging
import os

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .app_config import APP_CARDS, AppCard
from .game_servers import router as game_servers_router
from .proxmox.nodes import get_lxcs, get_node_status, get_storage, get_vms

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN", "*")

app = FastAPI(
    title="HomeLab Dashboard API",
    version="2.0.0",
    description="API to list and health-check homelab services.",
)

app.include_router(game_servers_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


async def _check_http(client: httpx.AsyncClient, url: str) -> bool:
    try:
        r = await client.get(url)
        return r.status_code < 400
    except Exception:
        return False


async def _check_tcp(host: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=3.0
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


async def _check_card(client: httpx.AsyncClient, card: AppCard) -> dict:
    health_type = card.get("healthType", "http")
    if health_type.startswith("tcp"):
        host, port_str = card["healthUrl"].rsplit(":", 1)
        online = await _check_tcp(host, int(port_str))
    else:
        online = await _check_http(client, card["healthUrl"])
    status = "Online" if online else "Offline"
    logger.debug("%s → %s", card["name"], status)
    return {
        "name": card["name"],
        "url": card["url"],
        "imageUrl": card["imageUrl"],
        "description": card["description"],
        "status": status,
    }


@app.get("/api/apps")
async def get_apps() -> dict[str, list[dict]]:
    async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
        results = await asyncio.gather(
            *[_check_card(client, card) for card in APP_CARDS]
        )
    return {"apps": list(results)}


@app.get("/api/proxmox/summary")
async def get_proxmox_summary() -> dict:
    host, vms, lxcs, storage = await asyncio.gather(
        get_node_status(),
        get_vms(),
        get_lxcs(),
        get_storage(),
    )
    return {"host": host, "vms": vms, "lxcs": lxcs, "storage": storage}
