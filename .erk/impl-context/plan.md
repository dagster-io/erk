# Plan: Fix `erk stack consolidate` Missing Mid-Rebase Worktrees

## Context

`erk stack consolidate` fails to detect worktrees that are mid-rebase on a stack branch. When a worktree (e.g., `erk-slot-14`) is in the middle of rebasing `plnd/consolidate-learn-docs-03-07-2145`, git puts it in detached HEAD state but still considers the branch "in use" by that worktree. `git worktree list --porcelain` reports `branch=None` for these worktrees, so `identify_removable_worktrees` skips them entirely. This means `erk stack consolidate` reports "No other worktrees found" while `gt restack` still fails.

## Approach

Enhance `RealWorktree.list_worktrees()` to detect rebase state for detached-HEAD worktrees and populate their branch info. This fixes the root cause at the data layer so all consumers (consolidate, `find_worktree_for_branch`, `is_branch_checked_out`) benefit automatically.

## Changes

### 1. Add `is_rebasing` field to `WorktreeInfo`
**File:** `packages/erk-shared/src/erk_shared/gateway/git/abc.py`

Add `is_rebasing: bool = False` to the frozen dataclass. Backward-compatible default.

### 2. Detect rebase branches in `RealWorktree.list_worktrees`
**File:** `packages/erk-shared/src/erk_shared/gateway/git/worktree/real.py`

After parsing porcelain output, for each worktree with `branch=None`:
1. Read `.git` file in the worktree path to find its git dir (format: `gitdir: <path>`)
2. For root worktree, the git dir is `<path>/.git/`
3. Check for `<git_dir>/rebase-merge/head-name` (interactive rebase) or `<git_dir>/rebase-apply/head-name` (non-interactive)
4. If found, parse branch name (strip `refs/heads/` prefix), set `branch=<name>` and `is_rebasing=True`

Extract a helper `_detect_rebase_branch(worktree_path: Path, is_root: bool) -> str | None` for clarity.

### 3. Skip uncommitted-changes check for mid-rebase worktrees in consolidate
**File:** `src/erk/cli/commands/stack/consolidate_cmd.py`

In the safety check loop (lines 308-321), skip worktrees where `is_rebasing=True`. Mid-rebase worktrees will have dirty state from the interrupted rebase, but force-removal handles cleanup. Add a warning message like "Worktree X is mid-rebase and will be cleaned up".

### 4. Display "(rebasing)" indicator for mid-rebase worktrees
**File:** `src/erk/cli/commands/stack/consolidate_cmd.py`

In `_format_consolidation_plan`, append "(rebasing)" to the branch name when the worktree `is_rebasing`.

### 5. Update `FakeWorktree`
**File:** `packages/erk-shared/src/erk_shared/gateway/git/worktree/fake.py`

Ensure `WorktreeInfo` construction in the fake passes through `is_rebasing` from test data.

### 6. Update existing test
**File:** `tests/core/utils/test_consolidation_utils.py`

The test `test_skip_worktrees_with_detached_head` tests that detached HEAD worktrees (no branch) are skipped. This test remains valid - truly detached worktrees (not mid-rebase) should still be skipped. No change needed.

### 7. Add new test for mid-rebase worktree detection
**File:** `tests/core/utils/test_consolidation_utils.py`

Add `test_include_rebasing_worktrees_in_removable()` - a worktree with `branch="feat-1"` and `is_rebasing=True` should be included in removable list when `feat-1` is in the stack.

### 8. Add test for rebase branch detection in real worktree
**File:** `tests/real/test_real_worktree.py` (or appropriate location)

Test that `_detect_rebase_branch` correctly parses rebase state files. Use tmp_path to create the expected git directory structure.

## Verification

1. Run `uv run pytest tests/core/utils/test_consolidation_utils.py` - existing + new tests pass
2. Run `uv run pytest tests/real/` - rebase detection test passes
3. Run `uv run ruff check` and `uv run ty check` - no lint/type errors
4. Manual: run `erk stack consolidate` in the current scenario (erk-slot-14 mid-rebase) and verify it detects the worktree
