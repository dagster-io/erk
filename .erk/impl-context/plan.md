# Make `erk pr sync` resilient to other-worktree gt sync failures

## Context

`gt sync --no-interactive -f` is a repo-wide operation that syncs ALL branches. When any branch has issues (e.g., unstaged changes in another worktree), it exits code 1 — even if the user's current branch synced fine. Currently, `sync_cmd.py:243` calls `ctx.graphite.sync()` with no error handling, so the RuntimeError propagates and crashes the entire command.

The goal: warn about other-branch issues instead of failing, so the user's sync/restack/submit flow can continue.

## Approach

Follow the existing `restack_idempotent` pattern: add a concrete template method on the `Graphite` ABC that wraps the abstract `sync()`, catches RuntimeError, and returns a discriminated union result. The CLI caller then uses isinstance checks (LBYL) to decide whether to warn or fail.

## Steps

### 1. Add `SyncSuccess`/`SyncError` types

**File:** `packages/erk-shared/src/erk_shared/gateway/gt/types.py`

Add after the Restack section (after line 43):

```python
SyncErrorType = Literal["other-branch-conflict", "sync-failed"]

@dataclass(frozen=True)
class SyncSuccess:
    success: Literal[True]
    message: str

@dataclass(frozen=True)
class SyncError:
    success: Literal[False]
    error_type: SyncErrorType
    message: str
```

### 2. Add `sync_idempotent` template method on ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py`

- Update `TYPE_CHECKING` imports to include `SyncError, SyncSuccess`
- Add `sync_idempotent()` concrete method after `restack_idempotent` (after line 464)
- Wraps `self.sync()` in try/except RuntimeError
- Classifies errors: `"cannot sync" + "unstaged changes"` → `"other-branch-conflict"`, everything else → `"sync-failed"`

No changes needed to `real.py`, `fake.py`, `dry_run.py`, etc. — they inherit the template method.

### 3. Update `sync_cmd.py` to use `sync_idempotent`

**File:** `src/erk/cli/commands/pr/sync_cmd.py`

Replace lines 241-244 (the "already tracked" path):

- Call `ctx.graphite.sync_idempotent()` instead of `ctx.graphite.sync()`
- `SyncError` with `error_type == "other-branch-conflict"`: display yellow warning, **continue** with restack/submit
- `SyncError` with `error_type == "sync-failed"`: raise `click.ClickException` (clean failure)
- `SyncSuccess`: display green checkmark (current behavior)

Only one call site needs updating — the "not-tracked" path (line 307+) doesn't call `sync()`.

### 4. Add tests

**Unit tests** for the template method (new file or in existing graphite test file):
- `sync_idempotent` returns `SyncSuccess` on happy path
- `sync_idempotent` classifies "unstaged changes" error as `"other-branch-conflict"`
- `sync_idempotent` classifies unknown errors as `"sync-failed"`

**CLI tests** in `tests/commands/pr/test_sync.py`:
- Sync warns and continues when other branch has unstaged changes (exit code 0)
- Sync fails cleanly on generic sync error (exit code != 0)

`FakeGraphite` already supports `sync_raises` parameter — no fake changes needed.

## Files Changed

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/gt/types.py` | Add `SyncErrorType`, `SyncSuccess`, `SyncError` |
| `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` | Add `sync_idempotent()` template method |
| `src/erk/cli/commands/pr/sync_cmd.py` | Use `sync_idempotent`, handle partial failures |
| Tests (2 files) | Unit + CLI tests |

## Verification

1. Run unit tests for the new `sync_idempotent` template method
2. Run CLI tests for `test_sync.py`
3. Run `make fast-ci` to verify no regressions
