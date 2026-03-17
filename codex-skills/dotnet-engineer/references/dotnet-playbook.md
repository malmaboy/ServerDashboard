# Dotnet Playbook

## Inspect first

1. Solution file and project layout.
2. Target frameworks and SDK expectations.
3. Package references and shared libraries.
4. Main execution path for the reported behavior.

## Common failure buckets

- Dependency injection wiring
- Async/cancellation misuse
- Configuration binding
- Serialization/model binding
- EF query shape or migrations
- Package or target framework mismatch
