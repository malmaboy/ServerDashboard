# Python Playbook

## Inspect first

1. Entry point and import graph
2. Dependency file such as `pyproject.toml` or `requirements.txt`
3. Runtime mode: CLI, API, worker, script, or library
4. Existing tests around the affected behavior

## Common failure buckets

- Import path or environment mismatch
- Async misuse
- Mutable shared state
- Unhandled exceptions
- Serialization or validation mismatch
- Dependency drift
