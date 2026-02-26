# Plan: Objective Filter for erk dash TUI

## Context

The erk dash TUI has a stack filter (`t` key) that filters the Plans view to show only PRs in a Graphite stack — a fast, inline interaction. Currently, viewing an objective's plans requires pressing `d` to open a modal (`ObjectivePlansScreen`), which is a different and heavier interaction pattern. The goal is to add an equivalent inline objective filter (`o` key) in the Plans view and eliminate the modal entirely.

The `o` key is currently bound to "open PR/issue in browser" (`action_open_row`), but `p` already opens PRs and `enter` opens the detail modal (which has browser-open options), making `o` redundant.

## Approach

Repurpose `o` as a toggle for objective filtering in the Plans view. When pressed on a plan linked to an objective, it filters the table to show only plans sharing that `objective_issue`. This mirrors exactly how `t` filters by Graphite stack.

## Changes

### 1. `src/erk/tui/app.py` — Core changes

**Add state variables** (after line 148, next to stack filter state):
```python
self._objective_filter_issue: int | None = None
self._objective_filter_label: str | None = None
```

**Replace `o` binding** (line 87): Change from `action_open_row` to `action_toggle_objective_filter`:
```python
Binding("o", "toggle_objective_filter", "Objective", show=False),
```

**Remove `d` binding** (line 99): Remove the `drill_down` binding entirely.

**Add `action_toggle_objective_filter`** method (new, mirrors `action_toggle_stack_filter`):
- Toggle off if already active → `_clear_objective_filter()`
- Get selected row; if `row.objective_issue is None` → status bar message "Plan not linked to an objective"
- Set `_objective_filter_issue = row.objective_issue`
- Filter all rows where `r.objective_issue == self._objective_filter_issue`
- Call `_apply_filter()`, show status bar: `"Objective: #{issue} ({count})"`

**Add `_clear_objective_filter`** method (new, mirrors `_clear_stack_filter`):
- Clear both state vars, call `_apply_filter()`, clear status message

**Update `_apply_filter_and_sort`** (line 302): Add objective filter step before stack filter:
```python
if self._objective_filter_issue is not None:
    rows = [r for r in rows if r.objective_issue == self._objective_filter_issue]
```

**Update `action_exit_app`** (line 386): Add objective filter to progressive escape chain before stack filter:
```python
if self._objective_filter_issue is not None:
    self._clear_objective_filter()
    return
```

**Update `_switch_view`** (line 439): Clear objective filter alongside stack filter:
```python
self._objective_filter_issue = None
self._objective_filter_label = None
```

**Remove `action_drill_down`** method (line 903-918) entirely.

**Remove `action_open_row`** method (line 970-984) entirely.

**Remove import** of `ObjectivePlansScreen` (line 26).

### 2. `src/erk/tui/screens/help_screen.py` — Update help text

- Remove line 79: `"o       Open PR (or issue if no PR)"`
- Add to "Filter & Sort" section (after `t` line 88): `"o       Filter to objective plans"`

### 3. `src/erk/tui/widgets/status_bar.py` — Update hint line

Update line 127 to add `o:obj` hint:
```python
"1-3:views  Enter:open  /:filter  t:stack  o:obj  s:sort  r:refresh  q:quit  ?:help"
```

### 4. Delete `src/erk/tui/screens/objective_plans_screen.py`

Entire file removed. The `_extract_plan_ids_from_roadmap` function is no longer needed since we filter by `objective_issue` field directly.

### 5. Delete `tests/tui/screens/test_objective_plans_screen.py`

Tests for the removed modal screen.

### 6. `tests/tui/test_app.py` — Add objective filter tests

Mirror the stack filter test pattern (lines 2866-3001). New tests:

- **`test_o_filters_plans_by_objective`** — Select plan with `objective_issue=42`, press `o`, verify only plans with `objective_issue=42` remain in `_rows`
- **`test_o_toggles_off_objective_filter`** — Activate filter, press `o` again, verify all rows restored
- **`test_o_on_plan_without_objective_shows_message`** — Plan has `objective_issue=None`, press `o`, verify status bar shows "Plan not linked to an objective"
- **`test_escape_clears_objective_filter`** — Activate filter, press Escape, verify filter cleared
- **`test_view_switch_clears_objective_filter`** — Activate filter, press `2`, verify filter cleared
- **`test_objective_filter_composes_with_text_filter`** — Activate objective filter, then text filter, verify both compose

Test data setup using existing `make_plan_row(plan_id, title, objective_issue=42)`.

## Key Files

| File | Action |
|------|--------|
| `src/erk/tui/app.py` | Modify — core filter logic |
| `src/erk/tui/screens/help_screen.py` | Modify — update help text |
| `src/erk/tui/widgets/status_bar.py` | Modify — update hint line |
| `src/erk/tui/screens/objective_plans_screen.py` | Delete |
| `tests/tui/screens/test_objective_plans_screen.py` | Delete |
| `tests/tui/test_app.py` | Modify — add objective filter tests |

## Reuse

- `_apply_filter_and_sort` pipeline (line 302) — extend, don't replace
- `_clear_stack_filter` pattern (line 535) — mirror for objective filter
- `action_toggle_stack_filter` pattern (line 503) — mirror for objective filter
- `make_plan_row` helper already supports `objective_issue` parameter
- `FakePlanDataProvider` needs no changes

## Verification

1. Run TUI tests: `uv run pytest tests/tui/ -x`
2. Manual test in `erk dash -i`:
   - Plans view: select a plan linked to an objective → press `o` → verify filter applies
   - Press `o` again → verify filter clears
   - Press `Escape` → verify filter clears
   - Select plan with no objective → press `o` → verify "Plan not linked to an objective" message
   - Activate filter → switch views (1/2/3) → verify filter clears
   - Activate both objective filter and text filter → verify they compose
