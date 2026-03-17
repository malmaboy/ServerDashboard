---
name: code-quality
description: Review and improve maintainability, readability, standards, consistency, complexity, and long-term code health. Use when Codex needs to assess code quality, identify smells, reduce complexity, improve naming and structure, review standards alignment, or suggest safer refactors without changing intended behavior.
---

# Code Quality

Use this skill when the main question is whether code is clean, maintainable, and safe to evolve.

## Review Priorities

1. Correctness risk from confusing structure
2. Complexity and readability
3. Naming and cohesion
4. Duplication and inconsistency
5. Testability and change safety

## Working Rules

- Preserve behavior unless the task explicitly asks for redesign.
- Prefer small maintainability wins with clear value.
- Distinguish style preferences from real quality risks.
- Highlight code smells only when they matter to future change or correctness.

## References

- Read [references/quality-checklist.md](./references/quality-checklist.md) for a concise review framework.
