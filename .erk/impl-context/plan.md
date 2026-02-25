# Plan: Embed PlanDataTable in ObjectivePlansScreen Modal

## Context

The `ObjectivePlansScreen` modal currently shows plans as plain text labels via `_format_plan_rows()` — a basic list of `#ID  Title  PR #NNN  STATE` strings. The user wants it upgraded to embed the full `PlanDataTable` widget (the same rich, interactive table from `erk dash -i`), filtered to show only the plans associated with the objective. This gives the modal all the columns, formatting, and click interactivity of the main plans view.

## Files to Modify

1. **`src/erk/tui/screens/objective_plans_screen.py`** — Major rewrite
2. **`tests/tui/screens/test_objective_plans_screen.py`** — Update tests

## Implementation

### 1. Rewrite `objective_plans_screen.py`

**Keep:**
- `_extract_plan_ids_from_roadmap()` — still needed for fetching
- Constructor signature (same params from `app.py` call site)
- `@work(thread=True)` fetch pattern with error boundary
- Dismiss bindings (Escape, q)

**Remove:**
- `_format_plan_rows()` function — replaced by PlanDataTable rendering
- Label-based plan row rendering in `_on_plans_loaded`

**Add:**
- Import `PlanDataTable` from `erk.tui.widgets.plan_table`
- Import `PlanFilters` from `erk.tui.data.types`
- In `compose()`: yield a `PlanDataTable(PlanFilters.default())` inside the content container (hidden initially, with loading label)
- In `_on_plans_loaded()`: call `self._table.populate(plans)` and show the table, remove loading label
- Handle `PlanDataTable` click messages with `@on()` decorators:
  - `PlanClicked` → open issue URL in browser via `self._provider.browser.launch()`
  - `PrClicked` → open PR URL in browser
  - `RunIdClicked` → open run URL in browser
  - `LocalWtClicked` → copy worktree name to clipboard
  - `BranchClicked` → copy branch name to clipboard
  - Ignore `ObjectiveClicked` and `DepsClicked` (not relevant in this context)
- Add keybindings: `o` to open selected plan issue, `p` to open PR, `enter` to open issue (matching main dash)
- Add `j`/`k` vim navigation bindings
- Store `self._rows` list for action handlers to reference by row index

**PlanDataTable cursor_left/right issue:** The current `PlanDataTable.action_cursor_left()` casts `self.app` to `ErkDashApp`. In a modal context, `self.app` is still the `ErkDashApp` instance (modals don't change the app). However, left/right arrows switching views in the main app would be confusing from within the modal. Override these bindings in the modal screen to do nothing (or don't — since the modal captures focus and the PlanDataTable won't be the main app's table).

Actually, `PlanDataTable.action_cursor_left/right` delegate to `ErkDashApp.action_previous_view/next_view`. Since the modal screen has its own focus tree, and the PlanDataTable in the modal is a different widget instance than the main one, the cast will still reference the app. To prevent view switching from within the modal, add `Binding("left", "noop", show=False)` and `Binding("right", "noop", show=False)` to the modal's BINDINGS to intercept before the table gets them.

**CSS:** Keep existing modal CSS structure but adjust the content container to work well with DataTable (ensure it gets enough height, `overflow-y: auto` on the container).

### 2. Update tests

**Remove:**
- All `test_format_plan_rows_*` tests (function is deleted)

**Keep:**
- All `test_extract_plan_ids_*` tests (function still exists)
- `_make_roadmap_body` helper

**Add:**
- No new Textual pilot tests needed (those would be integration tests in `tests/tui/` scope)

## Key References

- `PlanDataTable`: `src/erk/tui/widgets/plan_table.py` — `populate()`, click messages
- `PlanFilters.default()`: `src/erk/tui/data/types.py:178`
- `PlanDataProvider.browser`: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py` — browser/clipboard properties
- App call site: `src/erk/tui/app.py:841` — `action_drill_down()` pushes the modal
- Modal pattern: `src/erk/tui/screens/unresolved_comments_screen.py` — existing modal with async loading

## Also Apply: Review Feedback Fixes

While touching these files, also apply the 3 review feedback items from PR #8156 (commit `daf838d7c`) that never landed:

1. **`objective_plans_screen.py`**: `_errors` → `_` in `parse_roadmap` unpacking; `lstrip("#")` → `node.pr[1:] if node.pr.startswith("#") else node.pr`
2. **`packages/erk-shared/src/erk_shared/gateway/github/real.py`** (~line 2289): Remove try/except that silently swallows errors in `get_issues_by_numbers_with_pr_linkages`
3. **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`** (lines 169, 466): `if self._ctx.global_config` → `if self._ctx.global_config is not None`

## Verification

1. `devrun`: `uv run ruff check src/erk/tui/screens/objective_plans_screen.py`
2. `devrun`: `uv run ty check src/erk/tui/screens/objective_plans_screen.py`
3. `devrun`: `uv run pytest tests/tui/screens/test_objective_plans_screen.py -x`
4. `devrun`: `uv run pytest tests/tui/ -x`
5. Manual: `erk dash -i` → press `3` for Objectives view → `d` to drill down → verify rich table appears in modal
