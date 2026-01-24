# Fix: Branch Not Visible in `gt ls` After `erk plan submit`

## Problem

After `erk plan submit` completes with "Linking PR with Graphite... ✓ PR linked with Graphite", running `gt ls` immediately shows nothing - the branch is not visible.

## Root Cause

**In-memory cache invalidation bug** in `RealGraphite.submit_stack()`.

1. `submit_stack()` runs `gt submit` which updates `.graphite_cache_persist` on disk
2. But `RealGraphite._branches_cache` is NOT invalidated after the subprocess completes
3. Subsequent calls to `get_all_branches()` or `is_branch_tracked()` return stale cached data
4. Other methods already invalidate the cache:
   - `sync()` line 81: `self._branches_cache = None`
   - `restack()` line 117: `self._branches_cache = None`
   - `continue_restack()` also invalidates
   - **`submit_stack()` is missing this!**

## Solution

Add cache invalidation at the end of `submit_stack()`.

### File to Modify

`packages/erk-shared/src/erk_shared/gateway/graphite/real.py`

### Change

After line 323 (end of `submit_stack()` method), add:

```python
        # Invalidate branches cache - gt submit modifies Graphite metadata
        self._branches_cache = None
```

The full method with fix:

```python
def submit_stack(
    self,
    repo_root: Path,
    *,
    publish: bool = False,
    restack: bool = False,
    quiet: bool = False,
    force: bool = False,
) -> None:
    """Submit the current stack to create or update PRs."""
    cmd = ["gt", "submit", "--no-edit", "--no-interactive"]
    # ... existing code ...

    try:
        result = subprocess.run(...)
        if not quiet and result.stderr:
            user_output(result.stderr, nl=False)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(...) from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(...) from e

    # ADD THIS: Invalidate branches cache - gt submit modifies Graphite metadata
    self._branches_cache = None
```

## Why This Works

- `gt submit` **immediately** updates `.git/.graphite_cache_persist` on disk
- The stale in-memory cache was the problem, not timing
- Cache invalidation forces the next `get_all_branches()` call to re-read from disk
- No sleep/retry needed - purely local state fix

## Verification

1. Run `erk plan submit <issue>`
2. Immediately run `gt ls`
3. Branch should appear in the output

## Testing

Add a unit test that verifies `_branches_cache` is invalidated after `submit_stack()`:

```python
def test_submit_stack_invalidates_cache(tmp_path: Path) -> None:
    """Verify submit_stack() invalidates the branches cache."""
    graphite = RealGraphite()
    # Pre-populate cache
    graphite._branches_cache = {"stale": "data"}

    # submit_stack would normally run gt submit
    # After it completes, cache should be None
    # (Use mock to avoid actual subprocess)
    with patch("subprocess.run"):
        graphite.submit_stack(tmp_path)

    assert graphite._branches_cache is None
```