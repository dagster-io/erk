---
title: Same-Worktree Navigation
category: erk
read_when:
  - "modifying navigation commands (up/down)"
  - "activation instructions"
  - "worktree deletion in same-worktree scenarios"
tripwires:
  - action: "adding a new call site that passes same_worktree"
    warning: "Use target_path.resolve() == ctx.cwd.resolve() — not string comparison. See same-worktree-navigation.md."
last_audited: "2026-03-05 00:00 PT"
audit_result: clean
---

# Same-Worktree Navigation

When a navigation command's target is the worktree the user is already in, erk adjusts its activation behavior to avoid redundant shell commands.

## Detection Pattern

```python
same_worktree = target_path.resolve() == ctx.cwd.resolve()
```

Uses `Path.resolve()` on both sides to normalize symlinks and relative paths. Never use string comparison.

## Call Sites

The detection pattern is used at 5 locations:

<!-- Source: src/erk/cli/commands/wt/checkout_cmd.py:123 -->
<!-- Source: src/erk/cli/commands/wt/create_from_cmd.py:109 -->
<!-- Source: src/erk/cli/commands/navigation_helpers.py:359 -->
<!-- Source: src/erk/cli/commands/navigation_helpers.py:904 -->
<!-- Source: src/erk/cli/commands/branch/checkout_cmd.py:256 -->

1. `wt/checkout_cmd.py` — worktree checkout
2. `wt/create_from_cmd.py` — worktree create-from
3. `navigation_helpers.py` — `navigate_up()` helper
4. `navigation_helpers.py` — `navigate_down_with_delete()` helper
5. `branch/checkout_cmd.py` — branch checkout

Several other call sites pass `same_worktree=False` statically (e.g., `wt/create_cmd.py`, `branch/create_cmd.py`, `pr/checkout_cmd.py`) because creation always targets a new worktree.

## Affected Functions

### `build_activation_command()`

<!-- Source: src/erk/cli/activation.py:57-94 -->

`build_activation_command(config, script_path, *, same_worktree: bool)` returns a shell command string. When `same_worktree=True` and no implement command is needed, returns an empty string (skipping the `source activate.sh` prefix).

### `print_activation_instructions()`

<!-- Source: src/erk/cli/activation.py:323-386 -->

`print_activation_instructions(..., *, same_worktree: bool)` prints activation instructions. When `same_worktree=True`, it:

- Skips the `source activate.sh` prefix
- Suppresses the entire activation block if there's nothing actionable to show

## Deletion in Same-Worktree Scenarios

<!-- Source: src/erk/cli/commands/navigation_helpers.py:931-939 -->

When `erk down -d` navigates to a worktree the user is already in (`shared_worktree=True`), the deletion commands are shown differently:

- Shows the actual `gt delete` commands directly instead of suggesting `erk br delete` (which would incorrectly try to delete the shared worktree)
- Filters out `git worktree remove` and `erk slot unassign` commands
- Copies the filtered commands to clipboard via OSC 52

## Related Topics

- [Shell Activation Pattern](../cli/shell-activation-pattern.md) - Why `source "$()"` is required
