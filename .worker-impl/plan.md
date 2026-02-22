# Clean up stale branch-restoration remnants in one_shot_dispatch.py

## Context

**Objective:** #7813 ("Eliminate Unnecessary Git Checkouts via Plumbing Operations"), node 1.3

PR #7786 eliminated checkouts from `one_shot_dispatch.py` by replacing `checkout_branch` + `stage_files` + `commit` with `commit_files_to_branch` (git plumbing). This removed the entire `try`/`finally` save/restore scaffolding. However, it left behind a stale `original_branch` variable and comment, plus outdated documentation. This plan addresses those remnants.

**Source:** One-shot PR #7898 (to be closed after this plan is saved).

## Changes

### 1. Rename `original_branch` and update comment (`src/erk/cli/commands/one_shot_dispatch.py`)

Lines 226-233 — the comment claims "Save current branch for restoration" but no restoration occurs. Rename `original_branch` to `current_branch` and fix the comment:

```python
# Before (lines 226-233):
# Save current branch for restoration after workflow trigger
original_branch = ctx.git.branch.get_current_branch(repo.root)
if original_branch is None:

# After:
# Guard against detached HEAD state
current_branch = ctx.git.branch.get_current_branch(repo.root)
if current_branch is None:
```

`current_branch` is not used after the guard but the `get_current_branch()` call is needed for the `is None` check.

### 2. Update test function names (`tests/commands/one_shot/`)

Two test functions reference "original_branch" in their names:
- `tests/commands/one_shot/test_one_shot_dispatch.py:178` — `test_dispatch_stays_on_original_branch_on_error`
- `tests/commands/one_shot/test_one_shot.py:227` — `test_one_shot_stays_on_original_branch_on_error`

Rename to `test_dispatch_stays_on_current_branch_on_error` and `test_one_shot_stays_on_current_branch_on_error` respectively.

### 3. Update Branch Safety docs (`docs/learned/planning/one-shot-workflow.md`)

Line 158 — stale claim about `finally` block restoration. Replace:

```
# Before:
The dispatch function always restores the original branch in a `finally` block, even on errors. This prevents leaving the user's worktree on an unexpected branch.

# After:
The dispatch function commits directly to the target branch using git plumbing (`commit_files_to_branch`) without checking out any branch. The user's working tree and HEAD remain untouched throughout the dispatch.
```

### 4. Close PR #7898

Close the one-shot PR since this plan supersedes it.

## Verification

1. `ruff check src/erk/cli/commands/one_shot_dispatch.py`
2. `ty check src/erk/cli/commands/one_shot_dispatch.py`
3. `pytest tests/commands/one_shot/`
4. Grep for `original_branch` in `one_shot_dispatch.py` to confirm no references remain
