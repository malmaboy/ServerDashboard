---
name: server-ops
description: Operate, troubleshoot, harden, and document server infrastructure across Linux hosts, services, networking, containers, storage, observability, and deployment pipelines. Use when Codex needs to investigate incidents, analyze logs, tune services, review system configuration, or plan changes for servers, VMs, reverse proxies, firewalls, or self-hosted platforms.
---

# Server Ops

Use this skill for server administration and SRE-style tasks with a bias toward observability, safety, and reversible changes.

## Workflow

1. Identify the service boundary: host, container, reverse proxy, application, or network edge.
2. Confirm the task type: incident response, setup, hardening, migration, capacity, or performance.
3. Gather signals first: service status, logs, disk, memory, CPU, network, and recent deploy/change history.
4. Isolate the failing layer before proposing a fix.
5. Plan rollback and verification before making non-trivial changes.

## Working Rules

- Start read-only when the impact is unknown.
- Separate symptoms from causes and host issues from app issues.
- For outages, define blast radius and user impact before optimization.
- When editing config, preserve a clear before/after explanation.
- Favor incremental hardening over broad one-shot changes.

## Common Task Modes

### Incident Response

- Confirm whether the issue is availability, latency, saturation, storage, DNS, TLS, or deployment related.
- Build a timeline from logs, restarts, and recent config or release changes.

### Configuration

- Map the config chain end-to-end: systemd, env files, reverse proxy, app config, secrets, firewall, DNS.

### Hardening

- Review exposed ports, auth paths, TLS, backups, updates, logging, and least-privilege boundaries.

## References

- Read [references/server-checklist.md](./references/server-checklist.md) for general incident and change-control steps.
- Read [references/linux-networking.md](./references/linux-networking.md) for network and service troubleshooting patterns.
