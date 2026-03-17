---
name: tester-engineer
description: Design, extend, and review testing strategy across unit, integration, regression, API, UI, and smoke tests. Use when Codex needs to investigate failing tests, reproduce bugs, improve coverage, define test cases, review QA gaps, or build a verification plan before or after code changes.
---

# Tester Engineer

Use this skill when the main value is test design, regression prevention, or failure investigation.

## Workflow

1. Identify the risk area and expected behavior.
2. Classify the best test level: unit, integration, contract, end-to-end, or smoke.
3. Reproduce the failure or define reproducible acceptance criteria.
4. Add or adjust the smallest useful test coverage.
5. Report residual gaps and manual checks if automation is not enough.

## Working Rules

- Prefer tests that isolate the real contract being protected.
- Avoid brittle assertions tied to irrelevant formatting or timing.
- When debugging failures, distinguish flaky infrastructure from real regressions.
- Cover the happy path plus at least one important edge path for risky fixes.
- For reviews, focus on missing assertions, setup leakage, and untested branches.

## References

- Read [references/test-strategy.md](./references/test-strategy.md) for coverage decisions.
- Read [references/regression-debugging.md](./references/regression-debugging.md) for failure triage.
