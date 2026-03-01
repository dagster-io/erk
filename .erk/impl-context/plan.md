# Make "p" Open Objective Issue Page in Objectives View

## Context

In the TUI objectives screen, the `p` keyboard shortcut currently triggers `action_open_pr()`, which tries to open `row.pr_url`. Since objective rows typically don't have PR URLs, this shows "No PR linked to this plan" — useless in the objectives context. The user expects `p` to open the objective's GitHub issue page instead.

The command palette already has separate `open_pr` (plan views) and `open_objective` (objectives view) commands, but the direct `p` key binding doesn't participate in this view-aware dispatch. This plan makes `action_open_pr()` view-aware so `p` opens the appropriate page based on the current view.

## Changes

### 1. Make `action_open_pr()` view-aware in `src/erk/tui/app.py`

**File:** `src/erk/tui/app.py`
**Method:** `action_open_pr()` (lines 1182-1194)

**Current code:**
```python
def action_open_pr(self) -> None:
    """Open selected PR in browser."""
    row = self._get_selected_row()
    if row is None:
        return

    if row.pr_url:
        self._provider.browser.launch(row.pr_url)
        if self._status_bar is not None:
            self._status_bar.set_message(f"Opened PR #{row.pr_number}")
    else:
        if self._status_bar is not None:
            self._status_bar.set_message("No PR linked to this plan")
```

**New code:**
```python
def action_open_pr(self) -> None:
    """Open selected PR in browser, or objective issue in Objectives view."""
    row = self._get_selected_row()
    if row is None:
        return

    if self._view_mode == ViewMode.OBJECTIVES:
        if row.plan_url:
            self._provider.browser.launch(row.plan_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened objective #{row.plan_id}")
        else:
            if self._status_bar is not None:
                self._status_bar.set_message("No URL for this objective")
    else:
        if row.pr_url:
            self._provider.browser.launch(row.pr_url)
            if self._status_bar is not None:
                self._status_bar.set_message(f"Opened PR #{row.pr_number}")
        else:
            if self._status_bar is not None:
                self._status_bar.set_message("No PR linked to this plan")
```

**Key details:**
- Check `self._view_mode == ViewMode.OBJECTIVES` first (LBYL pattern)
- In objectives view: use `row.plan_url` (the objective issue URL) and show "Opened objective #N"
- In plan/learn views: preserve existing behavior using `row.pr_url`
- `ViewMode` is already imported in app.py (line 38)
- This mirrors exactly how `action_view_plan_body()` (line 1063-1078) dispatches based on `self._view_mode`

### 2. Update `open_objective` command shortcut in `src/erk/tui/commands/registry.py`

**File:** `src/erk/tui/commands/registry.py`
**Lines:** 313-320 (the `open_objective` CommandDefinition)

Change the shortcut from `"i"` to `"p"`:

```python
# Before:
        CommandDefinition(
            id="open_objective",
            name="Objective",
            description="objective",
            category=CommandCategory.OPEN,
            shortcut="i",
            is_available=lambda ctx: _is_objectives_view(ctx) and ctx.row.plan_url is not None,
            get_display_name=_display_open_objective,
        ),

# After:
        CommandDefinition(
            id="open_objective",
            name="Objective",
            description="objective",
            category=CommandCategory.OPEN,
            shortcut="p",
            is_available=lambda ctx: _is_objectives_view(ctx) and ctx.row.plan_url is not None,
            get_display_name=_display_open_objective,
        ),
```

**Why this is safe:** `open_pr` uses shortcut `"p"` with `_is_plan_view(ctx)`, and `open_objective` uses `_is_objectives_view(ctx)`. These predicates are mutually exclusive (see `view-aware-commands.md` shortcut reuse table), so no conflict occurs. This makes the command palette shortcut consistent with the keyboard binding behavior.

### 3. Update `test_registry.py` for new shortcut

**File:** `tests/tui/commands/test_registry.py`

Update any test that asserts the `open_objective` shortcut is `"i"` to expect `"p"` instead. Based on the current tests, there are no explicit shortcut-value assertions for `open_objective`, but the implementer should verify and update if found.

## Files NOT Changing

- `src/erk/tui/widgets/plan_table.py` — No key handling changes needed; `p` binding stays at app level
- `src/erk/tui/views/types.py` — No view config changes needed
- `src/erk/tui/commands/provider.py` — Provider logic unchanged
- `src/erk/tui/data/types.py` — PlanRowData already has `plan_url` field
- No new tests needed for the `action_open_pr` change since it's a direct keyboard binding without existing unit tests. The command registry shortcut change in step 2 is covered by the existing `test_available_objectives_view_commands` and `test_display_name_open_objective` tests (which don't assert shortcut values).

## Verification

1. Run `pytest tests/tui/commands/test_registry.py` — all registry tests should pass
2. Run `ty check src/erk/tui/app.py` — type check should pass
3. Run `ruff check src/erk/tui/app.py` — lint should pass
4. Manual verification: run `erk dash`, switch to Objectives view (key `3`), select an objective, press `p` → should open the objective issue URL in browser
5. Manual verification: switch to Plans view (key `1`), select a plan with a PR, press `p` → should still open the PR URL in browser