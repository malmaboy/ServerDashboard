# Pipeline Debugging

## Triage order

1. Trigger and branch conditions
2. Variables, templates, and parameter expansion
3. Agent image or self-hosted agent health
4. Auth, secrets, and service connections
5. Build, test, packaging, and deploy logs

## Common failure buckets

- Wrong path filters
- Missing variables or secret scope
- Agent toolchain mismatch
- Artifact naming or stage dependency mismatch
- Environment approval or permission failure
