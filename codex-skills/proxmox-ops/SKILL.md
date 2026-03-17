---
name: proxmox-ops
description: Operate and troubleshoot Proxmox VE environments including hosts, clusters, VMs, LXCs, storage, networking, backups, replication, and migrations. Use when Codex needs to plan, review, diagnose, or document work involving Proxmox nodes, virtualization, templates, bridges, ZFS, Ceph, HA, or maintenance procedures.
---

# Proxmox Ops

Use this skill for Proxmox planning and operations tasks with an emphasis on safety, change sequencing, and rollback awareness.

## Workflow

1. Identify scope: single node, cluster, VM, LXC, storage, or networking.
2. Confirm the change type: inspect, create, migrate, tune, backup, restore, or troubleshoot.
3. Map dependencies before action: storage backend, bridge, VLAN, HA, replication, backup schedule.
4. Prefer read-only checks first, then plan the smallest reversible change.
5. Document rollback, maintenance window, and post-change verification.

## Operational Rules

- Treat production cluster changes as high risk until proven otherwise.
- Distinguish host-level issues from guest-level issues early.
- Verify storage capacity, quorum, and backup health before migrations or upgrades.
- For networking tasks, map physical NICs, Linux bridges, VLAN tags, firewall rules, and guest config together.
- For VM or LXC incidents, separate compute, disk, network, and boot chain symptoms.
- Avoid destructive commands unless explicitly requested.

## Common Task Modes

### Troubleshooting

- Start with symptoms, affected node(s), and recent change history.
- Check host health, storage state, cluster state, and guest status in that order.
- Narrow to one failing plane: CPU/memory, storage, network, or orchestration.

### Provisioning

- Define template/base image, CPU, RAM, disk, network, backup policy, and tags.
- Prefer repeatable conventions for naming, storage, and bridge selection.

### Maintenance

- Validate backups and cluster health before upgrades or migrations.
- Sequence node-by-node work and confirm service placement impact.

## References

- Read [references/proxmox-checklist.md](./references/proxmox-checklist.md) for a concise incident and maintenance checklist.
- Read [references/storage-and-networking.md](./references/storage-and-networking.md) for storage and bridge decision points.
