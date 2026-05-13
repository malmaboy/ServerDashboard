import logging

from .client import PROXMOX_NODE, pve_get, pve_post

logger = logging.getLogger(__name__)


async def get_node_status() -> dict:
    try:
        data = await pve_get(f"/nodes/{PROXMOX_NODE}/status")
        mem = data.get("memory", {})
        return {
            "cpu": round(data.get("cpu", 0) * 100, 1),
            "ram_used_gb": round(mem.get("used", 0) / 1024**3, 2),
            "ram_total_gb": round(mem.get("total", 0) / 1024**3, 2),
            "uptime_seconds": data.get("uptime", 0),
        }
    except Exception as exc:
        logger.warning("Proxmox node status failed: %s", exc)
        return {}


async def get_vms() -> list[dict]:
    try:
        items = await pve_get(f"/nodes/{PROXMOX_NODE}/qemu")
        return [
            {
                "vmid": item["vmid"],
                "name": item.get("name", f"VM {item['vmid']}"),
                "status": item.get("status", "unknown"),
                "cpu": round(item.get("cpu", 0) * 100, 1),
                "ram_used_gb": round(item.get("mem", 0) / 1024**3, 2),
                "ram_max_gb": round(item.get("maxmem", 0) / 1024**3, 2),
                "type": "qemu",
            }
            for item in sorted(items, key=lambda x: x["vmid"])
        ]
    except Exception as exc:
        logger.warning("Proxmox VMs failed: %s", exc)
        return []


async def get_lxcs() -> list[dict]:
    try:
        items = await pve_get(f"/nodes/{PROXMOX_NODE}/lxc")
        return [
            {
                "vmid": item["vmid"],
                "name": item.get("name", f"LXC {item['vmid']}"),
                "status": item.get("status", "unknown"),
                "cpu": round(item.get("cpu", 0) * 100, 1),
                "ram_used_gb": round(item.get("mem", 0) / 1024**3, 2),
                "ram_max_gb": round(item.get("maxmem", 0) / 1024**3, 2),
                "type": "lxc",
            }
            for item in sorted(items, key=lambda x: x["vmid"])
        ]
    except Exception as exc:
        logger.warning("Proxmox LXCs failed: %s", exc)
        return []


async def get_storage() -> list[dict]:
    try:
        items = await pve_get(f"/nodes/{PROXMOX_NODE}/storage")
        result = []
        for item in items:
            if not item.get("active"):
                continue
            total = item.get("total", 0)
            used = item.get("used", 0)
            result.append({
                "name": item["storage"],
                "type": item.get("type", ""),
                "total_gb": round(total / 1024**3, 1),
                "used_gb": round(used / 1024**3, 1),
                "avail_gb": round(item.get("avail", 0) / 1024**3, 1),
                "pct": round(used / total * 100, 1) if total else 0,
            })
        return sorted(result, key=lambda x: x["name"])
    except Exception as exc:
        logger.warning("Proxmox storage failed: %s", exc)
        return []


async def control_vm(vmid: int, vm_type: str, action: str) -> str | None:
    """Start, stop or reboot a VM or LXC. Returns the Proxmox task UPID."""
    if action not in ("start", "stop", "reboot"):
        raise ValueError(f"Invalid action: {action}")
    if vm_type not in ("qemu", "lxc"):
        raise ValueError(f"Invalid vm_type: {vm_type}")
    path = f"/nodes/{PROXMOX_NODE}/{vm_type}/{vmid}/status/{action}"
    return await pve_post(path)
