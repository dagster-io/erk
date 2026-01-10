# Plan: Reorganize src/erk/tui/app.py

## Goal

Split the 1752-line `app.py` file into focused modules, reducing token count from ~15,600 to ~8,300 tokens (~47% reduction).

## Files to Create

### 1. `src/erk/tui/screens/__init__.py`
```python
from erk.tui.screens.help_screen import HelpScreen
from erk.tui.screens.issue_body_screen import IssueBodyScreen
from erk.tui.screens.plan_detail_screen import PlanDetailScreen
```

### 2. `src/erk/tui/screens/help_screen.py`
- Move `HelpScreen` class (lines 128-208)
- Imports: `textual.app.ComposeResult`, `textual.binding.Binding`, `textual.screen.ModalScreen`, `textual.containers.Vertical`, `textual.widgets.Label`

### 3. `src/erk/tui/screens/issue_body_screen.py`
- Move `IssueBodyScreen` class (lines 210-372)
- Imports: `textual` components, `Markdown`, `work` decorator
- Import `PlanDataProvider` from `erk.tui.data.provider`

### 4. `src/erk/tui/screens/plan_detail_screen.py`
- Move `PlanDetailScreen` class (lines 374-1092)
- Imports: `subprocess`, `Path`, textual components, `Timer`
- Import `ClickableLink`, `CopyableLabel` from widgets
- Import `CommandExecutor`, `CommandOutputPanel`, `PlanRowData`
- TYPE_CHECKING imports for `BrowserLauncher`, `Clipboard`

### 5. `src/erk/tui/widgets/clickable_link.py`
- Move `ClickableLink` class (lines 41-76)
- Imports: `typing.Any`, `rich.markup.escape`, `textual.events.Click`, `textual.widgets.Static`

### 6. `src/erk/tui/widgets/copyable_label.py`
- Move `CopyableLabel` class (lines 78-126)
- Imports: `typing.Any`, `textual.events.Click`, `textual.widgets.Static`

## Files to Modify

### 7. `src/erk/tui/widgets/__init__.py`
- Add exports for `ClickableLink`, `CopyableLabel`

### 8. `src/erk/tui/app.py`
- Remove moved classes
- Add imports from new locations:
  ```python
  from erk.tui.screens import HelpScreen, IssueBodyScreen, PlanDetailScreen
  from erk.tui.widgets.clickable_link import ClickableLink
  from erk.tui.widgets.copyable_label import CopyableLabel
  ```
- Keep only `ErkDashApp` class

## Implementation Order

1. Create `widgets/clickable_link.py` and `widgets/copyable_label.py`
2. Update `widgets/__init__.py` with new exports
3. Create `screens/` directory with `__init__.py`
4. Create `screens/help_screen.py`
5. Create `screens/issue_body_screen.py`
6. Create `screens/plan_detail_screen.py`
7. Update `app.py` - remove moved code, add imports
8. Run tests to verify no regressions

## Verification

1. Run `make fast-ci` to verify:
   - Type checking passes
   - Linting passes
   - Unit tests pass
2. Manual verification: `erk dash -i` still works

## Critical Files

- `src/erk/tui/app.py` (main file being split)
- `tests/tui/test_app.py` (existing tests - should still pass)