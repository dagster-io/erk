---
title: Exec Script Performance Patterns
read_when:
  - "optimizing exec script execution time"
  - "reducing gh subprocess overhead in exec scripts"
  - "bundling multiple API calls into a single exec script"
tripwires:
  - action: "making 5+ sequential gh api subprocess calls in an exec script"
    warning: "Each gh subprocess costs ~200-300ms. Bundle related API calls into a single exec script invocation or use the HTTP direct API path via PlanListService."
  - action: "making a separate subprocess call for each item in a batch operation"
    warning: "Use batch exec commands pattern (batch-exec-commands.md) to process items in a single invocation with per-item error handling."
---

# Exec Script Performance Patterns

Patterns for minimizing latency in exec scripts, particularly around subprocess overhead and API call batching.

## Subprocess Overhead Budget

Each `gh api` subprocess call costs approximately 200-300ms of overhead (process creation, shell initialization, JSON parsing). For exec scripts that make multiple API calls, this overhead dominates total execution time.

| Call Count | Approximate Overhead | Strategy                 |
| ---------- | -------------------- | ------------------------ |
| 1-2        | ~400-600ms           | Acceptable — use gh api  |
| 3-5        | ~600ms-1.5s          | Consider bundling        |
| 5+         | ~1s+                 | Use HTTP direct or batch |

## Bundling Strategies

### 1. Single GraphQL Query with Fragments

Instead of N separate `gh api` calls, use a single GraphQL query that fetches all needed data:

```graphql
query ($numbers: [Int!]!) {
  repository(owner: "...", name: "...") {
    issues: nodes(ids: $numbers) {
      ...IssueFields
    }
  }
}
```

### 2. Batch Exec Commands

For operations on multiple items, use the batch exec command pattern from `batch-exec-commands.md`:

- Process all items in a single invocation
- Return per-item success/failure in JSON
- Validate all items upfront before processing

### 3. HTTP Direct API Path

For bulk read operations, use `PlanListService` which selects the HTTP direct path when available, bypassing subprocess overhead entirely.

## Source Pointer

See `src/erk/core/services/plan_list_service.py` for the canonical dual-path implementation.

## Related Documentation

- [HTTP-Accelerated Plan Refresh](../architecture/http-accelerated-plan-refresh.md) — Dual-path architecture
- [Batch Exec Commands](batch-exec-commands.md) — Batch processing pattern
- [Exec Script Patterns](exec-script-patterns.md) — General exec script patterns
