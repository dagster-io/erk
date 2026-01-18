---
title: Checkout Helpers Module
read_when:
  - "writing checkout commands"
  - "creating worktrees in checkout commands"
  - "implementing branch checkout logic"
tripwires:
  - action: "putting checkout-specific helpers in navigation_helpers.py"
    warning: "`src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead."
---

# Checkout Helpers Module

## Overview

The `src/erk/cli/commands/checkout_helpers.py` module contains two shared helper functions used by checkout commands: `ensure_branch_has_worktree()` and `navigate_and_display_checkout()`.

These helpers eliminate ~100 lines of duplication across three checkout command variants (`erk plan checkout`, `erk pr checkout`, plan PR checkout).

## Why This Module Exists Separately

The helpers live in `checkout_helpers.py` instead of `navigation_helpers.py` **to break a circular import cycle**:

- `navigation_helpers` imports from `wt.create_cmd`
- `wt.create_cmd` is in a module where `wt/__init__.py` imports `wt.checkout_cmd`
- If `navigation_helpers` contains checkout-specific helpers, it creates a cycle: `navigation_helpers` -> `wt.create_cmd` -> `wt` -> `wt.checkout_cmd`

Solution: Keep checkout-specific helpers in a separate `checkout_helpers.py` module that doesn't import from `wt` subpackage.

## Function: `ensure_branch_has_worktree()`

### Signature

```python
def ensure_branch_has_worktree(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    branch_name: str,
    no_slot: bool,
    force: bool,
) -> tuple[Path, bool]:
    """Ensure branch has a worktree, creating if needed.

    Returns: (worktree_path, already_existed)
    """
```

### Behavior

1. **Check existing**: Uses `ctx.git.find_worktree_for_branch()` to check if branch is already in a worktree
   - If found, returns immediately with `already_existed=True`
2. **Create if needed**:
   - **With slot** (`no_slot=False`): Calls `allocate_slot_for_branch()` with reuse and cleanup options
     - Displays message if slot was newly assigned
   - **Without slot** (`no_slot=True`): Directly creates worktree at computed path via `worktree_path_for()`
3. **Returns**: `(worktree_path, already_existed)` tuple

### When to Use

Call this helper at the start of any checkout command that needs to ensure a branch has a worktree.

**Example:**

```python
worktree_path, already_existed = ensure_branch_has_worktree(
    ctx,
    repo,
    branch_name=branch_name,
    no_slot=no_slot,
    force=force,
)
```

## Function: `navigate_and_display_checkout()`

### Signature

```python
def navigate_and_display_checkout(
    ctx: ErkContext,
    *,
    worktree_path: Path,
    branch_name: str,
    script: bool,
    command_name: str,
    already_existed: bool,
    existing_message: str,
    new_message: str,
    script_message_existing: str,
    script_message_new: str,
) -> None:
```

### Behavior

1. **Format path**: Styles worktree path for display with cyan + bold
2. **Navigate**: Calls `navigate_to_worktree()` which handles two modes:
   - **Script mode**: Generates activation script and exits via `sys.exit(0)`
   - **Interactive mode**: Returns `True` so caller can output custom message
3. **Display sync status** (only in shell integration mode):
   - Shows sync arrows (1^ = 1 commit ahead, 2v = 2 commits behind)
   - Distinguishes between diverged, ahead-only, and behind-only states

### Message Templating

Messages support `{styled_path}` placeholder that gets replaced with the formatted cyan+bold path:

```python
existing_message = "Switched to existing worktree: {styled_path}"
new_message = "Created new worktree: {styled_path}"
```

### When to Use

Call after `ensure_branch_has_worktree()` has determined the worktree exists or was created:

**Example:**

```python
navigate_and_display_checkout(
    ctx,
    worktree_path=worktree_path,
    branch_name=branch_name,
    script=script,
    command_name="plan co",
    already_existed=already_existed,
    existing_message="Switched to branch in {styled_path}",
    new_message="Created worktree at {styled_path}",
    script_message_existing="echo 'Switched to existing worktree'",
    script_message_new="echo 'Created new worktree'",
)
```

## Refactoring Pattern

This is an example of successful minimal abstraction for eliminating duplication:

1. **Identified common pattern**: Three commands had identical worktree creation + navigation logic
2. **Extracted minimal helpers**: Two functions that handle the repeated blocks without over-engineering
3. **Preserved command-specific logic**: Each command still handles its own branch fetching, PR resolution, etc.
4. **Result**: ~100 lines eliminated, code remains testable

## Integration with Other Modules

- **Imports from**: `slot/common.allocate_slot_for_branch`, `core.worktree_path_for`, `activation.render_activation_script`
- **Used by**: `plan/checkout_cmd.py`, `pr/checkout_cmd.py`, and potentially future checkout variants
