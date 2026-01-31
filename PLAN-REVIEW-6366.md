# Convert Worktree add/remove from discriminated unions back to exceptions

## Rationale

These operations use exceptions that bubble to a top-level CLI handler. The error types (`WorktreeAddError`, `WorktreeRemoveError`) are structureless `message: str` wrappers with no domain-meaningful variants — they should be `RuntimeError` exceptions caught at the CLI boundary.

## Changes

### 1. Delete the non-ideal state types

**File:** `packages/erk-shared/src/erk_shared/gateway/git/worktree/types.py`

- Delete `WorktreeAddError` and `WorktreeRemoveError`
- Keep `WorktreeAdded` and `WorktreeRemoved` (success types still useful for dry-run/printing to return)

Actually — `WorktreeAdded` and `WorktreeRemoved` are empty dataclasses with zero fields. Once the error variants are gone, these return `None` semantics. Change return types to `-> None` and delete all four types.

### 2. Update the ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py`

- `add_worktree()` → return `None` (raises `RuntimeError` on failure)
- `remove_worktree()` → return `None` (raises `RuntimeError` on failure)
- Remove imports of the deleted types

### 3. Update all 5 implementations

**`real.py`:** Remove the try/except around `run_subprocess_with_context` — let `RuntimeError` propagate naturally. Remove imports of deleted types.

**`fake.py`:**

- Change `add_worktree_error: WorktreeAddError | None` constructor param → `add_worktree_error: str | None` (the error message to raise as RuntimeError)
- Change `remove_worktree_error: WorktreeRemoveError | None` → `remove_worktree_error: str | None`
- When error is set, `raise RuntimeError(self._add_worktree_error)` instead of returning error type
- Return `None` instead of `WorktreeAdded()`/`WorktreeRemoved()`

**`dry_run.py`:** Change return type to `-> None`, return `None` instead of `WorktreeAdded()`/`WorktreeRemoved()`.

**`printing.py`:** Change return type to `-> None`, return `None` from delegating calls.

### 4. Update all callsites

Every callsite currently does `isinstance(result, WorktreeAddError)` then raises. Remove these isinstance checks and let `RuntimeError` propagate to the top-level handler. The callers are:

**`src/erk/cli/commands/checkout_helpers.py:200`**

- Remove isinstance check, remove error import

**`src/erk/cli/commands/wt/create_cmd.py:272,334,341,348`**

- Remove all isinstance checks around `add_worktree()` calls

**`src/erk/cli/commands/stack/consolidate_cmd.py:117,329`**

- Remove isinstance checks for `WorktreeRemoveError` and `WorktreeAddError`

**`src/erk/cli/commands/slot/common.py:555,570`**

- Remove isinstance checks

**`src/erk/cli/commands/stack/move_cmd.py:153`**

- Remove isinstance check

**`src/erk/cli/commands/stack/split_old/plan.py:215`**

- Remove isinstance check

**`src/erk/cli/commands/slot/init_pool_cmd.py:129`**

- **Exception:** This callsite uses `continue` on error (keeps initializing remaining slots). Wrap in `try/except RuntimeError` with `user_output` + `continue`.

**`src/erk/cli/commands/navigation_helpers.py:182,312`**

- Remove isinstance checks

### 5. Add RuntimeError handling at top-level CLI boundary

`RuntimeError` from worktree operations propagates up to a single top-level handler — the Click command group or CLI entry point — which converts it to `UserFacingCliError`. No per-callsite `try/except` wrapping.

The one exception is `init_pool_cmd.py` (Section 4 above), which needs `continue` behavior inside a loop and therefore keeps its own `try/except RuntimeError`.

### 6. Update tests

Search for tests that construct `WorktreeAddError`/`WorktreeRemoveError` or assert isinstance on them. Update FakeWorktree construction to use `add_worktree_error="message"` (string) instead of `add_worktree_error=WorktreeAddError(message="...")`.

### 7. Delete types.py if empty

If `types.py` only contained these four types, delete the file entirely and remove it from `__init__.py` or any re-exports.

## Files to modify

- `packages/erk-shared/src/erk_shared/gateway/git/worktree/types.py` — delete all 4 types (or entire file)
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/real.py`
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/fake.py`
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/dry_run.py`
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/printing.py`
- `src/erk/cli/commands/checkout_helpers.py`
- `src/erk/cli/commands/wt/create_cmd.py`
- `src/erk/cli/commands/stack/consolidate_cmd.py`
- `src/erk/cli/commands/slot/common.py`
- `src/erk/cli/commands/stack/move_cmd.py`
- `src/erk/cli/commands/stack/split_old/plan.py`
- `src/erk/cli/commands/slot/init_pool_cmd.py`
- `src/erk/cli/commands/navigation_helpers.py`
- Tests referencing these types

## Verification

- `make fast-ci` — unit tests + lint + type checks
- Grep for any remaining references to `WorktreeAddError`, `WorktreeRemoveError`, `WorktreeAdded`, `WorktreeRemoved`
