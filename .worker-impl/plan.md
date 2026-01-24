# Plan: Mtime-Based Cache Invalidation for RealGraphite

## Summary

Replace manual cache invalidation in `RealGraphite` with automatic mtime-based staleness detection. This eliminates the bug-prone pattern of remembering to invalidate in every mutation method.

## Current Problem

- `_branches_cache` must be manually invalidated in every mutation method
- PR #5767 demonstrates this is error-prone (submit_stack was missing invalidation)
- External `gt` commands can modify `.graphite_cache_persist` without erk knowing

## Implementation

### File: `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`

**1. Add mtime tracking to cache:**

```python
def __init__(self) -> None:
    """Initialize with empty cache for get_all_branches."""
    self._branches_cache: dict[str, BranchMetadata] | None = None
    self._branches_cache_mtime: float | None = None
```

**2. Modify `get_all_branches()` to check mtime:**

```python
def get_all_branches(self, git_ops: Git, repo_root: Path) -> dict[str, BranchMetadata]:
    git_dir = git_ops.get_git_common_dir(repo_root)
    if git_dir is None:
        return {}

    cache_file = git_dir / ".graphite_cache_persist"
    if not cache_file.exists():
        return {}

    # Check if cache is still valid via mtime
    current_mtime = cache_file.stat().st_mtime
    if (
        self._branches_cache is not None
        and self._branches_cache_mtime is not None
        and self._branches_cache_mtime == current_mtime
    ):
        return self._branches_cache

    # Cache miss or stale - recompute
    data = read_graphite_json_file(cache_file, "Graphite cache")

    # Get all branch heads from git for enrichment
    git_branch_heads = {}
    branches_data = data.get("branches", [])
    for branch_name, _ in branches_data:
        if isinstance(branch_name, str):
            commit_sha = git_ops.get_branch_head(repo_root, branch_name)
            if commit_sha:
                git_branch_heads[branch_name] = commit_sha

    self._branches_cache = parse_graphite_cache(json.dumps(data), git_branch_heads)
    self._branches_cache_mtime = current_mtime
    return self._branches_cache
```

**3. Remove manual invalidation from mutation methods:**

Remove these lines:
- Line 81 in `sync()`: `self._branches_cache = None`
- Line 117 in `restack()`: `self._branches_cache = None`
- Line 356 in `continue_restack()`: `self._branches_cache = None`

Note: `submit_stack()` doesn't currently invalidate (the bug PR #5767 is fixing).

### File: `tests/integration/test_graphite.py`

**4. Replace `test_graphite_ops_get_all_branches_caches_results()`:**

Current test (lines 153-194) verifies cache does NOT re-read after file modification. This is the old behavior we're changing. Replace with two tests:

**Test A: Cache returns same result when mtime unchanged**
```python
def test_graphite_ops_get_all_branches_caches_when_mtime_unchanged(tmp_path: Path):
    """Test that get_all_branches() uses cache when file hasn't changed."""
    # Setup with real file
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    cache_file = git_dir / ".graphite_cache_persist"

    fixture_data = load_fixture("graphite/graphite_cache_persist.json")
    cache_file.write_text(fixture_data, encoding="utf-8")

    git_ops = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads={"main": "abc", "feature-1": "def", "feature-1-sub": "ghi", "feature-2": "jkl"},
    )
    ops = RealGraphite()

    # Multiple calls without file change should return cached result
    result1 = ops.get_all_branches(git_ops, tmp_path)
    result2 = ops.get_all_branches(git_ops, tmp_path)

    assert result1 == result2
    assert len(result1) == 4
```

**Test B: Cache invalidates when mtime changes**
```python
def test_graphite_ops_get_all_branches_invalidates_on_mtime_change(tmp_path: Path):
    """Test that get_all_branches() re-reads when file mtime changes."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    cache_file = git_dir / ".graphite_cache_persist"

    # Initial content
    initial_data = {"branches": [["feat-1", {"parentBranchName": "main"}]]}
    cache_file.write_text(json.dumps(initial_data))

    git_ops = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads={"feat-1": "abc123"},
    )
    ops = RealGraphite()

    result1 = ops.get_all_branches(git_ops, tmp_path)
    assert "feat-1" in result1

    # Modify file - ensure mtime changes
    time.sleep(0.01)
    new_data = {"branches": [["feat-2", {"parentBranchName": "main"}]]}
    cache_file.write_text(json.dumps(new_data))

    # Update git_ops with new branch
    git_ops = FakeGit(
        git_common_dirs={tmp_path: git_dir},
        branch_heads={"feat-2": "def456"},
    )

    result2 = ops.get_all_branches(git_ops, tmp_path)
    assert "feat-2" in result2
    assert "feat-1" not in result2
```

### File: `tests/unit/operations/test_real_graphite.py`

**5. Remove the 4 cache invalidation tests added in PR #5767:**

These tests verify manual invalidation (`_branches_cache = None`) which is no longer needed:
- `test_submit_stack_invalidates_branches_cache`
- `test_sync_invalidates_branches_cache`
- `test_restack_invalidates_branches_cache`
- `test_continue_restack_invalidates_branches_cache`

## Relationship to PR #5767

This plan supersedes PR #5767. That PR adds manual cache invalidation to `submit_stack()`. With mtime-based invalidation:
- The fix in PR #5767 becomes unnecessary
- The 4 tests added in PR #5767 become obsolete
- All existing manual invalidation lines can be removed

If PR #5767 merges first, this implementation will remove those changes. If this merges first, PR #5767 can be closed.

## Files to Modify

1. `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` - Core implementation
2. `tests/integration/test_graphite.py` - Replace cache behavior test
3. `tests/unit/operations/test_real_graphite.py` - Remove invalidation tests (if PR #5767 merged)

## Verification

1. Run integration tests: `pytest tests/integration/test_graphite.py -v`
2. Run unit tests: `pytest tests/unit/operations/test_real_graphite.py -v`
3. Manual test:
   - Run `erk plan submit`
   - Verify `gt ls` shows correct branches immediately after
4. Verify mtime detection works:
   - Call get_all_branches
   - Touch `.git/.graphite_cache_persist`
   - Call get_all_branches again - should re-read