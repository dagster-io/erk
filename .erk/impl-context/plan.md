# Plan: Eliminate Master Checkout Requirement from plan-save and dispatch

## Context

When running `erk exec plan-save` or `erk pr dispatch` from a non-master branch, both commands fail unnecessarily:
- `plan-save` uses the current branch as the PR base — if that branch isn't pushed to remote, GitHub API rejects the PR creation
- `dispatch` requires the root worktree to have master checked out for trunk syncing

Both can be fixed using the plumbing techniques from objective #7813 (Eliminate Unnecessary Git Checkouts). The dispatch command's trunk sync currently uses `pull_branch` which requires checkout; this can be replaced with `fetch + update_local_ref`.

## Changes

### 1. Fix plan-save: check remote before using current branch as base

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py` (~line 194)

Add `branch_exists_on_remote` check to the existing conditional. This method already exists in all 5 gateway implementations.

```python
# Before (line 194-198):
if (
    current_branch is not None
    and current_branch != trunk
    and not current_branch.startswith("learn/")
):

# After:
if (
    current_branch is not None
    and current_branch != trunk
    and not current_branch.startswith("learn/")
    and git.branch.branch_exists_on_remote(repo_root, "origin", current_branch)
):
```

Preserves Graphite stacking when the branch IS pushed. Falls back to trunk when it isn't. This matches the pattern already used in `dispatch_cmd.py` line ~504.

### 2. Add `update_local_ref` to GitBranchOps gateway (5-place pattern)

New method to update a local branch ref without checkout, using `git update-ref`.

| File | Implementation |
|------|---------------|
| `packages/erk-shared/.../branch_ops/abc.py` | Abstract method |
| `packages/erk-shared/.../branch_ops/real.py` | `git update-ref refs/heads/{branch} {target_sha}` |
| `packages/erk-shared/.../branch_ops/fake.py` | Track in `_updated_refs` list + update `_branch_heads` |
| `packages/erk-shared/.../branch_ops/dry_run.py` | No-op |
| `packages/erk-shared/.../branch_ops/printing.py` | Print + delegate |

### 3. Rewrite `ensure_trunk_synced` to remove checkout requirement

**File:** `src/erk/cli/commands/pr/dispatch_helpers.py`

Remove the "root worktree must be on trunk" check and the "must be clean" check. Replace `pull_branch` with `update_local_ref`:

- Fetch `origin/trunk`
- Compare local vs remote SHAs (existing logic, keep as-is)
- On fast-forward case: replace `pull_branch()` with `update_local_ref(repo.root, trunk, remote_sha)`
- Keep divergence/ahead-of-remote error messages as-is

One edge case: if trunk IS checked out in a worktree, `update_local_ref` moves the ref but doesn't update the working tree. Add a conditional clean-check only when trunk is checked out (using existing `find_worktree_for_branch` + `has_uncommitted_changes`).

### 4. Tests

**Update existing tests** in `tests/unit/cli/commands/exec/scripts/test_plan_save.py`:
- Tests that expect feature branch stacking need `remote_branches` set so `branch_exists_on_remote` returns True

**New test cases:**
- `test_planned_pr_unpushed_feature_branch_falls_back_to_trunk` — verifies fallback when branch isn't on remote
- `test_dispatch_from_non_trunk_branch_succeeds` — verifies dispatch works without master checked out
- `test_ensure_trunk_synced_uses_update_ref` — verifies plumbing path instead of pull
- Unit test for `FakeGitBranchOps.update_local_ref` mutation tracking

## Critical Files

- `src/erk/cli/commands/exec/scripts/plan_save.py` — one-line conditional addition
- `src/erk/cli/commands/pr/dispatch_helpers.py` — rewrite `ensure_trunk_synced`
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py` — add abstract method
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py` — implement with `git update-ref`
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py` — implement with tracking
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py` — no-op
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/printing.py` — print + delegate

## Verification

1. Run `erk exec plan-save` from a non-master, unpushed branch — should succeed with trunk as base
2. Run `erk pr dispatch <plan>` from a non-master branch — should succeed without checkout error
3. Run fast-ci to verify all existing tests still pass
4. Verify Graphite stacking still works when on a pushed feature branch
