---
name: python-engineer
description: Build, debug, review, and improve Python applications across APIs, automation, CLIs, services, data processing, packaging, tests, and repository structure. Use when Codex needs to work on Python code, virtual environments, dependency issues, async flows, typing, pytest, packaging, or common backend and scripting tasks.
---

# Python Engineer

Use this skill for Python-focused engineering tasks with attention to readability, correctness, and fast verification.

## Workflow

1. Inspect the repository layout, entry points, and dependency files.
2. Confirm the task type: bugfix, feature, refactor, review, test, or packaging.
3. Trace the execution path before editing code.
4. Apply the smallest correct change.
5. Verify with the fastest reliable check, usually tests or a focused command.

## Working Rules

- Respect the repository's formatter, linter, and test conventions.
- Prefer clear Python over clever Python.
- Check typing, exceptions, resource cleanup, and async boundaries around changes.
- For API work, trace request validation, business logic, persistence, and response shape.
- For scripts and automation, verify idempotency and failure handling.

## References

- Read [references/python-playbook.md](./references/python-playbook.md) for debugging and implementation prompts.
- Read [references/testing-and-packaging.md](./references/testing-and-packaging.md) for test and packaging checks.
