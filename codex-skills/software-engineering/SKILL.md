---
name: software-engineering
description: Plan, implement, review, and debug software engineering work across backend, frontend, APIs, tests, refactors, CI, architecture, and repositories. Use when Codex needs to inspect a codebase, propose or apply code changes, review diffs, diagnose failures, write tests, improve maintainability, or orchestrate multi-step engineering tasks.
---

# Software Engineering

Use this skill to handle general software engineering work with a bias toward safe iteration and verification.

## Workflow

1. Inspect the repository before proposing structural changes.
2. Clarify the execution target: bug fix, feature, refactor, review, test coverage, or design.
3. Build a small plan when the task spans multiple files or systems.
4. Implement the smallest change that solves the real problem.
5. Verify with focused tests, builds, or static checks when available.
6. Report outcome, residual risk, and any skipped validation.

## Working Rules

- Prefer reading the local code before inventing abstractions.
- Preserve existing patterns unless they are clearly harmful.
- Prioritize behavioral correctness over cosmetic cleanup.
- Keep changes scoped; avoid opportunistic rewrites unless requested.
- Add tests for regressions when the repository has a testing story.
- If a task is really infra-specific or .NET-specific, read the matching reference file first.

## Common Task Modes

### Implement

- Trace the request to the entry points, models, and side effects.
- Update the narrowest layer that can own the behavior cleanly.
- Include any required tests, fixtures, or docs updates.

### Debug

- Reproduce the issue if feasible.
- Collect the failing path, inputs, logs, stack trace, and recent code changes.
- Form 1-2 hypotheses, then validate them against the code and runtime signals.
- Fix the root cause, not only the symptom.

### Review

- Focus first on correctness, regressions, security, data loss, concurrency, and test gaps.
- Keep summaries short; findings come first.

### Refactor

- Preserve public behavior unless the task explicitly changes it.
- Split risky refactors into preparatory commits or small patches when possible.

## References

- Read [references/general-playbook.md](./references/general-playbook.md) for a compact execution checklist.
- Read [references/task-triage.md](./references/task-triage.md) when the request is ambiguous or spans multiple systems.
