---
title: HTTP-Accelerated Plan Refresh
read_when:
  - "understanding HTTP-only architecture for plan data fetching"
  - "working with HttpClient ABC extensions"
  - "optimizing plan list performance"
  - "adding CLI commands that need http_client"
tripwires:
  - action: "adding a new method to HttpClient ABC without implementing in all providers"
    warning: "HttpClient follows the gateway pattern. New methods must be added to abc.py, real.py, and fake.py at minimum."
  - action: "bypassing PlanListService for direct GitHub API plan queries"
    warning: "PlanListService handles HTTP API calls. Direct API calls bypass caching and error handling."
  - action: "passing None for http_client in service methods"
    warning: "http_client is a required parameter (not optional) in PlanListService and ObjectiveListService. Passing None causes TypeError. Validate at CLI entry point."
  - action: "adding a new CLI entry point that calls plan or objective services"
    warning: "Must validate ctx.http_client is not None before calling service methods. Follow the pattern in existing entry points (pr list, pr duplicate-check, objective list, exec dash-data)."
---

# HTTP-Accelerated Plan Refresh

The plan and objective list systems use an HTTP-only architecture for direct API access, bypassing the `gh` CLI subprocess overhead.

## HTTP-Only Architecture

Plan listing and objective listing use direct HTTP calls:

```
Command → Service → HttpClient → GitHub REST/GraphQL API
```

No subprocess overhead. Enables batched and parallel requests. The subprocess fallback path was removed; `http_client` is now a required parameter.

## HttpClient ABC Extensions

The `HttpClient` ABC is defined in `packages/erk-shared/src/erk_shared/gateway/http/abc.py`. See that file for the current method list.

## 4-Place Gateway Implementation

HttpClient follows the standard gateway pattern:

| Place    | File              | Purpose                |
| -------- | ----------------- | ---------------------- |
| ABC      | `http/abc.py`     | Interface definition   |
| Real     | `http/real.py`    | Production HTTP client |
| Fake     | `http/fake.py`    | In-memory test double  |
| Dry Run  | `http/dry_run.py` | No-op for dry-run mode |

## Required http_client Parameter

<!-- Source: packages/erk-shared/src/erk_shared/core/plan_list_service.py -->
<!-- Source: packages/erk-shared/src/erk_shared/core/objective_list_service.py -->

Service methods require `http_client: HttpClient` as a keyword argument (not optional). Both `PlanListService.get_plan_list_data()` and `ObjectiveListService.get_objective_list_data()` take `http_client` as a required parameter and return `PlanListData`.

## CLI Auth Validation Pattern

<!-- Source: src/erk/core/context.py -->

HTTP client is initialized once at startup in `create_context()` via `gh auth token`. It may be `None` if GitHub authentication is unavailable (no repo, or `gh auth` fails).

Five CLI entry points validate `ctx.http_client is not None` before calling services, raising `SystemExit(1)` with a styled error if unavailable:

| Entry Point              | Location                                   |
| ------------------------ | ------------------------------------------ |
| `erk pr list`            | `pr/list_cmd.py` (`_pr_list_impl`)         |
| `erk dash` (TUI)         | `pr/list_cmd.py` (`_run_interactive_mode`) |
| `erk pr duplicate-check` | `pr/duplicate_check_cmd.py`                |
| `erk objective list`     | `objective/list_cmd.py`                    |
| `erk exec dash-data`     | `exec/scripts/dash_data.py`                |

## PR Data Parsing

PR data parsing is extracted to a shared module to avoid duplication. Both plan and objective listing produce the same `PlanRowData` output type.

## Source Code

- `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — Plan list service (ABC)
- `packages/erk-shared/src/erk_shared/core/objective_list_service.py` — Objective list service (ABC)
- `packages/erk-shared/src/erk_shared/gateway/http/abc.py` — HttpClient ABC

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — 4-place implementation pattern
- [Gateway vs Backend ABC Pattern](gateway-vs-backend.md) — When to use gateway vs backend
