import time
import psutil
import docker
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

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
