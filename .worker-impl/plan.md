# Convert "Submit to Queue" from modal to non-blocking toast pattern

## Context

The `submit_to_queue` command in the TUI currently opens a full `PlanDetailScreen` modal with streaming output, blocking UI interaction until the user presses Esc. The `land_pr` and `close_plan` commands were recently converted to a non-blocking toast + background worker pattern (commit 873dc04bc). This change applies the same pattern to `submit_to_queue` for consistency.

## Changes

### 1. Add `_submit_to_queue_async` worker to `src/erk/tui/app.py`

Add a new `@work(thread=True)` method following the `_land_pr_async` pattern (line ~567):

```python
@work(thread=True)
def _submit_to_queue_async(self, plan_id: int, repo_root: Path) -> None:
    """Submit plan to queue in background thread with toast notifications."""
    try:
        result = subprocess.run(
            ["erk", "plan", "submit", str(plan_id), "-f"],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            self.call_from_thread(self.notify, f"Plan #{plan_id} submitted", timeout=5)
            self.call_from_thread(self.action_refresh)
        else:
            self.call_from_thread(
                self.notify,
                f"Submitting plan #{plan_id} failed",
                severity="error",
                timeout=8,
            )
    except OSError as e:
        self.call_from_thread(
            self.notify,
            f"Submitting plan #{plan_id} failed: {e}",
            severity="error",
            timeout=8,
        )
```

Key details:
- `-f` flag prevents blocking prompts in TUI context
- `stdin=subprocess.DEVNULL` prevents hanging
- Success triggers `action_refresh` to update table

### 2. Simplify `execute_palette_command` handler in `src/erk/tui/app.py` (lines 939-965)

Replace the modal creation with toast + async worker:

```python
elif command_id == "submit_to_queue":
    if row.plan_url:
        self.notify(f"Submitting plan #{row.plan_id}...")
        self._submit_to_queue_async(row.plan_id, self._provider.repo_root)
```

This removes the `RealCommandExecutor` creation, `PlanDetailScreen` push, and `call_after_refresh` streaming command.

### 3. Update detail screen handler in `src/erk/tui/screens/plan_detail_screen.py` (lines 676-685)

Replace the in-modal streaming with dismiss + delegate to app:

```python
elif command_id == "submit_to_queue":
    if row.plan_url and self._repo_root is not None:
        plan_id = row.plan_id
        repo_root = self._repo_root
        self.dismiss()
        if isinstance(self.app, ErkDashApp):
            self.app.notify(f"Submitting plan #{plan_id}...")
            self.app._submit_to_queue_async(plan_id, repo_root)
```

### 4. Update tests in `tests/tui/commands/test_execute_command.py`

Update `TestExecuteCommandSubmitToQueue` docstring to reflect the new non-blocking pattern (same as `TestExecuteCommandLandPR`). The guard condition tests remain valid as-is since they test that nothing happens without `repo_root` or `plan_url`.

### 5. Add tests in `tests/tui/test_app.py`

Add two new test classes following the `TestExecutePaletteCommandLandPR` / `TestLandPrAsync` pattern:

**`TestExecutePaletteCommandSubmitToQueue`** - verifies:
- Does nothing without `plan_url`
- Calls `_submit_to_queue_async` with correct args (plan_id, repo_root)
- Does NOT push a detail screen (non-blocking)

**`TestSubmitToQueueAsync`** - verifies:
- Success (returncode 0) triggers `action_refresh`
- Failure (returncode != 0) does NOT trigger refresh
- `OSError` is caught without crashing
- `subprocess.run` called with correct args: `["erk", "plan", "submit", "<plan_id>", "-f"]`

## Files modified

- `src/erk/tui/app.py` - New worker method, simplified handler
- `src/erk/tui/screens/plan_detail_screen.py` - Dismiss + delegate pattern
- `tests/tui/commands/test_execute_command.py` - Update docstring
- `tests/tui/test_app.py` - New test classes

## Verification

1. Run TUI tests: `uv run pytest tests/tui/ -x`
2. Run type checker on modified files
3. Manual: `erk dash -i`, select a plan with a URL, Ctrl+P > Submit - should show toast and return to table immediately