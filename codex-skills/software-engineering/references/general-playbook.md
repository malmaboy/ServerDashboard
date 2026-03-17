# General Playbook

## Use this order

1. Discover entry points and affected files.
2. Confirm expected behavior and actual behavior.
3. Trace dependencies and side effects.
4. Implement the narrowest credible fix.
5. Verify locally with the fastest reliable check.

## Verification ladder

- Prefer targeted tests over full suites when time matters.
- If no tests exist, use a build or lint step.
- If no automation exists, document a manual verification path.

## Output pattern

- State what changed.
- State what was verified.
- State residual risk or unverified areas.
