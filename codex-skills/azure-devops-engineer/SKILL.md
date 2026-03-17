---
name: azure-devops-engineer
description: Plan, troubleshoot, and improve Azure DevOps work across pipelines, repositories, pull requests, service connections, agents, artifacts, releases, boards, and deployment flow. Use when Codex needs to analyze CI/CD failures, edit Azure Pipelines YAML, reason about build agents, or guide repository and delivery workflows in Azure DevOps.
---

# Azure DevOps Engineer

Use this skill for Azure DevOps delivery and pipeline work with emphasis on failure isolation, safe rollout, and environment awareness.

## Workflow

1. Identify the failing or target stage: repo, PR, build, test, artifact, release, or deploy.
2. Confirm whether the issue is YAML logic, agent environment, credentials, permissions, or application build behavior.
3. Map dependencies across stages and environments.
4. Propose the smallest pipeline or config change that solves the problem.
5. Define the verification path for the next run.

## Working Rules

- Separate pipeline logic problems from application build problems.
- Check branch filters, triggers, variables, templates, and stage conditions together.
- Treat service connections, secrets, and permissions as first-class suspects.
- For self-hosted agents, distinguish agent health from job definition issues.
- Keep deployment and rollback steps explicit.

## References

- Read [references/pipeline-debugging.md](./references/pipeline-debugging.md) for failure triage.
- Read [references/yaml-review-checklist.md](./references/yaml-review-checklist.md) for Azure Pipelines review prompts.
