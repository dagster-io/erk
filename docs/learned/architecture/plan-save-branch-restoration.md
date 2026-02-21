---
title: Plan Save Branch Restoration
read_when:
  - "modifying plan_save.py branch commit behavior"
  - "understanding git plumbing patterns in erk"
  - "working with commit_files_to_branch"
tripwires:
  - action: "checking out a branch in plan_save to commit files"
    warning: "Plan save uses git plumbing (commit_files_to_branch) to commit without checkout. Do NOT add checkout_branch calls. See plan-save-branch-restoration.md."
---

# Plan Save Branch Restoration

`plan_save.py` commits plan files to the plan branch using git plumbing commands (`commit_files_to_branch`), avoiding any branch checkout. This eliminates race conditions when multiple sessions share the same worktree.

## Pattern

Located in `src/erk/cli/commands/exec/scripts/plan_save.py`, the `_save_as_draft_pr()` function:

<!-- Source: src/erk/cli/commands/exec/scripts/plan_save.py, _save_as_draft_pr -->

See `_save_as_draft_pr()` in `src/erk/cli/commands/exec/scripts/plan_save.py` — uses `git.commit.commit_files_to_branch()` to create a commit directly on the plan branch without modifying HEAD or the working tree.

Key properties:

- Creates plan branch from current branch via `branch_manager.create_branch()`
- Commits plan files directly to the branch using git plumbing (no checkout)
- Pushes to origin with upstream tracking
- **Never checks out the plan branch** — HEAD and working tree remain untouched

## Git Plumbing Approach

The `commit_files_to_branch` method on `GitCommitOps` uses a temporary index file to create a commit without modifying the working tree, HEAD, or the real index. This is race-condition-free because no branch checkout occurs.

See `RealGitCommitOps.commit_files_to_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py` for the full implementation.

## Evolution

- PR #7491 removed checkout (plan committed without switching branches)
- PR #7494 re-added checkout with try/finally for the plan file commit step
- PR #7783 replaced checkout with git plumbing to eliminate race conditions

## Testing

See the plan_save test suite in `tests/unit/cli/commands/exec/scripts/test_plan_save.py` for checkout-count and branch-commit assertions that verify the plumbing approach.

## Related Topics

- [Draft PR Plan Backend](../planning/draft-pr-plan-backend.md) - Backend that uses this pattern
