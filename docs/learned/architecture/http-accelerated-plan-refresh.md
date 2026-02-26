---
title: HTTP-Accelerated Plan Refresh
read_when:
  - "understanding dual-path architecture for plan data fetching"
  - "working with HttpClient ABC extensions"
  - "optimizing plan list performance"
tripwires:
  - action: "adding a new method to HttpClient ABC without implementing in all providers"
    warning: "HttpClient follows the gateway pattern. New methods must be added to abc.py, real.py, and fake.py at minimum."
  - action: "bypassing PlanListService for direct GitHub API plan queries"
    warning: "PlanListService handles the CLI-vs-HTTP path selection. Direct API calls bypass caching and error handling."
---

# HTTP-Accelerated Plan Refresh

The plan list system uses a dual-path architecture: a CLI subprocess path for simple operations and an HTTP direct API path for performance-critical operations.

## Dual-Path Architecture

### CLI Subprocess Path

Used by simple operations that make few API calls:

```
Command → GitHub gateway → gh CLI subprocess → GitHub API
```

Overhead: ~200-300ms per `gh api` call due to subprocess creation.

### HTTP Direct API Path

Used by plan listing and other bulk operations:

```
Command → PlanListService → HttpClient → GitHub REST/GraphQL API
```

No subprocess overhead. Enables batched and parallel requests.

## HttpClient ABC Extensions

The `HttpClient` ABC is defined in `packages/erk-shared/src/erk_shared/gateway/http/abc.py`. See that file for the current method list.

When `supports_direct_api` is False, the system falls back to the CLI subprocess path.

## 5-Place Gateway Implementation

HttpClient follows the standard gateway pattern:

| Place    | File               | Purpose                |
| -------- | ------------------ | ---------------------- |
| ABC      | `http/abc.py`      | Interface definition   |
| Real     | `http/real.py`     | Production HTTP client |
| Fake     | `http/fake.py`     | In-memory test double  |
| Dry Run  | `http/dry_run.py`  | No-op for dry-run mode |
| Printing | `http/printing.py` | Verbose output wrapper |

## Service Parameter Threading

`PlanListService` is threaded through many call sites (see `plan_list_service.py` for the current count). It accepts both `github` (gateway) and `http_client` parameters and selects the optimal path at runtime.

## PR Data Parsing

PR data parsing is extracted to a shared module to avoid duplication between the CLI and HTTP paths. Both paths produce the same `PlanRowData` output type.

## Source Code

- `src/erk/core/services/plan_list_service.py` — Service with dual-path selection
- `packages/erk-shared/src/erk_shared/gateway/http/abc.py` — HttpClient ABC

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — 5-place implementation pattern
- [Gateway vs Backend ABC Pattern](gateway-vs-backend.md) — When to use gateway vs backend
