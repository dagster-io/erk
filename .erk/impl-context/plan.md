# Plan: Break Up `src/erk/tui/app.py` Into Organized Subpackage

## Context

`app.py` is 1686 lines with ~90 methods covering 12 distinct responsibility areas. It's the largest file in the TUI package. The rest of the TUI is well-organized into focused subpackages (`commands/`, `filtering/`, `sorting/`, `views/`, `screens/`, `widgets/`), but the main app class carries all the orchestration, background workers, action handlers, event handlers, and command palette dispatch in a single file.

The goal is to reduce `app.py` to a ~350-line orchestrator and extract cohesive modules following existing TUI conventions.

## Approach: Module Functions + Targeted Mixins

**Why mixins?** Textual requires `action_*` methods and `@on(...)` event handlers to live on the App class. We can't move them to standalone modules without forwarding stubs. Mixins let us split the class across files while keeping all methods accessible as `self.action_*()` at runtime.

**Why module functions too?** Pure utility functions (`_build_github_url`, `_extract_learn_plan_number`, etc.) and the `_OperationResult` dataclass have no dependency on the App class — they follow the existing `filtering/logic.py` and `sorting/types.py` extraction pattern.

## Proposed Structure

```
src/erk/tui/
├── app.py                              # ~350 lines (down from 1686)
├── operations/                         # NEW: background operation infrastructure
│   ├── __init__.py
│   ├── types.py                        # OperationResult dataclass
│   ├── logic.py                        # Pure helpers (last_output_line, extract_learn_plan_number, build_github_url)
│   ├── streaming.py                    # StreamingOperationsMixin (_run_streaming_operation, _start/_update/_finish_operation)
│   └── workers.py                      # BackgroundWorkersMixin (all @work(thread=True) methods)
├── actions/                            # NEW: keyboard action handlers
│   ├── __init__.py
│   ├── navigation.py                   # NavigationActionsMixin (detail, help, open_pr, open_run, cursor, etc.)
│   ├── filter_actions.py               # FilterActionsMixin (stack, objective, text filter toggling)
│   └── palette.py                      # PaletteActionsMixin (execute_palette_command + one-shot)
├── events.py                           # NEW: EventHandlersMixin (all @on(...) handlers)
├── commands/  filtering/  sorting/     # (unchanged)
├── screens/  widgets/  views/          # (unchanged)
└── styles/                             # (unchanged)
```

## File-by-File Breakdown

### `operations/types.py` (~20 lines)
- `OperationResult` frozen dataclass (renamed from `_OperationResult` — public in its own module)

### `operations/logic.py` (~30 lines)
- `last_output_line(result)` (renamed from `_last_output_line`)
- `extract_learn_plan_number(result)` (renamed from `_extract_learn_plan_number`)
- `build_github_url(plan_url, resource_type, number)` (renamed from `_build_github_url`)

### `operations/streaming.py` (~55 lines)
- `StreamingOperationsMixin` with:
  - `_start_operation(op_id, label)`
  - `_update_operation(op_id, progress)`
  - `_finish_operation(op_id)`
  - `_run_streaming_operation(op_id, command)` — Popen with live status bar streaming

### `operations/workers.py` (~350 lines)
- `BackgroundWorkersMixin` with all 12 `@work(thread=True)` methods:
  - `_close_plan_async`, `_address_remote_async`, `_rebase_remote_async`
  - `_cmux_sync_async`, `_cmux_focus_workspace`, `_rewrite_remote_async`
  - `_land_pr_async`, `_dispatch_to_queue_async`
  - `_close_objective_async`, `_check_objective_async`, `_one_shot_plan_async`
  - `_one_shot_dispatch_async`

### `actions/navigation.py` (~175 lines)
- `NavigationActionsMixin` with:
  - `action_exit_app`, `action_refresh`, `action_help`
  - `action_launch`, `_on_launch_result`
  - `action_show_detail`, `action_view_plan_body`, `action_view_comments`, `action_view_checks`
  - `action_cursor_down`, `action_cursor_up`
  - `action_open_pr`, `action_open_run`, `action_show_implement`
  - `action_copy_checkout`, `action_close_plan`, `_copy_checkout_command`
  - `_get_selected_row`

### `actions/filter_actions.py` (~130 lines)
- `FilterActionsMixin` with:
  - `action_start_filter`, `action_toggle_stack_filter`, `_clear_stack_filter`
  - `action_toggle_objective_filter`, `_clear_objective_filter`
  - `action_toggle_sort`, `_load_activity_and_resort`, `_on_activity_loaded`
  - `_apply_filter`, `_exit_filter_mode`

### `actions/palette.py` (~230 lines)
- `PaletteActionsMixin` with:
  - `execute_palette_command` (the large if/elif dispatcher)
  - `action_one_shot_prompt`, `_on_one_shot_prompt_result`

### `events.py` (~90 lines)
- `EventHandlersMixin` with all `@on(...)` handlers:
  - `on_row_selected`, `on_filter_changed`, `on_filter_submitted`
  - `on_view_tab_clicked`, `on_plan_clicked`, `on_pr_clicked`
  - `on_local_wt_clicked`, `on_run_id_clicked`, `on_deps_clicked`, `on_objective_clicked`

### `app.py` (~350 lines) — The reduced orchestrator
Retains:
- Class declaration with BINDINGS, CSS_PATH, COMMANDS
- MRO: `ErkDashApp(NavigationActionsMixin, FilterActionsMixin, PaletteActionsMixin, EventHandlersMixin, StreamingOperationsMixin, BackgroundWorkersMixin, App)`
- `__init__` (all state initialization)
- `get_system_commands`, `_display_name_for_view`
- `compose`, `on_mount`
- `_load_data`, `_update_table`, `_filter_rows_for_view`, `_apply_filter_and_sort` (data loading core)
- `_switch_view`, `action_switch_view_*`, `action_next_view`, `action_previous_view`
- `_start_refresh_timer`, `_tick_countdown`, `_notify_with_severity`

## Mixin Type Safety

Mixins access `self._table`, `self._status_bar`, `self._rows`, etc. Pattern for type hints:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erk.tui.app import ErkDashApp
```

Methods can use `self: ErkDashApp` in docstrings or comments. At runtime, `self` is always `ErkDashApp` through inheritance. This matches the existing `TYPE_CHECKING` import pattern used in `commands/provider.py` and `screens/plan_detail_screen.py`.

## Import Updates

### Test imports that change
| File | Old Import | New Import |
|------|-----------|------------|
| `test_utils.py` | `from erk.tui.app import _build_github_url` | `from erk.tui.operations.logic import build_github_url` |
| `test_async_operations.py` | `from erk.tui.app import _extract_learn_plan_number, _OperationResult` | `from erk.tui.operations.logic import extract_learn_plan_number` + `from erk.tui.operations.types import OperationResult` |
| `test_core.py` | `from erk.tui.app import ErkDashApp, HelpScreen` | `from erk.tui.app import ErkDashApp` + `from erk.tui.screens.help_screen import HelpScreen` |
| `test_command_palette.py` | `from erk.tui.app import ErkDashApp, PlanDetailScreen` | split to canonical imports |
| `test_streaming.py` | `from erk.tui.app import ErkDashApp, PlanDetailScreen` | split to canonical imports |
| `test_plan_detail_screen.py` | `from erk.tui.app import ErkDashApp, PlanDetailScreen` | split to canonical imports |
| `test_plan_body_screen.py` | `from erk.tui.app import ErkDashApp, PlanBodyScreen` | split to canonical imports |

### Production imports (unchanged)
- `from erk.tui.app import ErkDashApp` stays valid (class stays in app.py)
- TYPE_CHECKING imports in `commands/provider.py`, `plan_detail_screen.py`, `plan_table.py` stay valid

## Implementation Sequence

### Step 1: Create `operations/` subpackage (types + logic)
- Create `operations/__init__.py`, `operations/types.py`, `operations/logic.py`
- Move `_OperationResult` -> `OperationResult` and the 3 pure functions
- Update app.py imports
- Update test imports
- Run tests

### Step 2: Create `operations/streaming.py` (StreamingOperationsMixin)
- Extract the 4 operation-tracking methods
- Add to ErkDashApp inheritance
- Run tests

### Step 3: Create `operations/workers.py` (BackgroundWorkersMixin)
- Extract all 12 `@work(thread=True)` methods
- Add to ErkDashApp inheritance
- Run tests

### Step 4: Create `events.py` (EventHandlersMixin)
- Extract all `@on(...)` event handler methods
- Add to ErkDashApp inheritance
- Run tests

### Step 5: Create `actions/` subpackage
- Create `actions/__init__.py`, `actions/navigation.py`, `actions/filter_actions.py`, `actions/palette.py`
- Extract methods to respective mixins
- Add to ErkDashApp inheritance
- Run tests

### Step 6: Clean up test imports
- Update tests importing screen classes via app.py to use canonical locations
- Final comprehensive test run

## Verification

1. Run `make fast-ci` after each step
2. Verify `from erk.tui.app import ErkDashApp` still works
3. Run `erk dash -i` manually to verify TUI launches and responds to keys
4. Verify no circular imports by importing each new module independently
