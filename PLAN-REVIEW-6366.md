# Convert Worktree add/remove from discriminated unions back to exceptions

## Rationale

`WorktreeAddError` and `WorktreeRemoveError` are structureless wrappers around an opaque `message: str`. No caller inspects `error_type` or branches on message content — they all just extract the string and convert to a CLI error. These don't model meaningful domain states (contrast with `PRNotFound` which has a `pr_number`, or `BranchAlreadyExists` which has a `branch_name`). They should just be exceptions that bubble to the CLI boundary.

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

Every callsite currently does `isinstance(result, WorktreeAddError)` then raises. Replace with letting the exception bubble. The callers are:

**`src/erk/cli/commands/checkout_helpers.py:200`**

- Remove isinstance check, let RuntimeError from `add_worktree()` propagate

**`src/erk/cli/commands/wt/create_cmd.py:272,334,341,348`**

- Remove all isinstance checks around `add_worktree()` calls

**`src/erk/cli/commands/stack/consolidate_cmd.py:117,329`**

- Remove isinstance check for `WorktreeRemoveError` and `WorktreeAddError`

**`src/erk/cli/commands/slot/common.py:555,570`**

- Remove isinstance checks

**`src/erk/cli/commands/stack/move_cmd.py:153`**

- Remove isinstance check

**`src/erk/cli/commands/stack/split_old/plan.py:215`**

- Remove isinstance check

**`src/erk/cli/commands/slot/init_pool_cmd.py:129`**

- This one uses `continue` on error (keeps initializing remaining slots). Wrap in try/except RuntimeError with `user_output` + `continue`.

**`src/erk/cli/commands/navigation_helpers.py:182,312`**

- Remove isinstance checks

### 5. Add RuntimeError handling at CLI boundary

The callsites currently convert errors to `click.ClickException`, `UserFacingCliError`, or `SystemExit(1)`. Since `RuntimeError` will now propagate, we need a handler.

**Option:** Add a `try/except RuntimeError` in each Click command function that calls worktree operations, converting to `UserFacingCliError`. This is the simplest approach and matches the one special case (`init_pool_cmd.py`) that needs `continue` behavior.

Alternatively, most callers already sit inside Click commands where `UserFacingCliError` would bubble to Click's handler. We could wrap the worktree calls in a thin helper, but that's over-engineering. The cleanest approach: just let `RuntimeError` propagate and rely on Click's default exception display, OR wrap at each callsite with a one-line try/except converting to `UserFacingCliError`.

**Recommended:** Wrap at each direct callsite since the error messages from `run_subprocess_with_context` are already user-readable. Use:

```python
try:
    ctx.git.worktree.add_worktree(...)
except RuntimeError as e:
    raise UserFacingCliError(str(e)) from None
```

This is the same number of lines as the isinstance pattern but with proper exception semantics. For `init_pool_cmd.py`, keep the try/except with `continue`.

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
