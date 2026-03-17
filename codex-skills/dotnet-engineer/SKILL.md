---
name: dotnet-engineer
description: Build, debug, review, and improve .NET applications across ASP.NET Core, Web API, worker services, libraries, Entity Framework, tests, build pipelines, and solution structure. Use when Codex needs to work on C#, csproj, sln, NuGet, DI, middleware, logging, configuration, LINQ, async code, or common .NET architecture tasks.
---

# Dotnet Engineer

Use this skill for .NET-focused engineering tasks with attention to solution structure, build integrity, and framework conventions.

## Workflow

1. Inspect the solution, project graph, target frameworks, and package references.
2. Find the execution path: controllers/endpoints, services, repositories, hosted services, or background jobs.
3. Respect existing dependency injection, configuration, and logging patterns.
4. Change behavior at the correct layer and keep API contracts explicit.
5. Validate with targeted `dotnet build`, `dotnet test`, or focused repro steps when available.

## Working Rules

- Prefer idiomatic .NET patterns over framework-agnostic abstractions.
- Check nullability, async flow, cancellation, disposal, and logging around the change.
- For ASP.NET Core, trace request flow through middleware, endpoints, services, and persistence.
- For EF Core work, verify tracking, query shape, migrations, and transaction boundaries.
- Keep `csproj` edits minimal and intentional.
- When touching configuration, map the source: `appsettings`, environment variables, secrets, or host config.

## Common Task Modes

### API and Backend

- Trace DTOs, validation, mapping, service logic, persistence, and response contracts.
- Guard against silent behavior changes in serialization or model binding.

### Performance and Reliability

- Check allocation-heavy loops, blocking I/O, sync-over-async, unbounded retries, and chatty queries.

### Build and Dependency Work

- Verify SDK version expectations, package compatibility, and target framework alignment across projects.

## References

- Read [references/dotnet-playbook.md](./references/dotnet-playbook.md) for a compact debugging and implementation guide.
- Read [references/aspnet-ef-checks.md](./references/aspnet-ef-checks.md) for ASP.NET Core and EF-specific checks.
