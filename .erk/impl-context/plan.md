# Plan: Fix stacked plan checkout when local parent branch diverges from origin

## Context

When `plan-save` creates a plan branch stacked on the current feature branch, it correctly records `base_ref_name` in the plan's PR metadata. Later, `erk br co --for-plan` resolves this metadata and calls `_rebase_and_track_for_plan` to rebase the plan branch onto the parent and register it with Graphite.

**The bug:** Between plan-save and plan-checkout, `gt submit` (via `erk pr submit`) may squash and force-push the parent branch. This causes the local parent ref to diverge from `origin/{parent}`. The rebase step uses `origin/{parent}` (correct), but `gt track` checks the local parent ref (stale). Since the local parent's pre-squash tip isn't in the rebased plan branch's history, `gt track` fails with:

```
ERROR: plnd/fix-inactive-slot-untracke-03-03-0854 is not in the history of plnd/add-print-init-03-03-0905
```

## Change

**File:** `src/erk/cli/commands/branch/checkout_cmd.py` — `_rebase_and_track_for_plan` (lines 344-390)

Current code only fetches the parent when it doesn't exist locally (line 373: `if parent_branch not in local_branches`). Fix: always fetch the parent from origin, and sync the local ref when it has diverged.

```python
# Current (broken):
if parent_branch != trunk:
    local_branches = ctx.git.branch.list_local_branches(repo_root)
    if parent_branch not in local_branches:
        user_output(f"Fetching base branch '{parent_branch}'...")
        ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
        ctx.branch_manager.create_tracking_branch(...)

# Fixed:
if parent_branch != trunk:
    ctx.git.remote.fetch_branch(repo_root, "origin", parent_branch)
    local_branches = ctx.git.branch.list_local_branches(repo_root)
    if parent_branch not in local_branches:
        ctx.branch_manager.create_tracking_branch(...)
    else:
        # Sync local ref when it diverges from origin (e.g. after gt submit squash)
        remote_head = ctx.git.branch.get_branch_head(repo_root, f"origin/{parent_branch}")
        local_head = ctx.git.branch.get_branch_head(repo_root, parent_branch)
        if remote_head is not None and remote_head != local_head:
            ctx.git.branch.update_local_ref(repo_root, parent_branch, remote_head)
```

**Existing APIs used:**
- `git.remote.fetch_branch` — already used in this function
- `git.branch.get_branch_head` — `GitBranchOps` ABC line 132, `FakeGitBranchOps` uses `_branch_heads` dict (supports `origin/` refs)
- `git.branch.update_local_ref` — `GitBranchOps` ABC line 282, fake tracks via `_updated_refs`

## Test

**File:** `tests/commands/branch/test_checkout_cmd.py`

Add one test: `test_checkout_for_plan_syncs_diverged_parent_ref`

Set up FakeGit with:
- Local parent branch `feature-parent` with HEAD `aaa111` (pre-squash)
- Remote `origin/feature-parent` with HEAD `bbb222` (post-squash)
- Plan with `base_ref_name: "feature-parent"`

Assert:
- `update_local_ref` was called to sync local parent to `bbb222`
- `rebase_onto` was called with `origin/feature-parent`
- `track_branch` was called with `feature-parent` as parent
- Exit code 0

## Verification

1. Run scoped tests: `uv run pytest tests/commands/branch/test_checkout_cmd.py`
2. Run py-fast-ci for full lint/format/type/test check
