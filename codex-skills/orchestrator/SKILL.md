---
name: orchestrator
description: Analyze a user problem, classify the domain, build an execution plan, and route the work to the most relevant Codex skills. Use when a request is broad, ambiguous, cross-functional, or likely to need staged thinking before implementation, especially for software engineering, architecture, code quality, Proxmox, servers, .NET, Python, testing, Azure DevOps, or Linux SSH operations.
---

# Orchestrator

Use this skill as the top-level entry point when the user wants Codex to think in stages: understand the problem, classify it, plan the work, and then choose the best specialist skill or skill chain.

## Workflow

1. Rewrite the request as a concrete problem statement.
2. Classify domain, task type, scope, and risk.
3. Surface constraints, assumptions, and missing information.
4. Produce a short actionable plan.
5. Choose the minimum specialist skill set required.
6. Continue using the selected skill guidance.

## Classification

Classify the request along these axes:

- Domain: software engineering, .NET, Python, testing, code quality, architecture, Azure DevOps, server operations, SSH Linux, Proxmox, mixed.
- Task type: bugfix, implementation, review, troubleshooting, migration, design, hardening, pipeline, refactor, test design.
- Scope: single file, single service, repository, pipeline, infrastructure component, multi-system.
- Risk: low, medium, high.

## Routing Rules

Use exactly the minimum set of specialist skills needed.

- Use `$software-engineering` for general codebase work, debugging, features, refactors, reviews, tests, or repo-wide engineering tasks.
- Use `$dotnet-engineer` for C#, ASP.NET Core, Web API, EF Core, `csproj`, `sln`, NuGet, DI, middleware, and .NET build issues.
- Use `$python-engineer` for Python applications, scripts, APIs, packaging, typing, async code, pytest, and backend tasks.
- Use `$tester-engineer` for regressions, test strategy, coverage gaps, failing tests, and verification planning.
- Use `$azure-devops-engineer` for Azure Pipelines, repos, agents, artifacts, releases, service connections, and CI/CD troubleshooting.
- Use `$server-ops` for Linux servers, services, networking, reverse proxies, logs, hardening, Docker hosts, or deployment issues.
- Use `$ssh-linux-ops` when the work is specifically command-oriented over SSH and needs safe sequencing or command interpretation.
- Use `$proxmox-ops` for Proxmox VE nodes, clusters, VMs, LXCs, storage, bridges, migrations, and virtualization operations.
- Use `$software-architect` for system design, service boundaries, integration strategy, decomposition, ADR-style decisions, and technical direction.
- Use `$code-quality` for maintainability reviews, complexity reduction, standards, smells, consistency, and long-term code health.
- Use `$senior-engineer` when strong tradeoff judgment, risk handling, and pragmatic technical leadership are needed.
- Use `$junior-engineer` when the user wants extra explanation, smaller steps, onboarding-style guidance, or a slower walkthrough.

## Routing Heuristics

- Prefer the most domain-specific skill first.
- Prefer `$software-architect` before implementation when the main uncertainty is structural design.
- Prefer `$tester-engineer` before implementation when the user wants a verification-first approach.
- Prefer `$code-quality` after a feature or bugfix when maintainability review is requested.
- Prefer `$senior-engineer` for ambiguous, risky, or cross-cutting work.
- Prefer `$junior-engineer` for educational, onboarding, or step-by-step execution.
- Use `$software-engineering` last when code still needs to be implemented in a repository after analysis by another specialist.

## Output Format

When using this skill, structure the response like this:

### Problem

State the user's actual problem in one or two sentences.

### Analysis

- Domain
- Task type
- Scope
- Key risks
- Assumptions

### Plan

List 3-6 short execution steps.

### Skill Routing

State which skill to use next and why.

If continuing the work in the same reply, explicitly say which skill guidance you are now following.

## References

- Read [references/routing-matrix.md](./references/routing-matrix.md) when multiple domains overlap.
- Read [references/response-template.md](./references/response-template.md) for the expected orchestration shape.
