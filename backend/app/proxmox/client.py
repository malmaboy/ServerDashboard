import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger(__name__)

PROXMOX_HOST = os.getenv("PROXMOX_HOST", "192.168.1.200")
PROXMOX_PORT = os.getenv("PROXMOX_PORT", "8006")
PROXMOX_USER = os.getenv("PROXMOX_USER", "root@pam")
PROXMOX_PASSWORD = os.getenv("PROXMOX_PASSWORD", "")
PROXMOX_NODE = os.getenv("PROXMOX_NODE", "pve")

BASE_URL = f"https://{PROXMOX_HOST}:{PROXMOX_PORT}/api2/json"

_ticket: str | None = None
_csrf: str | None = None
_ticket_expiry: float = 0.0
_auth_lock = asyncio.Lock()


async def _authenticate() -> tuple[str, str]:
    global _ticket, _csrf, _ticket_expiry
    async with _auth_lock:
        if _ticket and time.time() < _ticket_expiry:
            return _ticket, _csrf
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            r = await client.post(
                f"{BASE_URL}/access/ticket",
                data={"username": PROXMOX_USER, "password": PROXMOX_PASSWORD},
            )
            r.raise_for_status()
            data = r.json()["data"]
            _ticket = data["ticket"]
            _csrf = data["CSRFPreventionToken"]
            _ticket_expiry = time.time() + 3600
            logger.info("Proxmox authentication successful (node=%s)", PROXMOX_NODE)
            return _ticket, _csrf


async def pve_get(path: str) -> list | dict:
    ticket, _ = await _authenticate()
    async with httpx.AsyncClient(
        verify=False,
        timeout=10.0,
        cookies={"PVEAuthCookie": ticket},
    ) as client:
        r = await client.get(f"{BASE_URL}{path}")
        r.raise_for_status()
        return r.json()["data"]
