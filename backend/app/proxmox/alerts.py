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
