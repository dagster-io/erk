# Plan: Wire Incremental Dispatch into TUI (Objective #8470, Phase 2)

Part of Objective #8470, Nodes 2.1–2.4

## Context

Incremental dispatch (`erk exec incremental-dispatch`) lets users dispatch a local plan against an existing PR for remote AI implementation. It currently works only via CLI. This plan adds TUI support: a user selects a PR in ErkDash, presses `l` then `i`, types/pastes a plan in a modal, and submits it for remote implementation.

## Changes

### 1. Create `PlanInputScreen` modal (Node 2.1)

**New file:** `src/erk/tui/screens/plan_input_screen.py`

Clone the `OneShotPromptScreen` pattern (`src/erk/tui/screens/one_shot_prompt_screen.py`):

- Class `PlanInputScreen(ModalScreen[str | None])`
- `TextArea` for multi-line plan markdown input
- `Binding("ctrl+s", "submit_plan", "Submit", show=False)` — use Ctrl+S (not Ctrl+Enter like one-shot) since plans are longer-form content
- `Binding("escape", "dismiss_cancel", "Close")`
- Title: "Incremental Dispatch Plan"
- Footer hint: "Ctrl+S to dispatch · Esc to cancel"
- CSS: same 90%/80% dimensions as one-shot dialog
- Constructor takes `pr_number: int` to display in title: "Dispatch plan to PR #456"
- Returns `str | None` — stripped plan markdown or None

### 2. Add `incremental_dispatch` command to registry (Node 2.2)

**File:** `src/erk/tui/commands/registry.py`

Add `CommandDefinition`:
```python
CommandDefinition(
    id="incremental_dispatch",
    name="Incremental Dispatch",
    description="incremental dispatch",
    category=CommandCategory.ACTION,
    shortcut=None,
    launch_key="i",  # available (used launch keys: a,c,d,k,l,m,r,s,w)
    is_available=lambda ctx: (
        _is_plan_view(ctx)
        and ctx.row.pr_number is not None
        and ctx.row.pr_state == "OPEN"
    ),
    get_display_name=_display_incremental_dispatch,
)
```

Add display name helper:
```python
def _display_incremental_dispatch(ctx: CommandContext) -> str:
    return f"erk exec incremental-dispatch --pr {ctx.row.pr_number}"
```

### 3. Wire async worker (Node 2.3)

**File:** `src/erk/tui/operations/workers.py`

Add `_incremental_dispatch_async` method following `_one_shot_dispatch_async` pattern:

```python
@work(thread=True)
def _incremental_dispatch_async(
    self: ErkDashApp, op_id: str, pr_number: int, plan_content: str
) -> None:
```

Key detail: `erk exec incremental-dispatch` needs `--plan-file <path>` (file path, not stdin). The worker must:
1. Write `plan_content` to a `tempfile.NamedTemporaryFile(suffix=".md", delete=False)`
2. Call `_run_streaming_operation` with `["erk", "exec", "incremental-dispatch", "--plan-file", temp_path, "--pr", str(pr_number), "--format", "json"]`
3. Clean up the temp file in a `finally` block
4. Parse JSON success/failure, notify user, refresh on success

**File:** `src/erk/tui/actions/palette.py`

Add handler in `execute_palette_command`:
```python
elif command_id == "incremental_dispatch":
    if row.pr_number:
        self.push_screen(
            PlanInputScreen(pr_number=row.pr_number),
            self._on_incremental_dispatch_result,
        )
```

Add result callback (needs `pr_number` from closure — store as instance var or use `functools.partial`):
```python
def _on_incremental_dispatch_result(self: ErkDashApp, plan_markdown: str | None) -> None:
```

Note: The callback doesn't have access to `row` since the modal dismissed. Two approaches:
- **Option A:** Store `self._pending_dispatch_pr` before pushing screen, read in callback
- **Option B:** Use `functools.partial` to bind `pr_number` into the callback

Use Option A — matches existing patterns (simpler, no import needed).

### 4. Add handler in plan detail screen (Node 2.4)

**File:** `src/erk/tui/screens/plan_detail_screen.py`

Add `incremental_dispatch` case in `execute_command` (if this screen has command execution). Follow the pattern where the modal dismisses first, then delegates to app:

```python
elif command_id == "incremental_dispatch":
    if self._row.pr_number is None:
        return
    self.dismiss()
    if isinstance(self.app, ErkDashApp):
        self.app.execute_palette_command("incremental_dispatch")
```

### 5. Cleanup: Remove dead `modify_existing` input

**File:** `src/erk/cli/commands/launch_cmd.py:334`

Remove `"modify_existing": "true"` from the `inputs` dict in `_dispatch_one_shot()`. This is silently ignored by `one-shot.yml`.

## Files Modified

| File | Change |
|------|--------|
| `src/erk/tui/screens/plan_input_screen.py` | **New** — PlanInputScreen modal |
| `src/erk/tui/commands/registry.py` | Add `incremental_dispatch` CommandDefinition |
| `src/erk/tui/operations/workers.py` | Add `_incremental_dispatch_async` worker |
| `src/erk/tui/actions/palette.py` | Add handler + callback in PaletteActionsMixin |
| `src/erk/tui/screens/plan_detail_screen.py` | Add `incremental_dispatch` case |
| `src/erk/cli/commands/launch_cmd.py` | Remove dead `modify_existing` line |

## Patterns to Reuse

- `OneShotPromptScreen` (`src/erk/tui/screens/one_shot_prompt_screen.py`) — modal template
- `_one_shot_dispatch_async` (`src/erk/tui/operations/workers.py:400`) — async worker template
- `_on_one_shot_prompt_result` (`src/erk/tui/actions/palette.py:259`) — callback template
- `_run_streaming_operation` — subprocess execution with progress
- `last_output_line` from `operations/logic.py` — error extraction

## Tests

### Unit tests for PlanInputScreen
**New file:** `tests/tui/screens/test_plan_input_screen.py`
- Submit with Ctrl+S returns text
- Cancel with Escape returns None
- Empty text returns None

### Unit test for registry
**Existing file:** `tests/tui/commands/test_registry.py`
- Verify `incremental_dispatch` command is registered
- Verify availability predicate (needs pr_number + OPEN state)

### Integration test for dispatch flow
**New file:** `tests/tui/app/test_incremental_dispatch.py`
- Mock `_run_streaming_operation` to verify correct command args
- Verify temp file is created and cleaned up

## Verification

1. Run `make fast-ci` — all tests pass
2. Manual: `erk dash -i`, select an OPEN PR, press `l`, verify `i` appears for incremental dispatch
3. Manual: Press `i`, verify PlanInputScreen modal appears with PR number in title
4. Manual: Type plan text, press Ctrl+S, verify dispatch starts (status bar shows progress)
5. Manual: Verify Esc cancels without dispatching
