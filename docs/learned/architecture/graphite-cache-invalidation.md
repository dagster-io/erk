---
title: Graphite Cache Invalidation
read_when:
  - "implementing mtime-based cache invalidation"
  - "caching Graphite branch metadata"
  - "optimizing repeated calls to git or graphite operations"
tripwires:
  - action: "implementing mtime-based cache invalidation"
    warning: "Use triple-check guard pattern: (cache exists) AND (mtime exists) AND (mtime matches). Partial checks cause stale data bugs."
---

# Graphite Cache Invalidation

Mtime-based cache invalidation avoids repeated expensive operations while ensuring data freshness when underlying files change.

## The Pattern

The Graphite gateway caches branch metadata from `.graphite_cache_persist`. The cache uses file mtime (modification time) to detect staleness.

### Triple-Check Guard Pattern

Always check three conditions before using cached data:

1. **Cache exists** - `self._branches_cache is not None`
2. **Mtime exists** - `self._branches_cache_mtime is not None`
3. **Mtime matches** - `self._branches_cache_mtime == current_mtime`

```python
# Check if cache is still valid via mtime
current_mtime = cache_file.stat().st_mtime
if (
    self._branches_cache is not None
    and self._branches_cache_mtime is not None
    and self._branches_cache_mtime == current_mtime
):
    return self._branches_cache

# Cache miss or stale - recompute
```

### Why Triple-Check?

Partial checks cause bugs:

| Check Missing  | Bug                                    |
| -------------- | -------------------------------------- |
| No cache check | AttributeError when cache is None      |
| No mtime check | TypeError comparing None to float      |
| No match check | Stale data returned after file changes |

## Explicit Invalidation

When erk performs operations that modify Graphite state, explicitly invalidate the cache:

```python
def sync(self, repo_root: Path, *, force: bool, quiet: bool) -> None:
    # ... perform sync ...

    # Invalidate branches cache - gt sync modifies Graphite metadata
    self._branches_cache = None
```

Operations that require explicit invalidation:

- `gt sync` - Fetches remote state, updates tracking
- `gt submit` - Creates/updates PRs, modifies metadata
- `gt restack` - Rebases branches, changes parent relationships
- `gt continue` - Continues interrupted operations

## Trade-offs

### Mtime-Based (Current Approach)

**Pros:**

- Handles external `gt` commands automatically
- No timestamp coordination needed
- Simple to reason about

**Cons:**

- Requires file stat on every cache check
- Mtime resolution varies by filesystem (1s on HFS+, nanosecond on ext4)

### Eager Invalidation Only

**Pros:**

- Fastest for repeated erk-only workflows
- No filesystem stats

**Cons:**

- Misses external changes (user running `gt` directly)
- Requires tracking all mutation points

The mtime approach was chosen because users frequently mix erk and direct `gt` commands.

## Reference Implementation

See `RealGraphite.get_all_branches()` in `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`.

## Testing Mtime-Based Caches

When testing cache invalidation, filesystem mtime resolution can cause flaky tests. See [Integration Testing Patterns](../testing/integration-testing-patterns.md) for guidance on sleep patterns.

## Related Topics

- [Erk Architecture Patterns](erk-architecture.md) - Context and gateway design
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Adding new gateway methods
