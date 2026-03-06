# Plan: Add `--from-current-branch` flag to `erk slot assign`

## Context

`erk slot assign <branch>` fails when the branch is already checked out in the current worktree because git doesn't allow the same branch to be checked out in multiple worktrees. The user wants a `--from-current-branch` flag (mirroring `erk wt create --from-current-branch`) that moves the current branch out of the current worktree and into a pool slot.

## Files to Modify

1. **`src/erk/cli/commands/slot/assign_cmd.py`** — Add `--from-current-branch` flag
2. **`tests/`** — Add/update tests for the new flag

## Implementation

### 1. Modify `assign_cmd.py`

Add `--from-current-branch` click option (is_flag=True). When set:

- Ignore the `BRANCH` argument (make it optional when flag is set)
- Get current branch via `ctx.git.branch.get_current_branch(ctx.cwd)`
- Determine target branch to switch to (reuse logic from `wt/create_cmd.py:767-802`):
  1. Prefer Graphite parent branch
  2. Fall back to trunk branch (main/master)
- Validate current_branch != to_branch
- Switch current worktree: check if target is available, checkout or detach
- Call `allocate_slot_for_branch()` with the now-free branch

Make `BRANCH` argument optional (required=False) and validate that exactly one of BRANCH or `--from-current-branch` is provided.

### 2. Branch-switching logic

Extract from `wt/create_cmd.py:760-814` — the pattern is:

```python
current_branch = ctx.git.branch.get_current_branch(ctx.cwd)
parent_branch = ctx.branch_manager.get_parent_branch(repo.root, current_branch)
to_branch = parent_branch or ctx.git.branch.detect_trunk_branch(repo.root)

# Validate not on trunk
Ensure.invariant(current_branch != to_branch, ...)

# Switch current worktree
checkout_path = ctx.git.worktree.is_branch_checked_out(repo.root, to_branch)
if checkout_path is not None:
    ctx.branch_manager.checkout_detached(ctx.cwd, current_branch)
else:
    ctx.branch_manager.checkout_branch(ctx.cwd, to_branch)
```

Note: This is similar to `create_cmd.py` but we don't need to extract a shared helper — the logic is ~10 lines and duplicating it is simpler than creating an abstraction for two call sites.

### 3. Tests

Find existing slot assign tests and add cases for:
- `--from-current-branch` moves branch to slot and switches current worktree
- Error when already on trunk branch
- Error when providing both BRANCH arg and `--from-current-branch`

## Verification

- Run `erk slot assign --from-current-branch` from a feature branch — should move it to a slot
- Run existing slot assign tests to confirm no regressions
- Run `make fast-ci` for full validation
