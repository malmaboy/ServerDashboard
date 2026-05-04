import asyncio
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .app_config import APP_CARDS
from .game_servers import router as game_servers_router

app = FastAPI(
    title="HomeLab Dashboard API",
    version="1.0.0",
    description="API to list and health-check homelab services.",
)

app.include_router(game_servers_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


async def _check_http(client: httpx.AsyncClient, url: str) -> bool:
    try:
        r = await client.get(url)
        return r.status_code < 500
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


@app.get("/api/apps")
async def get_apps() -> dict[str, list[dict]]:
    results = []
    async with httpx.AsyncClient(verify=False, timeout=3.0) as client:
        for card in APP_CARDS:
            health_type = card.get("healthType", "http")

            if health_type == "tcp":
                host, port_str = card["healthUrl"].rsplit(":", 1)
                online = await _check_tcp(host, int(port_str))
            else:
                online = await _check_http(client, card["healthUrl"])

            results.append({
                "name": card["name"],
                "url": card["url"],
                "imageUrl": card["imageUrl"],
                "description": card["description"],
                "status": "Online" if online else "Offline",
            })
    return {"apps": results}
