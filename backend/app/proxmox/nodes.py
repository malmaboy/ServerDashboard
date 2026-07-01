import logging
import os

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


# Which Proxmox storage pool lives on which physical device
_STORAGE_TO_DISK: dict[str, str] = {
    "local":     "/dev/nvme0n1",
    "local-lvm": "/dev/nvme0n1",
    "hdd4tb":    "/dev/sda",
    "nas":       "/dev/sda",
}

# Human-readable service labels for each pool
_POOL_LABELS: dict[str, str] = {
    "local":     "Proxmox OS, ISOs, Backups",
    "local-lvm": "VMs & LXCs",
    "hdd4tb":    "Storage pool (sda2)",
    "nas":       "NAS / Samba (sda1)",
}

# Mount points that are bind-mounted into this container (docker-host).
# NAS lives on the Proxmox host's own disk (sda1), not on docker-host, so it's
# reported via the "nas" Proxmox storage pool above instead of a local mount.
_MOUNT_POINTS: list[dict] = [
    {"name": "Immich", "disk": "/dev/sda", "path": "/mnt/immich", "service": "Immich (photos + DB)"},
]


def _statvfs(path: str) -> dict | None:
    try:
        st = os.statvfs(path)
        total = st.f_blocks * st.f_frsize
        avail = st.f_bavail * st.f_frsize
        used = total - avail
        return {
            "total_gb": round(total / 1024**3, 1),
            "used_gb": round(used / 1024**3, 1),
            "pct": round(used / total * 100, 1) if total else 0,
        }
    except OSError:
        return None


async def get_disk_layout(storage: list[dict]) -> list[dict]:
    try:
        raw_disks = await pve_get(f"/nodes/{PROXMOX_NODE}/disks/list")
    except Exception as exc:
        logger.warning("Disk list failed: %s", exc)
        return []

    disks: dict[str, dict] = {}
    for d in raw_disks:
        dev = d.get("devpath", "")
        if not dev:
            continue
        model = (d.get("model") or d.get("vendor") or "Unknown").strip()
        disks[dev] = {
            "dev": dev,
            "model": model,
            "size_gb": round(d.get("size", 0) / 1024**3),
            "type": d.get("type", ""),
            "health": d.get("health", ""),
            "partitions": [],
        }

    pool_by_name = {s["name"]: s for s in storage}
    for pool_name, disk_dev in _STORAGE_TO_DISK.items():
        if disk_dev not in disks or pool_name not in pool_by_name:
            continue
        s = pool_by_name[pool_name]
        disks[disk_dev]["partitions"].append({
            "name": pool_name,
            "service": _POOL_LABELS.get(pool_name, ""),
            "total_gb": s["total_gb"],
            "used_gb": s["used_gb"],
            "pct": s["pct"],
            "source": "proxmox",
        })

    for mp in _MOUNT_POINTS:
        disk_dev = mp["disk"]
        if disk_dev not in disks:
            continue
        stats = _statvfs(mp["path"]) if mp["path"] else None
        partition: dict = {
            "name": mp["name"],
            "service": mp["service"],
            "source": "mount",
        }
        if stats:
            partition.update(stats)
        else:
            partition.update({"total_gb": 0, "used_gb": 0, "pct": 0, "error": "unavailable"})
        disks[disk_dev]["partitions"].append(partition)

    return sorted(disks.values(), key=lambda d: (d["type"] != "nvme", d["dev"]))


async def control_vm(vmid: int, vm_type: str, action: str) -> str | None:
    """Start, stop or reboot a VM or LXC. Returns the Proxmox task UPID."""
    if action not in ("start", "stop", "reboot"):
        raise ValueError(f"Invalid action: {action}")
    if vm_type not in ("qemu", "lxc"):
        raise ValueError(f"Invalid vm_type: {vm_type}")
    path = f"/nodes/{PROXMOX_NODE}/{vm_type}/{vmid}/status/{action}"
    return await pve_post(path)
