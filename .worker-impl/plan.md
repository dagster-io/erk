# Refactor `erk implement` to Remove `dry_run` Boolean Parameters

## Problem

PR #2275 added a `--force` flag to `erk implement` but introduced `dry_run: bool` parameters threaded through multiple functions. This violates the documented architecture in `docs/agent/architecture/erk-architecture.md`:

> **MUST**: Use DryRun wrappers for dry-run mode
> **MUST NOT**: Pass dry_run flags through business logic functions

The correct pattern wraps dependencies at context creation (already done in `context.py` lines 508-513), then business logic just uses `ctx.dry_run` property for UI-only concerns.

## Solution

Remove `dry_run: bool` parameters from function signatures and replace with `ctx.dry_run` property access at the points of use.

## Changes to `src/erk/cli/commands/implement.py`

### 1. `_handle_force_delete` (lines 545-609)

**Remove parameter from signature:**
```python
# Before
def _handle_force_delete(
    ctx: ErkContext,
    *,
    ...
    dry_run: bool,  # REMOVE
) -> None:

# After
def _handle_force_delete(
    ctx: ErkContext,
    *,
    ...
    # dry_run removed
) -> None:
```

**Replace usages in function body:**
- Line 587: `if not dry_run:` → `if not ctx.dry_run:`
- Line 595: `if dry_run:` → `if ctx.dry_run:`
- Line 602: `if dry_run:` → `if ctx.dry_run:`

### 2. `_create_worktree_with_plan_content` (lines 640-801)

**Remove parameter from signature:**
```python
# Before
def _create_worktree_with_plan_content(
    ctx: ErkContext,
    *,
    ...
    dry_run: bool,  # REMOVE
    ...
) -> Path | None:

# After
def _create_worktree_with_plan_content(
    ctx: ErkContext,
    *,
    ...
    # dry_run removed
    ...
) -> Path | None:
```

**Replace usages in function body:**
- Line 724: Remove `dry_run=dry_run,` from `_handle_force_delete` call
- Line 737: `if dry_run:` → `if ctx.dry_run:`

### 3. `_implement_from_file` (lines 948-1029)

**Remove parameter from signature:**
```python
# Before
def _implement_from_file(
    ctx: ErkContext,
    *,
    ...
    dry_run: bool,  # REMOVE
    ...
) -> None:

# After
def _implement_from_file(
    ctx: ErkContext,
    *,
    ...
    # dry_run removed
    ...
) -> None:
```

**Replace usages in function body:**
- Line 987: Remove `dry_run=dry_run,` from `_create_worktree_with_plan_content` call

### 4. `_implement_from_issue` (lines 861-945)

**No signature change needed** (doesn't have `dry_run` param currently)

**Replace usages in function body:**
- Line 905: Remove `dry_run=dry_run,` from `_create_worktree_with_plan_content` call

### 5. `implement` CLI entry point (lines 1088-1203)

**Remove `dry_run=dry_run` from both call sites:**
- Line 1179: Remove `dry_run=dry_run,` from `_implement_from_issue` call
- Line 1192: Remove `dry_run=dry_run,` from `_implement_from_file` call

## Why This Works

The context is already created with `dry_run=True` when the `--dry-run` flag is passed (in `cli.py`):

```python
ctx = create_context(dry_run=dry_run, script=script)
```

This means:
- `ctx.git` is already `DryRunGit(real_git)` - all git operations are no-ops
- `ctx.graphite` is already `DryRunGraphite(real_graphite)`
- etc.

The remaining `ctx.dry_run` checks are **legitimate** because they're for:
1. **Skipping user prompts** - UI concern at CLI boundary
2. **Showing dry-run preview output** - UI formatting

## Tests

Existing tests should continue to pass because:
- Tests that use `build_workspace_test_context(env, dry_run=True)` already wrap with DryRun implementations
- Tests checking `[DRY RUN]` output will still work via `ctx.dry_run` property

Verify these tests pass:
- `test_implement_from_issue_dry_run`
- `test_implement_from_plan_file_dry_run`
- `test_implement_submit_with_dry_run`
- `test_implement_force_dry_run_shows_would_delete`

## Summary of Changes

| Location | Change |
|----------|--------|
| `_handle_force_delete` signature | Remove `dry_run: bool` |
| `_handle_force_delete` body | `dry_run` → `ctx.dry_run` (3 places) |
| `_create_worktree_with_plan_content` signature | Remove `dry_run: bool` |
| `_create_worktree_with_plan_content` body | `dry_run` → `ctx.dry_run` (1 place), remove call arg (1 place) |
| `_implement_from_file` signature | Remove `dry_run: bool` |
| `_implement_from_file` body | Remove call arg (1 place) |
| `_implement_from_issue` body | Remove call arg (1 place) |
| `implement` CLI function | Remove call args (2 places) |

**Total: ~10 changes in 1 file**