import logging
import os
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
ALERT_COOLDOWN_SECS = 3600

_prev_service_states: dict[str, str] = {}
_alert_sent_at: dict[str, float] = {}


async def _post_discord(message: str, color: int) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                DISCORD_WEBHOOK_URL,
                json={
                    "embeds": [{
                        "description": message,
                        "color": color,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }]
                },
            )
    except Exception as exc:
        logger.warning("Discord notification failed: %s", exc)


async def check_service_transitions(apps: list[dict]) -> None:
    """Detect Online→Offline and Offline→Online transitions and notify Discord."""
    for app in apps:
        name = app["name"]
        status = app["status"]
        prev = _prev_service_states.get(name)
        if prev is not None:
            if prev == "Online" and status == "Offline":
                logger.warning("Service went offline: %s", name)
                await _post_discord(f"🔴 **{name}** ficou offline", color=15158332)
            elif prev == "Offline" and status == "Online":
                logger.info("Service recovered: %s", name)
                await _post_discord(f"🟢 **{name}** voltou online", color=5763719)
        _prev_service_states[name] = status


def compute_resource_alerts(host: dict, storage: list[dict]) -> list[dict]:
    """Return active resource alerts for the frontend."""
    alerts: list[dict] = []

    if host and host.get("ram_total_gb"):
        pct = host["ram_used_gb"] / host["ram_total_gb"] * 100
        if pct >= 85:
            alerts.append({
                "key": "ram",
                "level": "critical",
                "message": f"Host RAM em {pct:.0f}% — {host['ram_used_gb']:.1f} / {host['ram_total_gb']:.1f} GB",
            })

    for s in storage:
        if s.get("pct", 0) >= 80:
            alerts.append({
                "key": f"storage_{s['name']}",
                "level": "warning",
                "message": f"Storage '{s['name']}' em {s['pct']}% — {s['used_gb']} / {s['total_gb']} GB",
            })

    return alerts


async def check_resource_alerts_discord(alerts: list[dict]) -> None:
    """Send Discord alerts for resource conditions, debounced to once per hour per key."""
    now = time.time()
    for alert in alerts:
        key = alert["key"]
        if now - _alert_sent_at.get(key, 0) >= ALERT_COOLDOWN_SECS:
            color = 15158332 if alert["level"] == "critical" else 16776960
            await _post_discord(f"⚠️ {alert['message']}", color=color)
            _alert_sent_at[key] = now
