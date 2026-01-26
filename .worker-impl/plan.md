# Fix: `erk br delete` not force-deleting merged PR branches

## Problem

When deleting a branch with `erk br delete <branch> -a` after a PR has been merged (squash or rebase), the command fails with:

```
error: the branch 'branch-name' is not fully merged
```

This happens because squash/rebase merges create new commit SHAs, so git's `-d` flag thinks the commits are "missing" even though the PR content is in master.

## Root Cause

In `_delete_branch_at_error_boundary()` at `src/erk/cli/commands/wt/delete_cmd.py:401`:

```python
ctx.branch_manager.delete_branch(repo_root, branch)  # force NOT passed!
```

The function receives `force: bool` as a parameter (line 382) but doesn't forward it to `delete_branch()`. The caller passes `force=True` after user confirmation, but it's silently dropped, defaulting to `force=False`.

## Fix

One-line change at `src/erk/cli/commands/wt/delete_cmd.py:401`:

```python
# Before:
ctx.branch_manager.delete_branch(repo_root, branch)

# After:
ctx.branch_manager.delete_branch(repo_root, branch, force=force)
```

## Files to Modify

1. `src/erk/cli/commands/wt/delete_cmd.py` - Pass `force` parameter (line 401)

## Test Plan

Add a unit test that verifies:
1. When `force=True` is passed to `_delete_branch_at_error_boundary`, it forwards `force=True` to `branch_manager.delete_branch()`
2. When `force=False`, it forwards `force=False`

Test file: `tests/commands/wt/test_delete_cmd.py` (or create `tests/commands/branch/test_delete_cmd.py`)

## Verification

1. Run existing tests: `make fast-ci`
2. Manual test:
   - Create a branch, push a PR, squash-merge it
   - Run `erk br delete <branch> -a`
   - Should succeed without "not fully merged" error