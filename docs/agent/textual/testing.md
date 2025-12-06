---
title: Textual TUI Testing Patterns
read_when:
  - "testing Textual TUI components"
  - "writing tests for ModalScreen"
  - "testing keyboard bindings"
  - "using Pilot API for async tests"
---

# Textual TUI Testing Patterns

## Overview

This project uses Textual for TUI applications. Testing Textual apps requires async tests with the Pilot API.

## Basic Test Structure

```python
import pytest
from erk.tui.app import ErkDashApp, PlanDetailScreen

@pytest.mark.asyncio
async def test_tui_behavior() -> None:
    """Test TUI interaction."""
    provider = FakePlanDataProvider([make_plan_row(123, "Test")])
    filters = PlanFilters.default()
    app = ErkDashApp(provider, filters, refresh_interval=0)

    async with app.run_test() as pilot:
        # Wait for initial load
        await pilot.pause()
        await pilot.pause()  # Often need multiple pauses

        # Simulate key press
        await pilot.press("space")
        await pilot.pause()

        # Assert on screen stack
        assert isinstance(app.screen_stack[-1], PlanDetailScreen)
```

## Key Patterns

### Waiting for Async Operations

```python
await pilot.pause()  # Wait one frame
await pilot.pause()  # Often need 2+ for screen transitions
```

### Testing Key Bindings

```python
await pilot.press("space")      # Single key
await pilot.press("S")          # Shift+S (capital letter)
await pilot.press("escape")     # Named keys
await pilot.press("1", "2", "3") # Multiple keys in sequence
```

### Screen Stack Assertions

```python
# Check modal is showing
assert len(app.screen_stack) > 1
assert isinstance(app.screen_stack[-1], MyModalScreen)

# Check modal dismissed
assert not isinstance(app.screen_stack[-1], MyModalScreen)
```

### Testing ModalScreen with Callbacks

```python
result_holder: list[bool] = []

def capture_result(result: bool | None) -> None:
    if result is not None:
        result_holder.append(result)

dialog = ConfirmationDialog("Confirm?", "command")
app.push_screen(dialog, callback=capture_result)
await pilot.pause()

await pilot.press("y")
await pilot.pause()

assert result_holder[0] is True
```

### Testing Clipboard Operations

```python
clipboard = FakeClipboard()
provider = FakePlanDataProvider([...], clipboard=clipboard)
# ... run test ...
assert clipboard.last_copied == "expected command"
```

## Common Pitfalls

- **Not enough pauses**: Screen transitions need multiple `await pilot.pause()` calls
- **refresh_interval=0**: Always set to 0 in tests to disable auto-refresh timers
- **Callback types**: ModalScreen callbacks receive `T | None`, not just `T`

## Example Tests

See `tests/tui/test_app.py` for comprehensive examples:

- `TestConfirmationDialog` - Testing modal dialogs with y/n/escape
- `TestPlanDetailScreenCopyActions` - Testing keyboard shortcuts that copy to clipboard
- `TestPlanDetailScreenExecuteActions` - Testing actions that show confirmation dialogs
- `TestFilterMode` - Testing filter input interactions
