---
name: ssh-linux-ops
description: Safely investigate and operate Linux systems over SSH, including services, logs, networking, disks, permissions, processes, deployments, and routine maintenance. Use when Codex needs to guide or perform remote Linux troubleshooting, build an SSH command sequence, analyze command output, or plan low-risk operational changes.
---

# SSH Linux Ops

Use this skill for SSH-oriented Linux work where command safety, sequencing, and diagnosis matter.

## Workflow

1. Clarify target host, service, and impact.
2. Start with read-only commands to gather evidence.
3. Narrow the failure plane: service, process, disk, network, auth, or deploy.
4. Propose commands in a safe order.
5. Make changes only after defining rollback and verification.

## Working Rules

- Prefer read-only inspection before mutation.
- Group commands by purpose so the user can understand the sequence.
- For outages, identify blast radius before optimization.
- For permissions issues, verify user, group, path ownership, and service account assumptions together.
- For networking, separate local host issues from upstream or DNS problems.

## References

- Read [references/ssh-checklist.md](./references/ssh-checklist.md) for safe command flow.
- Read [references/linux-triage.md](./references/linux-triage.md) for service and system debugging prompts.
