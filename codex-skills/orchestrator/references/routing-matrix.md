# Routing Matrix

## Use this skill alone when

- The user asks for analysis, planning, or orchestration explicitly.
- The task is still ambiguous and needs classification first.
- The work likely spans multiple specialties.

## Route to software engineering when

- The main deliverable is code changes in a repository.
- The task is a review, refactor, feature, implementation, or bug in app code.

## Route to dotnet engineer when

- The codebase is C# or .NET.
- The issue mentions ASP.NET Core, EF Core, `dotnet build`, `dotnet test`, `csproj`, `sln`, or NuGet.

## Route to python engineer when

- The codebase is Python.
- The task mentions `pytest`, async Python, packaging, scripts, FastAPI, Flask, Django, or automation.

## Route to tester engineer when

- The user asks for tests, a QA plan, regression prevention, or failure reproduction.
- The main question is "how do we verify this safely?"

## Route to azure devops engineer when

- The issue is in Azure Pipelines, repos, artifacts, agents, releases, or service connections.

## Route to server ops when

- The problem is on a Linux host, reverse proxy, firewall, service, container host, or deployment target.

## Route to ssh linux ops when

- The user wants SSH commands, command sequencing, or help interpreting remote Linux command output.

## Route to proxmox ops when

- The problem involves Proxmox host lifecycle, clusters, VM/LXC management, storage, or bridges.

## Route to software architect when

- The main task is system design, decomposition, boundaries, architecture decisions, or migration strategy.

## Route to code quality when

- The task is maintainability review, complexity reduction, standards alignment, or long-term health.

## Route to senior engineer when

- The task is high-risk, ambiguous, cross-cutting, or needs strong tradeoff judgment.

## Route to junior engineer when

- The user wants more teaching, slower pacing, or step-by-step execution.

## Chain skills when

- Infra diagnosis must happen before code changes.
- A .NET or Python service problem includes both application and host-level causes.
- A design task must be followed by implementation.
- A code change should be followed by testing or code-quality review.
