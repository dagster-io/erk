# Plan: Add `sync_idempotent` to handle gt sync failures gracefully

## Context

`erk pr sync --dangerous` crashes with a full traceback when `gt sync` fails due to issues on **unrelated branches** (e.g., unstaged changes on a different worktree's branch). The `gt sync` command is all-or-nothing — it exits 1 if ANY branch has problems, even though the current branch synced fine. The call site at `sync_cmd.py:231` doesn't catch this, so it propagates as an unhandled `RuntimeError`.

The fix follows the established `restack_idempotent` / `squash_branch_idempotent` pattern: a compositing method on the ABC base class that wraps the abstract `sync()` primitive and returns a result type instead of raising.

## Changes

### 1. Add `SyncSuccess` and `SyncError` types to `gt/types.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/gt/types.py`

Add a new "Sync Operation Types" section (after the Restack section) with:
- `SyncErrorType = Literal["sync-unstaged-changes", "sync-failed"]`
- `SyncSuccess(frozen=True)` with `success: Literal[True]`, `message: str`
- `SyncError(frozen=True)` with `success: Literal[False]`, `error_type: SyncErrorType`, `message: str`

### 2. Add `sync_idempotent` method to Graphite ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py`

Add concrete method (NOT abstract) on the `Graphite` class, following `restack_idempotent` pattern:
- Wraps `self.sync()` in try/except `RuntimeError`
- On success: returns `SyncSuccess`
- On error with "unstaged changes" or "conflicting unstaged": returns `SyncError` with `error_type="sync-unstaged-changes"`
- On other errors: returns `SyncError` with `error_type="sync-failed"`
- Add `SyncError | SyncSuccess` to the existing `TYPE_CHECKING` imports

### 3. Update call site in `sync_cmd.py`

**File:** `src/erk/cli/commands/pr/sync_cmd.py`

Replace line 231-232:
```python
ctx.graphite.sync(repo.root, force=True, quiet=False)
user_output(click.style("✓", fg="green") + " Synced with remote")
```

With:
```python
sync_result = ctx.graphite.sync_idempotent(repo.root, force=True, quiet=False)
if isinstance(sync_result, SyncError):
    user_output(click.style("⚠", fg="yellow") + f" Sync warning: {sync_result.message}")
else:
    user_output(click.style("✓", fg="green") + " Synced with remote")
```

Add `SyncError` to the imports from `erk_shared.gateway.gt.types`.

## Files Modified

1. `packages/erk-shared/src/erk_shared/gateway/gt/types.py` — add types
2. `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` — add compositing method
3. `src/erk/cli/commands/pr/sync_cmd.py` — use `sync_idempotent`, warn on error

No changes needed to `real.py`, `fake.py`, `dry_run.py`, or `printing.py` — the compositing method lives on the base class and delegates to the existing abstract `sync()`.

## Verification

1. Run `make fast-ci` to verify types and tests pass
2. Manual test: `erk pr sync --dangerous` in a repo where `gt sync` would fail on unrelated branches — should print a warning and continue instead of crashing
