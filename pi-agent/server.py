import hmac
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

import psutil
import docker
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import bridge as bridge_module

logger = logging.getLogger("pi-agent")

# ── Arduino bridge (socat) — só ativo no Pi 1, via BRIDGE_ENABLED=true ────────
BRIDGE_ENABLED = bridge_module.env_enabled()
BRIDGE_RECONCILE_SECONDS = 10
# Token opcional partilhado com o backend do dashboard (header X-Agent-Token).
# Se vazio, as ações do bridge ficam como as restantes ações deste agente
# (abertas à LAN); se definido, start/stop exigem o token.
AGENT_TOKEN = os.getenv("AGENT_TOKEN", "")

_bridge: bridge_module.BridgeManager | None = None
if BRIDGE_ENABLED:
    _bridge = bridge_module.BridgeManager(
        port=bridge_module.env_port(),
        baud=bridge_module.env_baud(),
        state_file=os.getenv("BRIDGE_STATE_FILE", "/data/bridge.json"),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop_event = threading.Event()
    thread = None
    if _bridge is not None:
        def supervise() -> None:
            while not stop_event.is_set():
                try:
                    _bridge.reconcile()
                except Exception:  # o supervisor nunca deve morrer
                    logger.exception("Erro no supervisor do bridge")
                stop_event.wait(BRIDGE_RECONCILE_SECONDS)

        thread = threading.Thread(target=supervise, name="bridge-supervisor", daemon=True)
        thread.start()
    yield
    stop_event.set()
    if thread is not None:
        thread.join(timeout=2)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

_boot_time = psutil.boot_time()

try:
    _docker = docker.from_env()
except Exception:
    _docker = None


def _list_containers() -> list[dict]:
    if _docker is None:
        return []
    result = []
    for c in _docker.containers.list(all=True):
        ports = []
        for _proto, bindings in (c.ports or {}).items():
            if bindings:
                for b in bindings:
                    ports.append(f"{b['HostIp']}:{b['HostPort']}")
        result.append({
            "name": c.name,
            "status": c.status,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "ports": ports,
        })
    return result


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    mem = psutil.virtual_memory()
    return {
        "cpu": round(psutil.cpu_percent(interval=0.5), 1),
        "ram_used_gb": round(mem.used / 1024**3, 2),
        "ram_total_gb": round(mem.total / 1024**3, 2),
        "uptime_seconds": int(time.time() - _boot_time),
        "containers": _list_containers(),
    }


@app.post("/containers/{name}/start")
def start_container(name: str):
    if _docker is None:
        raise HTTPException(503, "Docker not available")
    try:
        _docker.containers.get(name).start()
        return {"status": "ok"}
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container {name!r} not found")
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.post("/containers/{name}/stop")
def stop_container(name: str):
    if _docker is None:
        raise HTTPException(503, "Docker not available")
    try:
        _docker.containers.get(name).stop()
        return {"status": "ok"}
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container {name!r} not found")
    except Exception as exc:
        raise HTTPException(500, str(exc))


# ── Arduino bridge (socat) ───────────────────────────────────────────────────

def _require_agent_token(x_agent_token: str | None = Header(default=None)) -> None:
    if not AGENT_TOKEN:
        return
    if x_agent_token is None or not hmac.compare_digest(x_agent_token, AGENT_TOKEN):
        raise HTTPException(401, "Invalid or missing agent token")


def _require_bridge() -> bridge_module.BridgeManager:
    if _bridge is None:
        raise HTTPException(404, "Arduino bridge management is not enabled on this agent")
    return _bridge


_BRIDGE_ERROR_STATUS = {
    "serial_missing": 409,
    "socat_missing": 500,
    "start_failed": 500,
    "stop_failed": 500,
}


@app.get("/bridge/status")
def bridge_status():
    if _bridge is None:
        return {"enabled": False}
    return _bridge.status()


@app.post("/bridge/start", dependencies=[Depends(_require_agent_token)])
def bridge_start():
    manager = _require_bridge()
    try:
        return manager.start()
    except bridge_module.BridgeError as exc:
        raise HTTPException(_BRIDGE_ERROR_STATUS.get(exc.code, 500), exc.message)


@app.post("/bridge/stop", dependencies=[Depends(_require_agent_token)])
def bridge_stop():
    manager = _require_bridge()
    try:
        return manager.stop()
    except bridge_module.BridgeError as exc:
        raise HTTPException(_BRIDGE_ERROR_STATUS.get(exc.code, 500), exc.message)
