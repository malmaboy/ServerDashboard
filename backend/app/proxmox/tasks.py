import logging

from .client import PROXMOX_NODE, pve_get

logger = logging.getLogger(__name__)

_TYPE_LABELS: dict[str, str] = {
    "qmstart": "VM Start",
    "qmstop": "VM Stop",
    "qmreboot": "VM Reboot",
    "qmcreate": "VM Create",
    "qmdestroy": "VM Delete",
    "qmmove": "Disk Move",
    "vzstart": "LXC Start",
    "vzstop": "LXC Stop",
    "vzreboot": "LXC Reboot",
    "vzcreate": "LXC Create",
    "vzdestroy": "LXC Delete",
    "vzdump": "Backup",
    "vzsnapshot": "Snapshot",
    "vncproxy": "Console",
    "download": "Download",
}


async def get_recent_tasks(limit: int = 8) -> list[dict]:
    try:
        items = await pve_get(f"/nodes/{PROXMOX_NODE}/tasks?limit={limit}")
        result = []
        for item in items:
            start = item.get("starttime", 0)
            end = item.get("endtime", 0)
            raw_status = item.get("status", "")

            if not end:
                status_norm = "running"
            elif raw_status == "OK":
                status_norm = "ok"
            else:
                status_norm = "failed"

            raw_type = item.get("type", "")
            result.append({
                "type": raw_type,
                "type_label": _TYPE_LABELS.get(raw_type, raw_type),
                "id": str(item.get("id", "")),
                "user": item.get("user", ""),
                "status": status_norm,
                "starttime": start,
                "duration_secs": (end - start) if end and start else None,
            })
        return result
    except Exception as exc:
        logger.warning("Proxmox tasks failed: %s", exc)
        return []
