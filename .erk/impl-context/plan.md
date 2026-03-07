# Sort Command Palette Menu Alphabetically

## Context

The command palette in `erk dash` has commands grouped by type (actions, opens, copies) with sub-groups (direct commands, launch commands, exec commands). Within these sub-groups, items are not sorted alphabetically. The user wants alphabetical sorting within each sub-group while preserving the sub-group structure.

## File

`src/erk/tui/commands/registry.py` — the `get_all_commands()` function (line 203)

## Changes

Reorder `CommandDefinition` entries within `get_all_commands()`. Sort by `description` field within each sub-group:

### PLAN ACTIONS (direct commands)
Current: close, dispatch, land → **already sorted ✓**

### PLAN ACTIONS (launch commands)
Current: rebase, address, rewrite → **Sorted: address, rebase, rewrite**

### PLAN ACTIONS (exec commands)
Current: cmux checkout → **only one ✓**

### OBJECTIVE ACTIONS
Current: plan (one-shot), check, close → **Sorted: check, close, plan (one-shot)**

### PLAN OPENS
Current: plan, pr, run → **already sorted ✓**

### OBJECTIVE OPENS
Current: objective → **only one ✓**

### PLAN COPIES (checkout/navigation sub-group)
Current: checkout (copy_checkout), checkout (cd) (copy_pr_checkout_script), checkout (copy_pr_checkout_plain), teleport, teleport (new slot)
**Sorted: checkout (copy_checkout), checkout (copy_pr_checkout_plain), checkout (cd) (copy_pr_checkout_script), teleport, teleport (new slot)**

### PLAN COPIES (workflow sub-group)
Current: cmux checkout, implement, dispatch, replan, land, close
**Sorted: close, cmux checkout, dispatch, implement, land, replan**

### PLAN COPIES (launch sub-group)
Current: rebase, address, rewrite → **Sorted: address, rebase, rewrite**

### OBJECTIVE COPIES
Current: plan, view, codespace → **Sorted: codespace, plan, view**

## Verification

- Run TUI tests: `pytest tests/tui/`
- Visual: `erk dash -i`, open command palette, confirm alphabetical order within each sub-group
