# Fix: Update stale local parent branch before `gt track` in plan checkout

## Context

When checking out a stacked plan branch for implementation (`erk br co --for-plan`), `gt track` fails if the local parent branch is stale (diverged from origin after squash/rebase via `gt submit`).

**Root cause**: `_rebase_and_track_for_plan()` in `checkout_cmd.py` rebases the plan branch onto `origin/<parent>`, but only fetches/creates the local parent branch if it **doesn't exist**. When the parent exists but is stale (different commits after squash), `gt track` compares against the stale local branch and fails with "not in the history of."

PR #8721 ("Retrack branch after plumbing commit in plan-save") fixed a related issue on the **save** side. This bug is on the **checkout/implement** side.

## Fix

**File**: `src/erk/cli/commands/branch/checkout_cmd.py` — `_rebase_and_track_for_plan()` (lines 371-392)

In the `else` branch (parent branch already exists locally), fetch from origin and update the local ref to match:

```python
# Current (lines 374-380):
local_branches = ctx.git.branch.list_local_branches(repo_root)
if parent_branch not in local_branches:
    user_output(f"Fetching base branch '{parent_branch}'...")
    ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
    ctx.branch_manager.create_tracking_branch(
        repo_root, parent_branch, f"origin/{parent_branch}"
    )

# Add else branch:
else:
    # Parent exists locally but may be stale after squash/rebase.
    # Update to match origin so gt track sees consistent history.
    ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
    remote_sha = ctx.git.branch.get_branch_head(repo_root, f"origin/{parent_branch}")
    local_sha = ctx.git.branch.get_branch_head(repo_root, parent_branch)
    if remote_sha is not None and remote_sha != local_sha:
        ctx.git.branch.update_local_ref(repo_root, parent_branch, remote_sha)
```

Uses existing `update_local_ref` (ABC at `branch_ops/abc.py:282`, real at `branch_ops/real.py:419`) which does `git update-ref` — safe when branch isn't checked out (and it won't be, since we just checked out the plan branch).

Need to verify `resolve_ref` exists or use an equivalent. If not, use `git rev-parse` via `get_branch_head`.

## Verification

1. Reproduce: check out a stacked plan branch whose parent was squashed since save
2. Run `erk br co --for-plan <plan> --script` followed by `erk implement -d`
3. Confirm `gt track` succeeds
4. Run unit tests for checkout_cmd
