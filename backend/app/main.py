from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .app_config import APP_CARDS


app = FastAPI(
    title="Proxmox Apps Dashboard API",
    version="1.0.0",
    description="API simples para listar apps deployed no Proxmox.",
)

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


@app.get("/api/apps")
def get_apps() -> dict[str, list[dict[str, str]]]:
    return {"apps": APP_CARDS}
