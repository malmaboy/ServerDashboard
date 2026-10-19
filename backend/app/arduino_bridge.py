"""Estado e controlo do bridge Arduino <-> TCP (socat) que corre no Raspberry Pi 1.

O socat é gerido pelo pi-agent do Pi 1 (pi-agent/bridge.py); este módulo só fala
HTTP com esse agente, tal como raspberry_pi.py (containers) e ailocal.py (gpu-agent).
O browser nunca fala diretamente com o agente e nunca fornece parâmetros além de
start|stop.
"""
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException

from .raspberry_pi import RASPBERRY_PI_URL

# Token opcional partilhado com o agente (AGENT_TOKEN no pi-agent). Vem do
# ambiente/GitHub Secrets, nunca do código.
AGENT_TOKEN = os.getenv("RASPBERRY_PI_AGENT_TOKEN", "")

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_STATES = ("active", "stopped", "no_device")
_UNSUPPORTED = {"supported": False}


def normalize_bridge_status(data: object) -> dict:
    """Reduz a resposta do agente a um contrato fixo (e tipos seguros)."""
    if not isinstance(data, dict) or not data.get("enabled"):
        return dict(_UNSUPPORTED)

    state = data.get("state")
    devices = data.get("serialDevices")
    if not isinstance(devices, list):
        devices = []
    return {
        "supported": True,
        "state": state if state in _VALID_STATES else "unknown",
        "socatRunning": bool(data.get("socatRunning")),
        "serialPresent": bool(data.get("serialPresent")),
        "serialDevices": [str(d) for d in devices[:8]],
        "port": int(data["port"]) if isinstance(data.get("port"), int) else 5555,
        "baud": int(data["baud"]) if isinstance(data.get("baud"), int) else 9600,
        "desired": bool(data.get("desired")),
        "managed": bool(data.get("managed")),
    }


async def get_arduino_bridge_status() -> dict | None:
    """None = agente do Pi 1 inacessível; {"supported": False} = agente sem a
    gestão do bridge ligada (versão antiga ou BRIDGE_ENABLED=false)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{RASPBERRY_PI_URL}/bridge/status")
            if r.status_code == 404:
                return dict(_UNSUPPORTED)
            r.raise_for_status()
            return normalize_bridge_status(r.json())
    except Exception as exc:
        logger.warning("Arduino bridge status unavailable: %s", exc)
        return None


async def control_arduino_bridge(action: str) -> dict:
    if action not in ("start", "stop"):
        raise ValueError("action must be start or stop")

    headers = {"X-Agent-Token": AGENT_TOKEN} if AGENT_TOKEN else {}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{RASPBERRY_PI_URL}/bridge/{action}", headers=headers)
    except httpx.HTTPError as exc:
        logger.error("Arduino bridge %s: agent unreachable: %s", action, exc)
        raise HTTPException(502, "Agente do Raspberry Pi 1 inacessível")

    if r.status_code == 409:
        raise HTTPException(409, "Arduino não detetado no Pi 1 (sem /dev/ttyACM* nem /dev/ttyUSB*)")
    if r.status_code == 404:
        raise HTTPException(501, "O agente do Pi 1 não tem a gestão do bridge ativa (atualizar pi-agent)")
    if r.status_code in (401, 403):
        raise HTTPException(502, "O agente do Pi 1 rejeitou o token (RASPBERRY_PI_AGENT_TOKEN)")
    if r.status_code >= 400:
        logger.error("Arduino bridge %s failed: HTTP %s %s", action, r.status_code, r.text[:200])
        raise HTTPException(502, "O agente do Pi 1 falhou a executar a ação")

    return normalize_bridge_status(r.json())


@router.get("/api/raspberry-pi/bridge")
async def get_bridge() -> dict:
    return {"arduinoBridge": await get_arduino_bridge_status()}


@router.post("/api/raspberry-pi/bridge/{action}")
async def bridge_action(action: str) -> dict:
    if action not in ("start", "stop"):
        raise HTTPException(400, "action must be start or stop")
    status = await control_arduino_bridge(action)
    logger.info("Arduino bridge %s -> state=%s", action, status.get("state"))
    return {"arduinoBridge": status}
