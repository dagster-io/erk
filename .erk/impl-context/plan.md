# Fix Graphite tracking divergence in `erk pr dispatch`

## Context

When launching jobs from the TUI, `erk pr dispatch` performs raw git operations (pull --rebase, commit, push) on Graphite-tracked branches. These operations change commit SHAs without updating Graphite's internal cache, causing tracking divergence. The fix follows the same pattern already used in `rewrite_cmd.py` and `sync_cmd.py`.

## Changes

### 1. Add `retrack_branch()` call in `dispatch_cmd.py`

**File:** `src/erk/cli/commands/pr/dispatch_cmd.py`

Insert after line 306 (after push succeeds), before line 308 (checkout back to original branch):

```python
    # Fix Graphite tracking divergence caused by pull_rebase + commit
    if ctx.graphite_branch_ops is not None:
        ctx.graphite_branch_ops.retrack_branch(repo.root, branch_name)
```

Follows the unconditional retrack pattern from `rewrite_cmd.py:189-191`. No new imports needed — `ctx.graphite_branch_ops` is already available on `ErkContext`.

### 2. Add test assertion in existing happy-path test

**File:** `tests/commands/pr/test_dispatch.py`

Add assertion to `test_dispatch_planned_pr_plan_triggers_workflow_with_planned_pr_backend` verifying that `retrack_branch` was called with the correct branch name after dispatch.

## Verification

- Run `tests/commands/pr/test_dispatch.py` to confirm the assertion passes
- Run full fast-ci to check for regressions
