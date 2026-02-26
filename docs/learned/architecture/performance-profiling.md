---
title: Performance Profiling Methodology
read_when:
  - "profiling CLI performance"
  - "measuring optimization impact"
  - "communicating performance improvements in PRs"
---

# Performance Profiling Methodology

## Identify Bottlenecks

### Subprocess Overhead Estimation

Each subprocess type has characteristic overhead:

- `git` commands: ~5-20ms
- `gh api` (Go runtime): ~200-300ms
- Python subprocess: ~20-50ms

### Calculate Total Time

```
Total = (N items) x (time per item) + fixed overhead
```

Example: 30 branches x 10ms per git rev-parse = 300ms

## Measure Improvements

### Before/After Pattern

Document in PR body:

```
Before: 30 git rev-parse calls x 10ms = 300ms
After: 1 git for-each-ref call = 5ms
Improvement: 60x faster
```

### Context Matters

Include:

- When the operation runs (every load, on-demand, etc.)
- User-perceivable impact (dashboard loads faster)
- Scale factors (N items typical range)

## Profiling Tools

For detailed timing, use Python's `time.perf_counter()` or the instrumentation added by PR #8171.

## Related Topics

- [Subprocess vs httpx Performance](subprocess-vs-httpx-performance.md) - Subprocess overhead characteristics
- [Parallelizing Gateway Calls](parallelizing-gateway-calls.md) - Reducing total latency
