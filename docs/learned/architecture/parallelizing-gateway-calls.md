---
title: Parallelizing Independent Gateway Calls
read_when:
  - "optimizing data loading with multiple independent operations"
  - "using concurrent.futures in Python"
  - "identifying parallelization opportunities"
---

# Parallelizing Independent Gateway Calls

## Pattern

When multiple operations are independent (don't depend on each other's results), run them in parallel:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {
        executor.submit(fetch_plan_data): "plans",
        executor.submit(build_worktree_mapping): "worktrees",
        executor.submit(warm_graphite_cache): "graphite",
    }
    results = {}
    for future in as_completed(futures):
        key = futures[future]
        results[key] = future.result()
```

## Candidates for Parallelization in erk dash

1. API calls (REST/GraphQL)
2. Worktree mapping (`git worktree list`)
3. Graphite cache warmup
4. File I/O operations (plan.md reads)

## Expected Impact

Parallel execution completes in time of slowest operation. If 3 operations take 300ms, 200ms, 100ms sequentially (600ms total), parallel execution completes in ~300ms.

## Caution

- Thread safety: Ensure operations don't share mutable state
- Resource limits: Don't spawn too many workers for I/O-bound tasks
- Error handling: Use try/except in each task

## Related Topics

- [Subprocess vs httpx Performance](subprocess-vs-httpx-performance.md) - Understanding operation overhead
- [Erk Architecture Patterns](erk-architecture.md) - Gateway dependency injection patterns
