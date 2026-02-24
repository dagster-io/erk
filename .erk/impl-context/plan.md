# Fix: `erk land` crashes when run from root worktree

## Context

When `erk land` is run on a branch checked out in the root worktree (not a linked worktree), the cleanup phase tries to `git worktree remove --force` on the root worktree path, which fails with `fatal: '/path' is a main working tree`. The PR merges successfully but the command crashes during cleanup.

**Root cause:** `_cleanup_non_slot_worktree()` unconditionally calls `remove_worktree()`. The root worktree is classified as `CleanupType.NON_SLOT` (correct — it's not a slot), but the handler assumes all non-slot worktrees can be removed.

## Approach

Add a `ROOT_WORKTREE` cleanup type that deletes the branch and checks out trunk, but skips worktree removal. This follows the existing pattern of explicit cleanup type classification.

## Changes

### 1. Add `ROOT_WORKTREE` to `CleanupType` enum — `src/erk/cli/commands/land_cmd.py:116`

```python
class CleanupType(Enum):
    NO_DELETE = auto()
    NO_WORKTREE = auto()
    SLOT_ASSIGNED = auto()
    SLOT_UNASSIGNED = auto()
    NON_SLOT = auto()
    ROOT_WORKTREE = auto()  # NEW
```

### 2. Add `repo_root` param to `determine_cleanup_type()` — same file, line 139

Add `repo_root: Path` parameter. Before the final `NON_SLOT` return (line 182), check for root worktree:

```python
if is_root_worktree(worktree_path, repo_root):
    return ResolvedCleanup(
        cleanup_type=CleanupType.ROOT_WORKTREE,
        pool_state=state,
        assignment=None,
    )
```

Import `is_root_worktree` from `erk.core.worktree_utils`.

### 3. Add `_cleanup_root_worktree()` handler — same file, near line 808

Delete branch and checkout trunk, but skip worktree removal:

```python
def _cleanup_root_worktree(cleanup: CleanupContext) -> None:
    """Handle cleanup for root worktree: delete branch, skip worktree removal."""
    assert cleanup.worktree_path is not None

    if not cleanup.cleanup_confirmed:
        user_output("Branch preserved.")
        return

    trunk = cleanup.ctx.git.branch.detect_trunk_branch(cleanup.main_repo_root)
    cleanup.ctx.branch_manager.checkout_branch(cleanup.worktree_path, trunk)

    _ensure_branch_not_checked_out(
        cleanup.ctx, repo_root=cleanup.main_repo_root, branch=cleanup.branch
    )
    cleanup.ctx.branch_manager.delete_branch(cleanup.main_repo_root, cleanup.branch, force=True)
    user_output(click.style("✓", fg="green") + " Deleted branch (root worktree preserved)")
```

### 4. Wire into `_cleanup_and_navigate()` match — same file, line 1570

Add case before `NON_SLOT`:

```python
case CleanupType.ROOT_WORKTREE:
    _cleanup_root_worktree(cleanup)
```

### 5. Handle confirmation in `_gather_cleanup_confirmation()` — same file, line 215

Add case for `ROOT_WORKTREE` (different prompt — no "remove worktree" language):

```python
case CleanupType.ROOT_WORKTREE:
    proceed = ctx.console.confirm(
        f"After landing, delete branch '{target.branch}'?",
        default=True,
    )
```

### 6. Update all `determine_cleanup_type()` call sites to pass `repo_root`

Three call sites:
- `_cleanup_and_navigate()` line 1563 — pass `repo_root=main_repo_root`
- `_gather_cleanup_confirmation()` line 208 — pass `repo_root=repo.main_repo_root or repo.root`

### 7. Update existing tests — `tests/unit/cli/commands/land/test_determine_cleanup_type.py`

Add `repo_root` param to all existing test calls (use `tmp_path` — won't match any worktree_path so no behavior change). Add a new test:

```python
def test_root_worktree_returns_root_worktree(self, tmp_path: Path) -> None:
    pool_json = tmp_path / "pool.json"
    state = PoolState.test()
    save_pool_state(pool_json, state)

    result = determine_cleanup_type(
        no_delete=False,
        worktree_path=tmp_path,  # same as repo_root
        pool_json_path=pool_json,
        branch="feature-branch",
        repo_root=tmp_path,
    )
    assert result.cleanup_type == CleanupType.ROOT_WORKTREE
```

### 8. Add integration test — `tests/unit/cli/commands/land/test_cleanup_and_navigate.py`

Test `_cleanup_and_navigate` with `worktree_path == main_repo_root` and verify:
- Branch is deleted
- `remove_worktree` is NOT called (check FakeGit mutation tracking)
- No crash

## Files to modify

- `src/erk/cli/commands/land_cmd.py` — enum, detection, handler, match, confirmation
- `tests/unit/cli/commands/land/test_determine_cleanup_type.py` — add `repo_root` param + new test
- `tests/unit/cli/commands/land/test_cleanup_and_navigate.py` — new root worktree test

## Verification

1. `uv run pytest tests/unit/cli/commands/land/test_determine_cleanup_type.py` — classification tests
2. `uv run pytest tests/unit/cli/commands/land/test_cleanup_and_navigate.py` — cleanup behavior tests
3. `uv run pytest tests/commands/land/` — integration tests still pass
