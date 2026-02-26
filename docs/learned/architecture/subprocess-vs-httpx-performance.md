---
title: Subprocess vs httpx Performance Characteristics
read_when:
  - "optimizing TUI data loading performance"
  - "choosing between gh api subprocess and httpx for API calls"
  - "analyzing slow dashboard or CLI operations"
tripwires:
  - action: "before using `gh api` subprocess in TUI operations or hot paths"
    warning: "Each subprocess adds 200-300ms overhead (Go runtime + TLS). Use HttpClient with httpx for latency-sensitive operations (<500ms requirement)."
    score: 6
  - action: "before calling subprocess commands in a loop over N items"
    warning: "Batch with single command: git for-each-ref for branches, GraphQL aliased queries for PRs, etc. Reduces O(N) subprocess calls to O(1)."
    score: 6
---

# Subprocess vs httpx Performance Characteristics

Each subprocess call to `gh api` adds significant overhead beyond the actual API request time. Understanding this overhead is critical for performance-sensitive operations like TUI data loading.

## Subprocess Overhead Breakdown

Each `gh api` subprocess call adds approximately 200-300ms overhead:

- Process fork/exec: ~50ms
- Go runtime initialization: ~100ms
- TLS handshake: ~50-100ms
- Actual API call: variable (50-500ms depending on payload)

**Implication**: Two sequential subprocess calls = 400-600ms overhead before any actual work. This overhead is fixed per call, regardless of payload size.

## When to Use Each Approach

### Use httpx (HttpClient) when:

- Latency requirements are <500ms
- Making multiple sequential API calls
- TUI operations where perceived speed matters
- Connection pooling can be leveraged

### Use gh api subprocess when:

- One-off CLI operations where startup time is acceptable
- Complex authentication flows handled by gh
- Operations that benefit from gh's retry logic

## Anti-Pattern: Splitting Queries

Replacing 1 subprocess call with 2 sequential ones (e.g., REST filtering + GraphQL enrichment) makes things SLOWER due to doubled overhead. Only split queries when server-side filtering saves enough data transfer to offset the additional subprocess overhead.

See `packages/erk-shared/src/erk_shared/gateway/http/` for HttpClient implementation.

## Related Topics

- [REST+GraphQL Trade-offs](rest-graphql-tradeoffs.md) - Decision framework for splitting queries
- [GitHub API Optimization](github-api-optimization.md) - Server-side filtering patterns
- [Parallelizing Gateway Calls](parallelizing-gateway-calls.md) - Running independent operations concurrently
