# Plan: Stale Git Index.lock Cleanup via PreToolUse Hook

> **Replans:** #5093

## What Changed Since Original Plan

- The infrastructure (hook system, lock utilities) is fully mature and well-documented
- Related diagnostic command `/erk:diag-lock-error` was added in Jan 2026
- No implementation work has been done on the actual hook

## Investigation Findings

### Corrections to Original Plan

1. **Stale Lock Detection**: Original plan uses `lsof` (Unix-specific). Better: check if lock file is 0-byte (git writes content when active)
2. **Command Detection Complexity**: `is_git_index_command()` parsing is unnecessary - just check for stale locks before ANY Bash command (minimal overhead)
3. **Hook Pattern**: Must use `ERK_HOOK_ID=git-lock-check-hook` marker pattern for detection

### Existing Infrastructure (DO NOT recreate)

- `get_lock_path()` in `packages/erk-shared/src/erk_shared/git/lock.py`
- `@hook_command()` decorator in `src/erk/hooks/decorators.py`
- Hook registration in `src/erk/core/claude_settings.py`
- Example hook: `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`

## Remaining Gaps

- [ ] Hook exec script `git_lock_check_hook.py` does not exist
- [ ] No PreToolUse hook registered for "Bash" matcher
- [ ] No tests for the hook

## Implementation Steps

### Step 1: Create Hook Script

**File:** `src/erk/cli/commands/exec/scripts/git_lock_check_hook.py`

```python
@hook_command(name="git-lock-check-hook")
def git_lock_check_hook(ctx: click.Context, *, hook_ctx: HookContext) -> None:
    """Clean stale git index.lock before Bash commands."""
    if not hook_ctx.is_erk_project:
        return  # Exit 0, not an erk project

    lock_path = get_lock_path(hook_ctx.repo_root)
    if lock_path is None or not lock_path.exists():
        return  # Exit 0, no lock file

    # Check if lock is stale (0-byte = stale, git writes content when active)
    if lock_path.stat().st_size == 0:
        lock_path.unlink()
        click.echo(f"Cleaned stale git index.lock: {lock_path}")

    return  # Exit 0, allow command to proceed
```

### Step 2: Register Hook Command

**File:** `src/erk/cli/commands/exec/__init__.py`

Add import and registration of the new hook command.

### Step 3: Add Hook to Settings

**File:** `src/erk/core/claude_settings.py`

Add constants:
```python
ERK_GIT_LOCK_CHECK_HOOK_COMMAND = (
    "command -v erk >/dev/null 2>&1 || exit 0; "
    "ERK_HOOK_ID=git-lock-check-hook erk exec git-lock-check-hook"
)
```

Update `add_erk_hooks()` to include PreToolUse entry with `matcher: "Bash"`.

### Step 4: Update HooksCapability

**File:** `src/erk/core/capabilities/hooks.py`

Add the git-lock-check-hook to managed_artifacts list (for detection during `erk init`).

### Step 5: Add Tests

**File:** `tests/unit/cli/commands/exec/scripts/test_git_lock_check_hook.py`

Test cases:
- Stale lock (0-byte) is cleaned
- Active lock (non-zero) is not touched
- No lock file present - exits cleanly
- Non-erk project - exits cleanly

## Files to Modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/git_lock_check_hook.py` | Create |
| `src/erk/cli/commands/exec/__init__.py` | Modify (add import) |
| `src/erk/core/claude_settings.py` | Modify (add constants, update hook list) |
| `src/erk/core/capabilities/hooks.py` | Modify (add to managed_artifacts) |
| `tests/unit/cli/commands/exec/scripts/test_git_lock_check_hook.py` | Create |

## Verification

1. Run unit tests: `make test-unit`
2. Run `erk init` in a test repo to verify hook is registered in `.claude/settings.json`
3. Manual test:
   - Create stale lock: `touch .git/index.lock`
   - Run any Bash command via Claude Code
   - Verify lock is cleaned and command succeeds