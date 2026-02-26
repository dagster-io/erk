# Plan: Split tests/tui/test_app.py into Sub-Module

## Context

`tests/tui/test_app.py` has grown to 3,640 lines with 32 test classes — roughly 6-8x the project's recommended threshold ("split when 5+ functions, 3+ tests each"). The surrounding `tests/tui/` directory already uses subdirectories for focused areas (`commands/`, `data/`, `filtering/`, `screens/`, `views/`). Creating `tests/tui/app/` follows that established pattern.

## Approach

Create `tests/tui/app/` subdirectory. Move all test classes into logically grouped files. Delete the original monolith. Each file gets only the imports it needs.

## File Structure

```
tests/tui/app/
├── __init__.py                   (empty)
├── test_core.py                  (~110 lines)
├── test_status_bar.py            (~60 lines)
├── test_filter_mode.py           (~165 lines)
├── test_plan_detail_screen.py    (~390 lines)
├── test_command_palette.py       (~350 lines)
├── test_streaming.py             (~180 lines)
├── test_plan_body_screen.py      (~245 lines)
├── test_view_switching.py        (~420 lines)
├── test_actions.py               (~200 lines)
├── test_async_operations.py      (~850 lines)
├── test_operation_tracking.py    (~290 lines)
├── test_app_filtering.py         (~370 lines)
└── test_utils.py                 (~25 lines)
```

## File Contents (Test Class Mapping)

| File | Test Classes |
|------|-------------|
| `test_core.py` | `TestErkDashAppCompose`, `TestErkDashAppDataLoading`, `TestErkDashAppNavigation`, `TestErkDashAppRefresh` |
| `test_status_bar.py` | `TestStatusBar` |
| `test_filter_mode.py` | `TestFilterMode` |
| `test_plan_detail_screen.py` | `TestPlanDetailScreen`, `TestPlanDetailScreenCopyActions`, `TestPlanDetailScreenFixConflictsKeybinding` |
| `test_command_palette.py` | `TestClosePlanViaCommandPalette`, `TestCommandPaletteFromMain`, `TestCommandPaletteFromMainCopyVariants`, `TestExecutePaletteCommandLandPR`, `TestExecutePaletteCommandFixConflictsRemote`, `TestExecutePaletteCommandCodespaceRunPlan` |
| `test_streaming.py` | `TestStreamingCommandTimeout`, `TestClosePlanInProcess` |
| `test_plan_body_screen.py` | `TestPlanBodyScreen` |
| `test_view_switching.py` | `TestViewSwitching` |
| `test_actions.py` | `TestActionViewComments`, `TestActionLaunch`, `TestShouldTriggerLearn`, standalone `test_display_name_*` functions |
| `test_async_operations.py` | `TestAddressRemoteAsync`, `TestFixConflictsRemoteAsync`, `TestLandPrAsync`, `TestDispatchToQueueAsync`, `TestCloseObjectiveAsync`, `TestCheckObjectiveAsync`, `TestOneShotPlanAsync` |
| `test_operation_tracking.py` | `TestOperationTracking` |
| `test_app_filtering.py` | `TestStackFilter`, `TestObjectiveFilter` |
| `test_utils.py` | `TestBuildGithubUrl`, `_build_github_url` import |

## Implementation Steps

1. Create `tests/tui/app/__init__.py` (empty)
2. For each target file listed above:
   - Extract the relevant test classes/functions from `tests/tui/test_app.py`
   - Include only the imports each file needs
   - Write the file to `tests/tui/app/<filename>`
3. Delete `tests/tui/test_app.py`

## Key Imports (shared across files)

Most files will use a subset of:
```python
from pathlib import Path
import pytest
from erk.tui.app import ErkDashApp, HelpScreen, PlanBodyScreen, PlanDetailScreen, _build_github_url, _should_trigger_learn
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode, get_view_config
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk.tui.widgets.view_bar import ViewBar
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

## Critical Files

- **Source**: `tests/tui/test_app.py` (3,640 lines — read fully before splitting)
- **Reference structure**: `tests/tui/commands/__init__.py` (empty, the pattern to follow)
- **Pattern**: `tests/tui/screens/` for how existing subdirectories are organized

## Verification

```bash
uv run pytest tests/tui/app/ -x
```

All tests that previously passed should still pass. The original file will be gone, so any reference to it in CI or tooling should also be verified.
