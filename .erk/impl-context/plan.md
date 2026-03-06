# Fix `is_rebase_in_progress` in git worktrees

## Context

`erk pr rebase` fails to launch Claude with `/erk:rebase` when run in a non-root worktree (e.g., `erk-slot-05`). Instead of detecting the in-progress rebase and launching Claude, it throws `ClickException("gt restack failed:")`.

**Root cause**: `RealGitRebaseOps.is_rebase_in_progress()` checks for `rebase-merge`/`rebase-apply` directories under the **common** git dir (`git rev-parse --git-common-dir`). In worktrees, these directories are stored in the **per-worktree** git dir (`git rev-parse --git-dir`). So the check always returns `False` in non-root worktrees.

- Common dir (shared): `/path/to/repo/.git` — does NOT contain rebase state for worktrees
- Per-worktree dir: `/path/to/repo/.git/worktrees/erk-slot-05` — DOES contain `rebase-merge`/`rebase-apply`

In `rebase_cmd.py:102`, when `is_rebase_in_progress()` returns `False`, the command raises an error instead of falling through to launch Claude with `/erk:rebase`.

## Changes

### 1. Add `get_git_dir()` to `GitRepoOps` ABC

**File**: `packages/erk-shared/src/erk_shared/gateway/git/repo_ops/abc.py`

Add abstract method `get_git_dir(self, cwd: Path) -> Path | None` — returns the per-worktree git directory via `git rev-parse --git-dir`. Distinct from `get_git_common_dir` which returns the shared dir.

### 2. Implement in `RealGitRepoOps`

**File**: `packages/erk-shared/src/erk_shared/gateway/git/repo_ops/real.py`

Add `get_git_dir()` that calls `git rev-parse --git-dir` (same pattern as existing `get_git_common_dir` but with `--git-dir`).

### 3. Implement in `FakeGitRepoOps`

**File**: `packages/erk-shared/src/erk_shared/gateway/git/repo_ops/fake.py`

- Add optional `git_dirs: dict[Path, Path] | None` constructor param
- `get_git_dir()` checks `_git_dirs` first, falls back to `_git_common_dirs` (in non-worktree repos these are identical)
- Add `git_dirs` to `link_state()`

### 4. Implement in `DryRunGitRepoOps`

**File**: `packages/erk-shared/src/erk_shared/gateway/git/repo_ops/dry_run.py`

Delegate `get_git_dir()` to `self._wrapped.get_git_dir(cwd)`.

### 5. Implement in `PrintingGitRepoOps`

**File**: `packages/erk-shared/src/erk_shared/gateway/git/repo_ops/printing.py`

Delegate `get_git_dir()` to `self._wrapped.get_git_dir(cwd)`.

### 6. Update `RealGitRebaseOps` to use per-worktree git dir

**File**: `packages/erk-shared/src/erk_shared/gateway/git/rebase_ops/real.py`

- Change constructor param from `get_git_common_dir` to `get_git_dir`
- Update `is_rebase_in_progress()` to call `self._get_git_dir(cwd)` instead of `self._get_git_common_dir(cwd)`

### 7. Update `RealGit` wiring

**File**: `packages/erk-shared/src/erk_shared/gateway/git/real.py`

Change line 57 from `get_git_common_dir=self._repo.get_git_common_dir` to `get_git_dir=self._repo.get_git_dir`.

### 8. Update ABC docstring

**File**: `packages/erk-shared/src/erk_shared/gateway/git/rebase_ops/abc.py`

Fix the `is_rebase_in_progress` docstring: change "Handles worktrees by checking git common dir" to "Handles worktrees by checking per-worktree git dir".

## Verification

1. Run existing rebase tests: `uv run pytest tests/commands/pr/test_rebase.py`
2. Run repo ops tests if any exist
3. Run ty type checker on changed packages
4. Run ruff linter
