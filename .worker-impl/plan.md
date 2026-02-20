# Break up tests/tui/test_app.py into a subpackage

## Context

`tests/tui/test_app.py` is a 2,167-line monolithic test file containing 22 test classes and 80 test methods. It tests the `ErkDashApp` TUI application from multiple angles: composition, data loading, navigation, screens, commands, and utilities. Breaking it into a `tests/tui/app/` subpackage with focused modules improves discoverability, enables targeted test runs, and follows the established pattern used by `tests/tui/commands/`, `tests/tui/data/`, etc.

## Target Structure

Delete `tests/tui/test_app.py` and create the following subpackage:

```
tests/tui/app/
├── __init__.py                        # Required: """Tests for ErkDashApp."""
├── test_compose.py                    # App composition and layout
├── test_data_loading.py               # Data fetching on mount, error handling
├── test_navigation.py                 # Keyboard navigation, quit, help, refresh
├── test_status_bar.py                 # StatusBar widget (sync tests)
├── test_filter_mode.py                # Filter input behavior (/ key)
├── test_open_and_learn.py             # Row open (o key), learn click handlers
├── test_detail_screen.py              # PlanDetailScreen modal lifecycle
├── test_detail_screen_copy.py         # Detail screen copy shortcuts (1, 3, c, e)
├── test_command_palette.py            # Command palette from main + specific commands
├── test_streaming_commands.py         # Streaming command timeout, dismiss-blocked
├── test_close_plan.py                 # Close plan via palette + in-process close
├── test_plan_body_screen.py           # PlanBodyScreen modal (v key)
├── test_view_switching.py             # View switching (1/2/3, arrow keys, cache)
├── test_utilities.py                  # _build_github_url helper
└── test_view_comments.py             # action_view_comments (c key from main)
```

## Changes: File-by-file

### 1. Create `tests/tui/app/__init__.py`

```python
"""Tests for ErkDashApp."""
```

### 2. Create `tests/tui/app/test_compose.py`

**Classes moved:** `TestErkDashAppCompose` (lines 26-44)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider
```

Contains 1 test: `test_app_has_required_widgets`

### 3. Create `tests/tui/app/test_data_loading.py`

**Classes moved:** `TestErkDashAppDataLoading` (lines 46-91)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 2 tests: `test_fetches_data_on_mount`, `test_api_error_shows_notification_and_empty_table`

### 4. Create `tests/tui/app/test_navigation.py`

**Classes moved:** `TestErkDashAppNavigation` (lines 94-134), `TestErkDashAppRefresh` (lines 137-157)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp, HelpScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 4 tests across 2 classes: `test_quit_on_q`, `test_quit_on_escape`, `test_help_on_question_mark`, `test_refresh_on_r`

### 5. Create `tests/tui/app/test_status_bar.py`

**Classes moved:** `TestStatusBar` (lines 160-190)

**Imports needed:**
```python
from erk.tui.widgets.status_bar import StatusBar
```

Contains 4 sync tests (no `@pytest.mark.asyncio`): `test_set_plan_count_singular`, `test_set_plan_count_plural`, `test_set_message`, `test_clear_message`

### 6. Create `tests/tui/app/test_filter_mode.py`

**Classes moved:** `TestFilterMode` (lines 231-393)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Note: `textual.widgets.Input` and `erk.tui.filtering.types.FilterMode` are imported inline within test methods (lines 249, 300-302, 334). Preserve these inline imports as-is.

Contains 6 tests: `test_slash_activates_filter_mode`, `test_filter_narrows_results`, `test_escape_clears_then_exits`, `test_enter_returns_focus_to_table`, `test_filter_by_issue_number`, `test_filter_by_pr_number`

### 7. Create `tests/tui/app/test_open_and_learn.py`

**Classes moved:** `TestOpenRow` (lines 395-452), `TestOnLearnClicked` (lines 455-579)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.widgets.plan_table import PlanDataTable
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 6 tests across 2 classes: `test_o_opens_pr_when_available`, `test_o_opens_issue_when_no_pr`, `test_learn_click_opens_pr_when_both_pr_and_issue_set`, `test_learn_click_opens_issue_when_only_issue_set`, `test_learn_click_does_nothing_when_no_learn_data`, `test_learn_click_does_nothing_when_no_issue_url`

### 8. Create `tests/tui/app/test_detail_screen.py`

**Classes moved:** `TestPlanDetailScreen` (lines 582-732)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 6 tests: `test_space_opens_detail_screen`, `test_detail_modal_dismisses_on_escape`, `test_detail_modal_dismisses_on_q`, `test_detail_modal_dismisses_on_space`, `test_detail_modal_displays_full_title`, `test_detail_modal_shows_pr_info_when_linked`

### 9. Create `tests/tui/app/test_detail_screen_copy.py`

**Classes moved:** `TestPlanDetailScreenCopyActions` (lines 734-848)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 4 tests: `test_copy_prepare_shortcut_1`, `test_copy_submit_shortcut_3`, `test_copy_checkout_shortcut_c_with_local_worktree`, `test_copy_pr_checkout_shortcut_e`

### 10. Create `tests/tui/app/test_command_palette.py`

**Classes moved:** `TestCommandPaletteFromMain` (lines 851-937), `TestExecutePaletteCommandLandPR` (lines 940-1013), `TestExecutePaletteCommandSubmitToQueue` (lines 1016-1047), `TestExecutePaletteCommandFixConflictsRemote` (lines 1050-1139), `TestExecutePaletteCommandCodespaceRunPlan` (lines 2056-2087)

**Imports needed:**
```python
from collections.abc import Callable
from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.clipboard.fake import FakeClipboard
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 11 tests across 5 classes. Note: `TestExecutePaletteCommandFixConflictsRemote.test_execute_palette_command_fix_conflicts_remote_pushes_screen_and_runs_command` uses `monkeypatch: pytest.MonkeyPatch` and patches `PlanDetailScreen.run_streaming_command`.

### 11. Create `tests/tui/app/test_streaming_commands.py`

**Classes moved:** `TestStreamingCommandTimeout` (lines 1142-1319)

**Imports needed:**
```python
from pathlib import Path

import pytest

from erk.tui.app import ErkDashApp, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 4 tests: `test_timeout_fires_and_kills_process`, `test_successful_command_cancels_timer`, `test_timeout_disabled_when_zero`, `test_dismiss_blocked_during_command`

### 12. Create `tests/tui/app/test_close_plan.py`

**Classes moved:** `TestClosePlanViaCommandPalette` (lines 193-228), `TestClosePlanInProcess` (lines 1321-1401)

**Imports needed:**
```python
import pytest
from erk.tui.app import ErkDashApp, PlanDetailScreen
from erk.tui.data.types import PlanFilters
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 4 tests across 2 classes: `test_close_plan_not_accessible_via_c_key`, `test_close_plan_in_process_creates_output_panel`, `test_close_plan_in_process_removes_plan_from_list`

Wait — `TestClosePlanViaCommandPalette` has 1 test, `TestClosePlanInProcess` has 2 tests = 3 total.

### 13. Create `tests/tui/app/test_plan_body_screen.py`

**Classes moved:** `TestPlanBodyScreen` (lines 1404-1644)

**Imports needed:**
```python
import pytest
from textual.widgets import Markdown

from erk.tui.app import ErkDashApp, PlanBodyScreen
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 9 tests: `test_v_key_opens_issue_body_screen`, `test_issue_body_screen_fetches_and_shows_content`, `test_issue_body_screen_dismisses_on_escape`, `test_issue_body_screen_dismisses_on_q`, `test_issue_body_screen_dismisses_on_space`, `test_issue_body_screen_shows_empty_message_when_no_content`, `test_issue_body_screen_shows_plan_number_and_title`, `test_issue_body_screen_renders_content_as_markdown`, `test_objective_view_shows_objective_header_and_fetches_content`

### 14. Create `tests/tui/app/test_view_switching.py`

**Classes moved:** `TestViewSwitching` (lines 1663-2053)

**Imports needed:**
```python
import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.views.types import ViewMode, get_view_config
from erk.tui.widgets.view_bar import ViewBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 14 tests: `test_app_has_view_bar`, `test_default_view_is_plans`, `test_pressing_2_switches_to_learn_view`, `test_plans_view_excludes_learn_plans`, `test_pressing_3_switches_to_objectives_view`, `test_pressing_1_returns_to_plans_view`, `test_same_view_key_is_noop`, `test_view_bar_updates_on_switch`, `test_right_arrow_wraps_from_last_to_first`, `test_left_arrow_wraps_from_first_to_last`, `test_data_cache_avoids_refetch`, `test_stale_fetch_does_not_update_display`, `test_right_arrow_cycles_to_next_view`, `test_left_arrow_cycles_to_previous_view`

### 15. Create `tests/tui/app/test_utilities.py`

**Classes moved:** `TestBuildGithubUrl` (lines 1647-1660)

**Imports needed:**
```python
from erk.tui.app import _build_github_url
```

Contains 2 sync tests: `test_build_github_url_for_pull_request`, `test_build_github_url_for_issue`

### 16. Create `tests/tui/app/test_view_comments.py`

**Classes moved:** `TestActionViewComments` (lines 2090-2167)

**Imports needed:**
```python
import pytest

from erk.tui.app import ErkDashApp
from erk.tui.data.types import PlanFilters
from erk.tui.screens.unresolved_comments_screen import UnresolvedCommentsScreen
from erk.tui.widgets.status_bar import StatusBar
from erk_shared.gateway.plan_data_provider.fake import FakePlanDataProvider, make_plan_row
```

Contains 4 tests: `test_no_selected_row_does_nothing`, `test_no_pr_linked_shows_status_message`, `test_zero_unresolved_shows_status_message`, `test_unresolved_comments_pushes_screen`

### 17. Delete `tests/tui/test_app.py`

After all modules are created and verified, delete the original monolithic file.

## Implementation Details

### Docstrings
Each new file gets a module docstring describing its scope. Example for `test_compose.py`:
```python
"""Tests for ErkDashApp composition and layout."""
```

### Import conventions
- Absolute imports only (no relative imports)
- Stdlib → third-party → local ordering
- Each file includes only the imports it needs (no copy-paste of the full import block)
- Inline imports (like `from textual.widgets import Input` inside test methods in `test_filter_mode.py`) are preserved exactly as-is

### Test class and method names
All class names, method names, docstrings, and test logic are preserved exactly. No renaming, no rewriting.

### No shared fixtures or conftest.py
Each file is self-contained. No `conftest.py` in `tests/tui/app/`. Each test creates its own `FakePlanDataProvider`, `FakeClipboard`, etc. inline, matching the current pattern.

## Files NOT Changing

- `tests/tui/__init__.py` — unchanged
- `tests/tui/test_plan_table.py` — unchanged (separate widget tests)
- `tests/tui/test_view_bar.py` — unchanged (separate widget tests)
- All existing subdirectories (`commands/`, `data/`, `filtering/`, `jsonl_viewer/`, `screens/`, `views/`) — unchanged
- Any source files in `src/erk/tui/` — unchanged (this is a test reorganization only)
- `CHANGELOG.md` — never modify

## Verification

1. **Run the new test subpackage:** `pytest tests/tui/app/ -v` — all 80 tests should pass
2. **Run the full TUI test suite:** `pytest tests/tui/ -v` — no regressions in other test files
3. **Verify old file is gone:** `tests/tui/test_app.py` should not exist
4. **Count check:** Sum of tests across all new files = 80 (matching original)
5. **Type check:** `ty check tests/tui/app/` passes (or at least no new errors)
6. **Lint check:** `ruff check tests/tui/app/` passes

## Test Count Verification

| File | Classes | Tests |
|------|---------|-------|
| test_compose.py | 1 | 1 |
| test_data_loading.py | 1 | 2 |
| test_navigation.py | 2 | 4 |
| test_status_bar.py | 1 | 4 |
| test_filter_mode.py | 1 | 6 |
| test_open_and_learn.py | 2 | 6 |
| test_detail_screen.py | 1 | 6 |
| test_detail_screen_copy.py | 1 | 4 |
| test_command_palette.py | 5 | 11 |
| test_streaming_commands.py | 1 | 4 |
| test_close_plan.py | 2 | 3 |
| test_plan_body_screen.py | 1 | 9 |
| test_view_switching.py | 1 | 14 |
| test_utilities.py | 1 | 2 |
| test_view_comments.py | 1 | 4 |
| **TOTAL** | **22** | **80** |