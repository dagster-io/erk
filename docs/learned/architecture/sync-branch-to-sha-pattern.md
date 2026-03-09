---
title: sync_branch_to_sha Pattern
read_when:
  - "syncing a local branch to a remote SHA"
  - "updating a branch that might be checked out in a worktree"
  - "working with dispatch_helpers.py"
tripwires:
  - action: "calling update_local_ref on a branch without checking if it's checked out"
    warning: "Use sync_branch_to_sha() instead — it handles checked-out branches by using git reset --hard. Raw update_local_ref on checked-out branches causes index desync."
  - action: "using git checkout to sync a branch to a remote SHA"
    warning: "Use sync_branch_to_sha() from dispatch_helpers.py. It avoids checkout and handles both checked-out and non-checked-out branches."
---

# sync_branch_to_sha Pattern

Safely moves a local branch to a target SHA, handling both checked-out and non-checked-out branches.

## Source

`src/erk/cli/commands/pr/dispatch_helpers.py:12-40`

## Problem

`update_local_ref()` moves a branch pointer via `git update-ref`, but when the branch is checked out in a worktree, the index and working tree become stale. The ref points at the new commit but the files on disk reflect the old commit, causing phantom staged changes in `git status`.

## Solution

`sync_branch_to_sha()` uses LBYL to check checkout state and applies the appropriate strategy:

1. **Not checked out**: Uses `update_local_ref()` for a fast ref-only update
2. **Already at target SHA**: No-op (early return)
3. **Checked out with uncommitted changes**: Refuses with error (prevents data loss)
4. **Checked out and clean**: Uses `git reset --hard` to atomically sync ref + index + working tree

```python
def sync_branch_to_sha(ctx, repo_root, branch, target_sha):
    checked_out_path = ctx.git.worktree.is_branch_checked_out(repo_root, branch)
    if checked_out_path is None:
        ctx.git.branch.update_local_ref(repo_root, branch, target_sha)
        return
    # ... dirty check, then reset_hard
```

## Call Sites

| File                          | Usage                                             |
| ----------------------------- | ------------------------------------------------- |
| `dispatch_cmd.py:237`         | Sync target branch before committing impl-context |
| `incremental_dispatch.py:113` | Sync branch for incremental dispatch              |
| `branch/checkout_cmd.py:389`  | Sync parent branch during checkout                |
| `pr/checkout_cmd.py:275`      | Sync base branch during PR checkout               |

## When to Use vs `ensure_trunk_synced`

| Function              | Purpose                    | Scope                                |
| --------------------- | -------------------------- | ------------------------------------ |
| `sync_branch_to_sha`  | Move any branch to any SHA | General-purpose, takes explicit SHA  |
| `ensure_trunk_synced` | Sync trunk to match remote | Trunk-specific, fetches remote first |

`ensure_trunk_synced` internally uses `update_local_ref` (for non-checked-out trunk) or `pull_branch(ff_only=True)` (for checked-out trunk). It does NOT use `sync_branch_to_sha` because it also handles fetch and divergence detection.

## Related Documentation

- [Git Plumbing Patterns](git-plumbing-patterns.md) — broader context on plumbing-based git operations
- [Incremental Dispatch Workflow](../planning/incremental-dispatch.md) — uses sync_branch_to_sha for branch sync
