---
title: GitHub API Optimization Patterns
read_when:
  - "optimizing GitHub API usage"
  - "implementing server-side filtering"
  - "choosing between gh api and HttpClient"
---

# GitHub API Optimization Patterns

## Server-Side Filtering

Filter results at the server before expensive processing:

### Label Filtering (REST)

```
/repos/{owner}/{repo}/issues?labels=erk-plan&state=open
```

Note: REST `labels` parameter is AND-only (all labels must be present). Exclusion requires client-side filtering after REST call.

### Author Filtering (REST)

```
/repos/{owner}/{repo}/issues?creator={username}
```

## HttpClient vs gh api Subprocess

See [Subprocess vs httpx Performance](subprocess-vs-httpx-performance.md) for detailed comparison.

**Quick decision:** TUI operations -> HttpClient. CLI one-offs -> gh api subprocess.

## Connection Pooling

HttpClient (httpx-based) maintains persistent connections. Multiple requests to same host reuse the connection, avoiding TLS handshake overhead (~50-100ms per connection).

See `packages/erk-shared/src/erk_shared/gateway/http/real.py` for implementation.

## Related Topics

- [Subprocess vs httpx Performance](subprocess-vs-httpx-performance.md) - Overhead analysis
- [REST+GraphQL Trade-offs](rest-graphql-tradeoffs.md) - Query splitting decisions
- [GitHub API Rate Limits](github-api-rate-limits.md) - Rate limit considerations
