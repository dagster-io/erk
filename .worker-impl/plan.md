# Plan: Fix RealGraphite Cache Invalidation

## Problem

Three test failures in `tests/unit/operations/test_real_graphite.py`:
- `test_sync_invalidates_branches_cache`
- `test_restack_invalidates_branches_cache`
- `test_continue_restack_invalidates_branches_cache`

These tests verify that `sync()`, `restack()`, and `continue_restack()` invalidate the `_branches_cache` after execution. Currently they don't, causing stale cache data.

## Root Cause

In `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`:
- `submit_stack()` correctly invalidates the cache (line 327: `self._branches_cache = None`)
- `sync()`, `restack()`, and `continue_restack()` are missing this cache invalidation

These methods modify Graphite/branch state, so subsequent `get_all_branches()` calls should return fresh data.

## Implementation

### File: `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`

Add `self._branches_cache = None` at the end of three methods:

1. **`sync()` method** (after line 79):
   ```python
   # Invalidate branches cache - gt sync modifies Graphite metadata
   self._branches_cache = None
   ```

2. **`restack()` method** (after line 112):
   ```python
   # Invalidate branches cache - gt restack modifies branch state
   self._branches_cache = None
   ```

3. **`continue_restack()` method** (after line 357):
   ```python
   # Invalidate branches cache - gt continue modifies branch state
   self._branches_cache = None
   ```

## Verification

Run the failing tests to confirm the fix:
```bash
make test-unit-erk
```

Or specifically:
```bash
pytest tests/unit/operations/test_real_graphite.py -v
```

All three cache invalidation tests should pass.