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
from .raspberry_pi import (
    control_pi_container,
    control_pi_2_container,
    get_raspberry_pi_stats,
    get_raspberry_pi_2_stats,
)
from .proxmox.alerts import (
    check_resource_alerts_discord,
    check_service_transitions,
    compute_resource_alerts,
)
from .proxmox.nodes import control_vm, get_disk_layout, get_lxcs, get_node_status, get_storage, get_vms
from .proxmox.tasks import get_recent_tasks
from .ups import get_ups_summary
from .gpu import get_gpu_stats

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
    disks = await get_disk_layout(storage)
    alerts = compute_resource_alerts(host, storage)
    return {
        "host": host,
        "vms": vms,
        "lxcs": lxcs,
        "storage": storage,
        "disks": disks,
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


@app.get("/api/ups/summary")
async def get_ups() -> dict:
    return {"ups": await get_ups_summary()}


@app.get("/api/gpu/summary")
async def get_gpu() -> dict:
    return {"gpu": await get_gpu_stats()}


@app.post("/api/raspberry-pi/containers/{name}/{action}")
async def pi_container_action(name: str, action: str) -> dict:
    if action not in ("start", "stop"):
        raise HTTPException(400, "action must be start or stop")
    try:
        await control_pi_container(name, action)
        logger.info("Pi container %s %s", action, name)
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Pi container action failed: %s", exc)
        raise HTTPException(500, str(exc))


@app.post("/api/raspberry-pi-2/containers/{name}/{action}")
async def pi_2_container_action(name: str, action: str) -> dict:
    if action not in ("start", "stop"):
        raise HTTPException(400, "action must be start or stop")
    try:
        await control_pi_2_container(name, action)
        logger.info("Pi 2 container %s %s", action, name)
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Pi 2 container action failed: %s", exc)
        raise HTTPException(500, str(exc))


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

                apps_data, proxmox_data, game_data, pi_data, pi2_data, ups_data, gpu_data = await asyncio.gather(
                    _fetch_apps(),
                    _fetch_proxmox(),
                    run_in_threadpool(list_game_servers),
                    get_raspberry_pi_stats(),
                    get_raspberry_pi_2_stats(),
                    get_ups_summary(),
                    get_gpu_stats(),
                )

                await asyncio.gather(
                    check_service_transitions(apps_data),
                    check_resource_alerts_discord(proxmox_data.get("alerts", [])),
                )

                yield {"event": "apps", "data": json.dumps({"apps": apps_data})}
                yield {"event": "proxmox", "data": json.dumps(proxmox_data)}
                yield {"event": "game-servers", "data": json.dumps({"gameServers": game_data})}
                yield {"event": "raspberry-pi", "data": json.dumps({"raspberryPi": pi_data})}
                yield {"event": "raspberry-pi-2", "data": json.dumps({"raspberryPi2": pi2_data})}
                yield {"event": "ups", "data": json.dumps({"ups": ups_data})}
                yield {"event": "gpu", "data": json.dumps({"gpu": gpu_data})}

                await asyncio.sleep(15)
        except asyncio.CancelledError:
            logger.info("SSE generator cancelled")

    return EventSourceResponse(generator())
