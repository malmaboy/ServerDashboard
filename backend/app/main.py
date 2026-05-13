import asyncio
import json
import logging
import os
import time

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from .app_config import APP_CARDS, AppCard
from .game_servers import list_game_servers, router as game_servers_router
from .proxmox.alerts import (
    check_resource_alerts_discord,
    check_service_transitions,
    compute_resource_alerts,
)
from .proxmox.nodes import control_vm, get_lxcs, get_node_status, get_storage, get_vms
from .proxmox.tasks import get_recent_tasks

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


# ── Health checks ────────────────────────────────────────────────────────────

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
    t0 = time.monotonic()
    health_type = card.get("healthType", "http")
    if health_type.startswith("tcp"):
        host, port_str = card["healthUrl"].rsplit(":", 1)
        online = await _check_tcp(host, int(port_str))
    else:
        online = await _check_http(client, card["healthUrl"])
    latency_ms = round((time.monotonic() - t0) * 1000)
    status = "Online" if online else "Offline"
    logger.debug("%s → %s (%dms)", card["name"], status, latency_ms)
    return {
        "name": card["name"],
        "url": card["url"],
        "imageUrl": card["imageUrl"],
        "description": card["description"],
        "status": status,
        "latencyMs": latency_ms if online else None,
    }


async def _fetch_apps() -> list[dict]:
    async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
        results = await asyncio.gather(
            *[_check_card(client, card) for card in APP_CARDS]
        )
    return list(results)


async def _fetch_proxmox() -> dict:
    host, vms, lxcs, storage, tasks = await asyncio.gather(
        get_node_status(),
        get_vms(),
        get_lxcs(),
        get_storage(),
        get_recent_tasks(),
    )
    alerts = compute_resource_alerts(host, storage)
    return {
        "host": host,
        "vms": vms,
        "lxcs": lxcs,
        "storage": storage,
        "tasks": tasks,
        "alerts": alerts,
    }


# ── REST endpoints ───────────────────────────────────────────────────────────

@app.get("/api/apps")
async def get_apps() -> dict[str, list[dict]]:
    return {"apps": await _fetch_apps()}


@app.get("/api/proxmox/summary")
async def get_proxmox_summary() -> dict:
    return await _fetch_proxmox()


@app.post("/api/proxmox/vms/{vmid}/{action}")
async def vm_action(vmid: int, action: str, vm_type: str = "qemu") -> dict:
    if action not in ("start", "stop", "reboot"):
        raise HTTPException(400, "action must be start, stop or reboot")
    if vm_type not in ("qemu", "lxc"):
        raise HTTPException(400, "vm_type must be qemu or lxc")
    try:
        upid = await control_vm(vmid, vm_type, action)
        logger.info("VM %s %s/%s → %s", action, vm_type, vmid, upid)
        return {"status": "ok", "upid": upid}
    except Exception as exc:
        logger.error("VM action failed: %s", exc)
        raise HTTPException(500, str(exc))


# ── SSE ──────────────────────────────────────────────────────────────────────

@app.get("/api/events")
async def events(request: Request):
    async def generator():
        logger.info("SSE client connected")
        try:
            while True:
                if await request.is_disconnected():
                    logger.info("SSE client disconnected")
                    break

                apps_data, proxmox_data, game_data = await asyncio.gather(
                    _fetch_apps(),
                    _fetch_proxmox(),
                    run_in_threadpool(list_game_servers),
                )

                await asyncio.gather(
                    check_service_transitions(apps_data),
                    check_resource_alerts_discord(proxmox_data.get("alerts", [])),
                )

                yield {"event": "apps", "data": json.dumps({"apps": apps_data})}
                yield {"event": "proxmox", "data": json.dumps(proxmox_data)}
                yield {"event": "game-servers", "data": json.dumps({"gameServers": game_data})}

                await asyncio.sleep(15)
        except asyncio.CancelledError:
            logger.info("SSE generator cancelled")

    return EventSourceResponse(generator())
