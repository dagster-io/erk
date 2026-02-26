# Add keyboard shortcut (n) to open GitHub Action run URL

## Context

The TUI main list view (`ErkDashApp`) has keyboard shortcuts for common actions - `p` opens the PR in a browser, `i` shows the implement command, `r` triggers a refresh, etc. However, there is no direct keyboard shortcut on the main list to open the GitHub Actions workflow run URL.

The `open_run` command already exists in the command palette registry (`registry.py`) with shortcut `r`, and the plan detail screen already binds `r` to `action_open_run`. But on the main list, `r` is bound to `action_refresh`. The user wants a dedicated `n` key binding on the main list to quickly open the GitHub Actions run page for the selected plan.

The `n` key is currently unused in the main app BINDINGS.

## Changes

### 1. Add `Binding("n", "open_run", "Run")` to `ErkDashApp.BINDINGS`

**File:** `src/erk/tui/app.py`

In the `BINDINGS` list (around line 98-122), add a new binding after the existing `Binding("p", "open_pr", "Open PR")` line:

```python
Binding("n", "open_run", "Run"),
```

Place it after the `Binding("p", "open_pr", "Open PR")` line (line 108) to keep browser-open shortcuts grouped together.

### 2. Add `action_open_run` method to `ErkDashApp`

**File:** `src/erk/tui/app.py`

Add a new action method after `action_open_pr` (around line 1095-1107). Follow the exact same pattern as `action_open_pr`:

```python
def action_open_run(self) -> None:
    """Open selected workflow run in browser."""
    row = self._get_selected_row()
    if row is None:
        return

    if row.run_url:
        self._provider.browser.launch(row.run_url)
        if self._status_bar is not None:
            run_id = row.run_url.rsplit("/", 1)[-1]
            self._status_bar.set_message(f"Opened run {run_id}")
    else:
        if self._status_bar is not None:
            self._status_bar.set_message("No workflow run linked to this plan")
```

Note: Extract the run ID from the URL to avoid any Rich markup in the status bar, matching the pattern used in `on_run_id_clicked` at line 1408.

### 3. Add test for the new keyboard shortcut action

**File:** `tests/tui/test_app.py`

Add a test in the `TestErkDashAppCommandPalette` class (or create a new test class nearby) following the pattern of `test_execute_palette_command_open_pr`:

```python
@pytest.mark.asyncio
async def test_action_open_run_opens_run_url(self) -> None:
    """Pressing n opens workflow run in browser."""
    provider = FakePlanDataProvider(
        plans=[
            make_plan_row(
                123, "Test Plan", run_url="https://github.com/test/repo/actions/runs/789"
            ),
        ]
    )
    filters = PlanFilters.default()
    app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()

        # Execute open_run action (same as pressing n)
        app.action_open_run()

        assert provider.browser.last_launched == "https://github.com/test/repo/actions/runs/789"
```

Also add a test for the no-run-url case:

```python
@pytest.mark.asyncio
async def test_action_open_run_no_run_url(self) -> None:
    """Pressing n with no run URL shows status message."""
    provider = FakePlanDataProvider(
        plans=[make_plan_row(123, "Test Plan")]
    )
    filters = PlanFilters.default()
    app = ErkDashApp(provider=provider, filters=filters, refresh_interval=0)

    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()

        app.action_open_run()

        # Should not have launched any URL
        assert provider.browser.last_launched is None
```

## Implementation Details

- The `_get_selected_row()` helper already handles the case where no row is selected (returns `None`)
- The `_provider.browser.launch()` method is the standard way to open URLs in the TUI (delegates to `webbrowser.open` in production, captured by `FakeBrowser` in tests)
- The `run_url` field on `PlanRowData` is `str | None` - it's `None` when no GitHub Actions workflow has been triggered for the plan
- The run ID extraction (`row.run_url.rsplit("/", 1)[-1]`) avoids displaying the full URL in the status bar and prevents Rich markup issues, matching the existing pattern in `on_run_id_clicked`

## Files NOT Changing

- `src/erk/tui/commands/registry.py` - The `open_run` command already exists with shortcut `r` for the command palette context. No changes needed.
- `src/erk/tui/screens/plan_detail_screen.py` - Already has `Binding("r", "open_run", "Run")` and `action_open_run`. No changes needed.
- `src/erk/tui/data/types.py` - `run_url` field already exists on `PlanRowData`. No changes needed.
- `tests/tui/commands/test_registry.py` - Registry tests already cover `open_run` availability. No changes needed.
- `tests/tui/commands/test_execute_command.py` - Detail screen `open_run` tests already exist. No changes needed.

## Verification

1. Run `pytest tests/tui/test_app.py -x` to verify the new tests pass
2. Run `pytest tests/tui/commands/ -x` to verify existing command tests still pass
3. Run `ruff check src/erk/tui/app.py` to verify no lint issues
4. Run `ty check src/erk/tui/app.py` to verify no type errors