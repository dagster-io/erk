# Plan: Strip impl-context before restack in pr sync

## Context

When running `erk pr sync --dangerous`, `gt restack` hits merge conflicts in `.erk/impl-context/` files. These are temporary staging files committed to plan branches -- they get cleaned up before implementation. The user must manually delete and `gt continue` (sometimes multiple times) to get past the conflicts.

**Root cause**: Plan branches have commits adding `.erk/impl-context/` files. When rebasing onto updated master, these transient files cause conflicts.

**Fix**: Before restack, strip impl-context files from the branch and squash. No conflict detection loops needed -- the files are simply removed before rebase starts.

## Changes

### File: `src/erk/cli/commands/pr/sync_cmd.py`

**1. Add helper function:**

```python
def _strip_impl_context_if_present(ctx: ErkContext, repo_root: Path) -> bool:
    """Remove .erk/impl-context/ from working tree and stage if present."""
    impl_dir = repo_root / IMPL_CONTEXT_DIR
    if not impl_dir.exists():
        return False
    shutil.rmtree(impl_dir)
    ctx.git.commit.add_all(repo_root)
    return True
```

**2. Add new imports:**
- `import shutil`
- `from erk_shared.plan_store.draft_pr_lifecycle import IMPL_CONTEXT_DIR`

**3. Already-tracked path (line ~234, before restack):**

Insert before `restack_idempotent` call:
```python
if _strip_impl_context_if_present(ctx, repo.root):
    user_output("Stripping .erk/impl-context/ before restack...")
    ctx.git.commit.commit(repo.root, "Remove impl-context before sync")
    _squash_commits(ctx, repo.root)
```

**4. First-time-tracking path (line ~300, after message update, before restack):**

Insert after `_update_commit_message_from_pr` and before `restack_idempotent`:
```python
if _strip_impl_context_if_present(ctx, repo.root):
    user_output("Stripping .erk/impl-context/ before restack...")
    ctx.git.commit.commit(repo.root, "Remove impl-context before sync")
    _squash_commits(ctx, repo.root)
```

The pattern is identical at both sites: strip files → commit removal → squash (folds removal into the main commit) → restack proceeds without impl-context files.

### File: `tests/commands/pr/test_sync.py`

**Test 1: `test_pr_sync_strips_impl_context_before_restack`**
- Set up already-tracked branch with impl-context directory on disk
- Run sync
- Assert: `commit.commit()` was called with "Remove impl-context before sync"
- Assert: squash was called
- Assert: restack succeeded (no conflict)

**Test 2: `test_pr_sync_skips_strip_when_no_impl_context`**
- Set up already-tracked branch WITHOUT impl-context directory
- Run sync
- Assert: no extra commit created for impl-context removal
- Assert: restack called normally

## Key files
- `src/erk/cli/commands/pr/sync_cmd.py` -- primary modification
- `tests/commands/pr/test_sync.py` -- add 2 tests following existing patterns
- `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py` -- `IMPL_CONTEXT_DIR` constant
- `packages/erk-shared/src/erk_shared/impl_context.py` -- existing precedent for `shutil.rmtree`

## Verification

1. Run existing sync tests: `pytest tests/commands/pr/test_sync.py`
2. Run new tests
3. Type check: `ty check src/erk/cli/commands/pr/sync_cmd.py`
