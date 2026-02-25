# Objective Plans Modal Screen

## Context

From the Objectives tab in `erk dash`, users want to press a single key on a selected objective to see all associated plans/PRs as a list. Currently the only plan visibility is `objective_head_plans` (blocking dependencies for the next node). There's no way to see the full list of plans linked to an objective without leaving the TUI.

## Approach

New modal screen (`ObjectivePlansScreen`) following the established `UnresolvedCommentsScreen` pattern. Key `d` (drill-down) opens it from the Objectives view. Data comes from a new provider method that reuses the existing `fetch_plans()` with client-side filtering by `objective_issue`.

## Changes

### 1. Add `fetch_plans_for_objective()` to provider ABC

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`

Add abstract method:
```python
@abstractmethod
def fetch_plans_for_objective(self, objective_issue: int) -> list[PlanRowData]:
```

### 2. Implement in real provider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`

Call `self.fetch_plans()` with `labels=("erk-plan",)`, `state=None` (open plans only — matches Plans tab), then filter where `row.objective_issue == objective_issue`.

### 3. Implement in fake provider

**File:** `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

Filter the stored plans list by `objective_issue` field. No new test helpers needed — existing `make_plan_row(objective_issue=N)` already supports this.

### 4. Create `ObjectivePlansScreen` modal

**New file:** `src/erk/tui/screens/objective_plans_screen.py`

Follow `UnresolvedCommentsScreen` pattern exactly:
- `ModalScreen` subclass with escape/q/space to dismiss
- `__init__` takes `provider`, `objective_id`, `objective_title`, `progress_display`
- `compose()` builds header (objective # + title + progress) + divider + loading placeholder + footer
- `on_mount()` triggers `_fetch_plans()` worker
- `@work(thread=True) _fetch_plans()` calls `provider.fetch_plans_for_objective()` with error boundary
- `_on_plans_loaded()` via `call_from_thread()` replaces loading label with plan list

**Display format** — each plan rendered as a Label row:
```
#7911  delete-issue-plan-backend    PR #8141  OPEN
#7813  eliminate-git-checkouts      PR #7991  OPEN
#7724  rename-issue-to-plan         PR #8139  OPEN
```

Add keybindings within the modal:
- `o` — open the highlighted/first plan in browser
- `enter` — open the selected plan issue in browser

Use a simple vertical list of Labels (not a DataTable) since there's no need for row selection/actions — this is a read-only drill-down view. Each plan line is a `ClickableLink` to the issue URL.

### 5. Add keybinding + action in app

**File:** `src/erk/tui/app.py`

Add binding:
```python
Binding("d", "drill_down", "Drill Down", show=False),
```

Add action:
```python
def action_drill_down(self) -> None:
    """Show plans for selected objective (Objectives view only)."""
    if self._view_mode != ViewMode.OBJECTIVES:
        return
    row = self._get_selected_row()
    if row is None:
        return
    self.push_screen(
        ObjectivePlansScreen(
            provider=self._provider,
            objective_id=row.plan_id,
            objective_title=row.full_title,
            progress_display=row.objective_progress_display,
        )
    )
```

### 6. Tests

**New file:** `tests/unit/tui/screens/test_objective_plans_screen.py`

- Test compose renders header with objective info
- Test fetch success populates plan list
- Test fetch error shows error message
- Test empty plans shows empty state
- Test escape dismisses

**File:** `tests/unit/gateway/plan_data_provider/test_fake.py` (or equivalent)

- Test `fetch_plans_for_objective()` filters correctly on both real and fake

## Key files to reference

- `src/erk/tui/screens/unresolved_comments_screen.py` — primary pattern to follow
- `src/erk/tui/screens/plan_body_screen.py` — secondary pattern reference
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` — ABC for new method
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` — `make_plan_row()` helper
- `src/erk/tui/app.py` — keybinding + action wiring

## Verification

1. Run `erk dash -i`, go to Objectives tab (press `3`)
2. Select an objective that has associated plans (e.g., #8088 or #8036)
3. Press `d` — modal should appear with plan list
4. Click a plan link or press `o` — should open in browser
5. Press Esc — modal should dismiss
6. Verify pressing `d` on Plans/Learn tabs does nothing
7. Run tests: `pytest tests/unit/tui/screens/test_objective_plans_screen.py`
