---
title: REST+GraphQL Trade-offs
read_when:
  - "optimizing GitHub API calls"
  - "deciding between REST and GraphQL"
  - "splitting or combining API queries"
tripwires:
  - action: "before splitting 1 API query into multiple sequential subprocess calls"
    warning: "Each subprocess call adds overhead. 2 sequential calls = 2x overhead. Only split if server-side filtering saves enough data transfer to offset subprocess cost."
    score: 4
---

# REST+GraphQL Trade-offs

## The Two-Step Pattern

**Pattern:** REST filtering + GraphQL enrichment

1. REST call with query params to filter results server-side
2. GraphQL call to enrich only the filtered subset

**When it helps:**

- Filtering reduces result set by 50%+ before expensive enrichment
- Using httpx (no subprocess overhead)
- Server-side filtering saves significant data transfer

**When it hurts:**

- Using subprocess for both calls (2x 200-300ms overhead)
- Filter doesn't significantly reduce result set
- GraphQL query is already efficient

## Anti-Pattern: Subprocess Splitting

Replacing 1 subprocess GraphQL call with 2 sequential subprocess calls (REST + GraphQL) makes things SLOWER:

- 1 call: ~300ms overhead + network
- 2 calls: ~600ms overhead + network

Only split when using httpx, where connection pooling minimizes per-call overhead.

## Decision Framework

1. Is subprocess overhead acceptable? (>500ms latency OK)
   - Yes: Single GraphQL query via subprocess
   - No: Use httpx for all API calls

2. Using httpx and filtering reduces results by >50%?
   - Yes: Consider REST filter + GraphQL enrichment
   - No: Single GraphQL query

## Related Topics

- [Subprocess vs httpx Performance](subprocess-vs-httpx-performance.md) - Detailed overhead analysis
- [GitHub API Optimization](github-api-optimization.md) - Server-side filtering patterns
