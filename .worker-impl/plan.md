# Fix TUI Workflow Launch Commands

## Problem

The TUI is using `erk workflow launch <workflow-name>` but the correct CLI command is `erk launch <workflow-name>`. The "workflow" subcommand doesn't exist, causing "No such command" errors when launching workflows from the TUI.

## Root Cause

The command arrays in the TUI include an extra `"workflow"` element that shouldn't be there:
- Current (broken): `["erk", "workflow", "launch", "pr-fix-conflicts", ...]`
- Correct: `["erk", "launch", "pr-fix-conflicts", ...]`

## Files to Modify

### 1. `src/erk/tui/app.py`

**Line 627-630** - fix_conflicts_remote command:
```python
# Remove "workflow" from:
["erk", "workflow", "launch", "pr-fix-conflicts", "--pr", str(row.pr_number)]
# To:
["erk", "launch", "pr-fix-conflicts", "--pr", str(row.pr_number)]
```

**Line 659** - address_remote command:
```python
# Remove "workflow" from:
["erk", "workflow", "launch", "pr-address", "--pr", str(row.pr_number)]
# To:
["erk", "launch", "pr-address", "--pr", str(row.pr_number)]
```

### 2. `src/erk/tui/screens/plan_detail_screen.py`

**Line 362** - action_fix_conflicts_remote:
```python
# Remove "workflow" from:
["erk", "workflow", "launch", "pr-fix-conflicts", "--pr", str(self._row.pr_number)]
# To:
["erk", "launch", "pr-fix-conflicts", "--pr", str(self._row.pr_number)]
```

**Line 659** - fix_conflicts_remote command handler:
```python
# Remove "workflow" from:
["erk", "workflow", "launch", "pr-fix-conflicts", "--pr", str(row.pr_number)]
# To:
["erk", "launch", "pr-fix-conflicts", "--pr", str(row.pr_number)]
```

**Line 667** - address_remote command handler:
```python
# Remove "workflow" from:
["erk", "workflow", "launch", "pr-address", "--pr", str(row.pr_number)]
# To:
["erk", "launch", "pr-address", "--pr", str(row.pr_number)]
```

## Note

The display names in `src/erk/tui/commands/registry.py` are already correct:
- Line 37: `f"erk launch pr-fix-conflicts --pr {ctx.row.pr_number}"`
- Line 42: `f"erk launch pr-address --pr {ctx.row.pr_number}"`

No changes needed there.

## Verification

1. Run `erk dash -i` to open the interactive TUI
2. Select a plan with a PR
3. Press Ctrl+P to open command palette
4. Select "fix-conflicts" or "address" action
5. Verify the command executes without "No such command" error