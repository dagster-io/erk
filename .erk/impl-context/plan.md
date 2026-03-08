# Plan: Add "l" key to launch launchpad from ObjectiveNodesScreen

## Context

The TUI's launchpad menu (LaunchScreen) lets users quickly execute ACTION commands on a selected plan row via the "l" key. This works from the main planned PRs page but not from the ObjectiveNodesScreen modal (which shows individual plan/PR nodes within an objective). The user wants "l" to work here too, since nodes represent individual plans with PRs.

## Changes

### 1. `src/erk/tui/screens/objective_nodes_screen.py`

**A. Add import** for `LaunchScreen`:
```python
from erk.tui.screens.launch_screen import LaunchScreen
```

**B. Add "l" binding** to `BINDINGS` (before `ctrl+p`):
```python
Binding("l", "launch", "Launch", show=False),
```

**C. Add `action_launch` and `_on_launch_result` methods** (after `action_command_palette`):
- `action_launch`: get selected row via `_get_selected_row()`, create `CommandContext(row=row, view_mode=ViewMode.PLANS)`, push `LaunchScreen`
- `_on_launch_result`: delegate to `self.execute_command(command_id)`

**D. Extend `execute_command`** to handle ACTION commands. Follow the PlanDetailScreen pattern: dismiss the nodes screen, then call app-level methods directly with the row data. ACTION commands to handle:
- `close_plan` → `app._close_plan_async`
- `dispatch_to_queue` → `app._dispatch_to_queue_async`
- `land_pr` → `app._land_pr_async` (use keyword args, include `plan_id`)
- `rebase_remote` → `app._rebase_remote_async`
- `address_remote` → `app._address_remote_async`
- `rewrite_remote` → `app._rewrite_remote_async`
- `cmux_checkout`/`cmux_teleport` → `app._cmux_checkout_async`
- `incremental_dispatch` → `app.execute_palette_command("incremental_dispatch")`

Each uses `from erk.tui.app import ErkDashApp` (inline to avoid circular imports), calls `self.dismiss()`, then `isinstance(self.app, ErkDashApp)` guard before calling app methods.

**E. Update footer text** to include "l: launch":
```
"p: PR  o: objective  l: launch  Enter: detail  Ctrl+P: commands  Esc: close"
```

### 2. `src/erk/tui/commands/provider.py` — NodeCommandProvider

Remove the `_ALLOWED_CATEGORIES` filter so ACTION commands also appear in the Ctrl+P command palette from the nodes screen (consistent with launch screen showing them). Delete `_ALLOWED_CATEGORIES` class variable and the two `if cmd.category not in self._ALLOWED_CATEGORIES: continue` checks in `discover` and `search`. Update the docstring.

### Key Files
- `src/erk/tui/screens/objective_nodes_screen.py` — main changes
- `src/erk/tui/commands/provider.py` — remove category filter
- `src/erk/tui/screens/plan_detail_screen.py:772-868` — reference pattern for ACTION command dispatch
- `src/erk/tui/actions/palette.py:208-219` — reference for `land_pr` with correct keyword args

## Verification

1. Run `uv run pytest tests/tui/screens/test_objective_nodes_screen.py tests/tui/screens/test_launch_screen.py`
2. Manual: `erk dash -i`, switch to objectives view, enter an objective's nodes, press "l" on a node with a PR — should show launchpad with available actions
