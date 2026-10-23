"""Read-only summary of both Raspberry Pis, for other services (e.g. SENTINEL).

Only GET ``/stats`` of pi-stats is used; start/stop endpoints are never called.
A Pi that fails is reported as ``reachable: false`` with a short reason and never
affects the other one.
"""

import asyncio
import logging
import math

import httpx

from . import raspberry_pi

logger = logging.getLogger(__name__)

# Per-Pi hard cap (seconds) for the whole request; keeps a dead Pi from delaying the other.
PI_TIMEOUT_SECONDS = 3.5

# (id, display name, name of the URL attribute in raspberry_pi). The URL is looked up at
# call time so the single configuration in raspberry_pi.py stays the source of truth.
PIS: tuple[tuple[str, str, str], ...] = (
    ("pi1", "Raspberry Pi 1 — Pi-hole", "RASPBERRY_PI_URL"),
    ("pi2", "Raspberry Pi 2 — GardenAssistant (prod)", "RASPBERRY_PI_2_URL"),
)


def _number(value: object) -> float | None:
    """A finite, non-negative real number, else None (bool, NaN, inf, negatives rejected)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) and value >= 0 else None


def _ram_pct(used: float | None, total: float | None) -> float | None:
    if used is None or total is None or total <= 0:
        return None
    pct = used / total * 100
    return round(pct, 1) if math.isfinite(pct) else None


def _containers(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    result = []
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        status = item.get("status")
        result.append({"name": item["name"], "status": status if isinstance(status, str) else None})
    return result


def build_pi_summary(pi_id: str, name: str, payload: object) -> dict:
    """Turn a raw /stats payload into the public per-Pi shape (reachable: true)."""
    if not isinstance(payload, dict):
        raise ValueError("invalid response")
    used = _number(payload.get("ram_used_gb"))
    total = _number(payload.get("ram_total_gb"))
    uptime = _number(payload.get("uptime_seconds"))
    return {
        "id": pi_id,
        "name": name,
        "reachable": True,
        "cpu": _number(payload.get("cpu")),
        "ram_used_gb": used,
        "ram_total_gb": total,
        "ram_pct": _ram_pct(used, total),
        "uptime_seconds": int(uptime) if uptime is not None else None,
        "containers": _containers(payload.get("containers")),
    }


def _unreachable(pi_id: str, name: str, error: str) -> dict:
    return {"id": pi_id, "name": name, "reachable": False, "error": error}


def _short_error(exc: BaseException) -> str:
    """A short reason that never includes URLs, hosts or other details."""
    if isinstance(exc, (asyncio.TimeoutError, httpx.TimeoutException)):
        return "timeout"
    if isinstance(exc, httpx.ConnectError):
        return "connection failed"
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http {exc.response.status_code}"
    if isinstance(exc, ValueError):  # bad JSON (JSONDecodeError) or non-dict payload
        return "invalid response"
    return "unavailable"


async def _summarize_pi(pi_id: str, name: str, url_attr: str) -> dict:
    try:
        url = getattr(raspberry_pi, url_attr)
        payload = await asyncio.wait_for(
            raspberry_pi.fetch_pi_stats_payload(url, timeout=PI_TIMEOUT_SECONDS),
            timeout=PI_TIMEOUT_SECONDS + 0.5,
        )
        return build_pi_summary(pi_id, name, payload)
    except Exception as exc:
        logger.warning("%s summary unavailable: %s", pi_id, type(exc).__name__)
        return _unreachable(pi_id, name, _short_error(exc))


async def get_pis_summary() -> dict:
    """Query both Pis concurrently; never raises."""
    try:
        results = await asyncio.gather(*(_summarize_pi(*pi) for pi in PIS))
        return {"pis": list(results)}
    except Exception as exc:  # defensive: the route must not return a 500
        logger.error("pis summary failed: %s", type(exc).__name__)
        return {"pis": [_unreachable(pi_id, name, "unavailable") for pi_id, name, _ in PIS]}
