# Split tests/tui/test_app.py into Sub-Module

## Context

`tests/tui/test_app.py` has grown to 3,802 lines with 33 classes (31 test classes, 1 helper class, 1 fake) and 2 standalone test functions — roughly 6-8x the project's recommended threshold. The surrounding `tests/tui/` directory already uses subdirectories for focused areas (`commands/`, `data/`, `filtering/`, `screens/`, `views/`). Creating `tests/tui/app/` follows that established pattern.

This is a pure mechanical refactor: move test classes into logically grouped files. No test logic changes. No production code changes.

## Changes

### Step 1: Create `tests/tui/app/` directory with `__init__.py`

Create an empty `tests/tui/app/__init__.py` (matching the pattern used by `tests/tui/commands/__init__.py` and other subdirectories).

### Step 2: Create 12 test files + 1 utility file

Each file gets only the imports it actually uses. All imports come from the same pool used by the original file:

```python
from pathlib import Path
import pytest
from textual.widgets import Markdown
from erk.tui.app import (
    ErkDashApp, HelpScreen, PlanBodyScreen, PlanDetailScreen,
    _build_github_url, _should_trigger_learn,
)
from erk.tui.data.types import PlanFilters
from erk.tui.screens.launch_screen import LaunchScreen
from erk.tui.screens.unresolved_comments_screen import UnresolvedCommentsScreen
from erk.tui.views.types import ViewMode, get_view_config
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk.tui.widgets.view_bar import ViewBar
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Below is the exact mapping from source classes/functions to destination files. Line ranges are from the current `tests/tui/test_app.py` (3,802 lines total).

---

#### `tests/tui/app/test_core.py` (~110 lines)

Test classes for basic app composition, data loading, navigation, and refresh:

| Class                       | Source Lines | Description                        |
| --------------------------- | ------------ | ---------------------------------- |
| `TestErkDashAppCompose`     | 27–45        | App composition and layout         |
| `TestErkDashAppDataLoading` | 47–93        | Data loading behavior              |
| `TestErkDashAppNavigation`  | 95–156       | Keyboard navigation (q, escape, ?) |
| `TestErkDashAppRefresh`     | 158–179      | Data refresh behavior (r key)      |

**Imports needed:** `pytest`, `ErkDashApp`, `HelpScreen`, `PlanFilters`, `PlanDataTable`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_status_bar.py` (~60 lines)

| Class           | Source Lines | Description                                            |
| --------------- | ------------ | ------------------------------------------------------ |
| `TestStatusBar` | 181–239      | StatusBar widget (plan count, messages, fetch timings) |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_filter_mode.py` (~165 lines)

| Class            | Source Lines | Description                                       |
| ---------------- | ------------ | ------------------------------------------------- |
| `TestFilterMode` | 279–441      | "/" filter mode (activate, narrow, escape, focus) |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `PlanDataTable`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_plan_detail_screen.py` (~390 lines)

| Class                                        | Source Lines | Description                                         |
| -------------------------------------------- | ------------ | --------------------------------------------------- |
| `TestPlanDetailScreen`                       | 443–593      | Plan detail modal (space opens, escape/q dismisses) |
| `TestPlanDetailScreenCopyActions`            | 595–710      | Copy actions in detail screen                       |
| `TestPlanDetailScreenFixConflictsKeybinding` | 712–786      | Fix conflicts keybinding                            |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanDetailScreen`, `PlanFilters`, `StatusBar`, `FakeClipboard`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_command_palette.py` (~350 lines)

| Class                                         | Source Lines | Description                              |
| --------------------------------------------- | ------------ | ---------------------------------------- |
| `TestClosePlanViaCommandPalette`              | 241–277      | Close plan command palette integration   |
| `TestCommandPaletteFromMain`                  | 788–855      | Command palette activation from main app |
| `TestCommandPaletteFromMainCopyVariants`      | 857–916      | Copy command variants                    |
| `TestExecutePaletteCommandLandPR`             | 918–967      | Land PR command execution                |
| `TestExecutePaletteCommandFixConflictsRemote` | 969–1032     | Fix conflicts remote command             |
| `TestExecutePaletteCommandCodespaceRunPlan`   | 1989–2021    | Codespace run plan command               |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `StatusBar`, `FakeClipboard`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_streaming.py` (~180 lines)

| Class                         | Source Lines | Description                        |
| ----------------------------- | ------------ | ---------------------------------- |
| `TestStreamingCommandTimeout` | 1034–1211    | Streaming command timeout handling |
| `TestClosePlanInProcess`      | 1213–1294    | Close plan in-process execution    |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_plan_body_screen.py` (~245 lines)

| Class                | Source Lines | Description                     |
| -------------------- | ------------ | ------------------------------- |
| `TestPlanBodyScreen` | 1296–1588    | Plan body screen modal behavior |

**Imports needed:** `pytest`, `Markdown`, `ErkDashApp`, `PlanBodyScreen`, `PlanFilters`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_view_switching.py` (~420 lines)

| Class                                                    | Source Lines | Description                               |
| -------------------------------------------------------- | ------------ | ----------------------------------------- |
| `TestViewSwitching`                                      | 1606–1987    | View switching (1/2/3 keys, persistence)  |
| `test_display_name_plans_view` (standalone function)     | 2106–2111    | \_display_name_for_view() for PLANS mode  |
| `test_display_name_non_plans_view` (standalone function) | 2114–2122    | \_display_name_for_view() for other modes |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `ViewMode`, `get_view_config`, `ViewBar`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_actions.py` (~200 lines)

| Class                    | Source Lines | Description                    |
| ------------------------ | ------------ | ------------------------------ |
| `TestActionViewComments` | 2023–2101    | View comments action ('e' key) |
| `TestActionLaunch`       | 2125–2245    | Launch action ('l' key)        |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `LaunchScreen`, `UnresolvedCommentsScreen`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_async_operations.py` (~850 lines)

| Class                         | Source Lines | Description                            |
| ----------------------------- | ------------ | -------------------------------------- |
| `TestAddressRemoteAsync`      | 2247–2312    | Address remote async operation         |
| `TestFixConflictsRemoteAsync` | 2314–2414    | Fix conflicts remote async             |
| `TestLandPrAsync`             | 2416–2814    | Land PR async operation                |
| `TestShouldTriggerLearn`      | 2816–2840    | \_should_trigger_learn helper function |
| `TestDispatchToQueueAsync`    | 2842–2935    | Dispatch to queue async                |
| `TestCloseObjectiveAsync`     | 2937–3000    | Close objective async                  |
| `TestCheckObjectiveAsync`     | 3002–3066    | Check objective async                  |
| `TestOneShotPlanAsync`        | 3068–3132    | One-shot plan async                    |

**Imports needed:** `pytest`, `Path`, `ErkDashApp`, `_should_trigger_learn`, `PlanFilters`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_operation_tracking.py` (~290 lines)

| Class                   | Source Lines | Description                                      |
| ----------------------- | ------------ | ------------------------------------------------ |
| `_FakePopen`            | 3134–3142    | Fake subprocess.Popen (helper class, NOT a test) |
| `TestOperationTracking` | 3145–3435    | Multi-operation status bar tracking              |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

**Note:** `_FakePopen` is only used within `TestOperationTracking`, so it stays in this file rather than being extracted to a shared utils module.

---

#### `tests/tui/app/test_app_filtering.py` (~370 lines)

| Class                 | Source Lines | Description                              |
| --------------------- | ------------ | ---------------------------------------- |
| `TestStackFilter`     | 3437–3637    | Stack filter functionality ('t' key)     |
| `TestObjectiveFilter` | 3639–3803    | Objective filter functionality ('o' key) |

**Imports needed:** `pytest`, `ErkDashApp`, `PlanFilters`, `StatusBar`, `FakePlanDataProvider`, `make_plan_row`

---

#### `tests/tui/app/test_utils.py` (~25 lines)

| Class                | Source Lines | Description                        |
| -------------------- | ------------ | ---------------------------------- |
| `TestBuildGithubUrl` | 1590–1604    | \_build_github_url helper function |

**Imports needed:** `_build_github_url`

---

### Step 3: Delete `tests/tui/test_app.py`

After all classes are moved to their new files, delete the original monolith.

## Implementation Details

### File creation pattern

For each new file:

1. Add the module docstring (e.g., `"""Tests for ErkDashApp core composition and data loading."""`)
2. Add only the imports that file needs (not the full import block)
3. Copy the test classes verbatim — no refactoring, no renaming, no logic changes
4. Preserve blank lines between classes (2 blank lines between top-level definitions per PEP 8)

### Import optimization

Each file should import only what it uses. This is the mapping of which symbols each file needs (detailed in each file section above). The implementing agent should verify each import is actually used in the destination file — do not carry unused imports.

### No shared conftest.py needed

The original file has no fixtures in a conftest. All test setup is inline (constructing `FakePlanDataProvider`, `PlanFilters.default()`, `ErkDashApp` in each test method). No conftest.py is needed for the new `tests/tui/app/` directory.

### `_FakePopen` placement

`_FakePopen` (lines 3134–3142) is a private helper class used only by `TestOperationTracking`. Keep it in `test_operation_tracking.py` — do not extract to a shared module.

## Files NOT Changing

- **No production code changes** — this is purely a test reorganization
- **No other test files** — only `tests/tui/test_app.py` is affected
- **No conftest.py files** — none exist and none are needed
- **No CHANGELOG.md** — per project rules
- Other `tests/tui/` subdirectories (`commands/`, `data/`, `filtering/`, `screens/`, `views/`, `jsonl_viewer/`) are untouched

## Verification

1. **All tests pass:** Run `pytest tests/tui/app/ -v` — all tests from the original file should pass in their new locations
2. **No test loss:** Run `pytest tests/tui/app/ --collect-only` and verify the total collected test count matches the original file's count
3. **Original deleted:** Verify `tests/tui/test_app.py` no longer exists
4. **No import errors:** Ensure pytest collection succeeds with no import errors
5. **Full suite still passes:** Run `pytest tests/tui/ -v` to confirm no regressions in the broader TUI test suite
6. **Linting passes:** Run `ruff check tests/tui/app/` to verify no lint issues (unused imports, etc.)
7. **Type checking passes:** Run `ty check tests/tui/app/` to verify no type errors
