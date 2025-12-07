---
title: Textual Async Best Practices
read_when:
  - "overriding Screen actions"
  - "working with async/await in Textual"
  - "testing async TUI code"
---

# Textual Async Best Practices

Guide for working with async/await in Textual applications.

## When to Make Actions Async

Actions (methods prefixed with `action_`) can be either sync or async depending on what they do:

**Sync Actions** - For immediate, non-blocking operations:

```python
def action_toggle_filter(self) -> None:
    """Toggle filter visibility."""
    self._filter_visible = not self._filter_visible
    self.query_one("#filter").visible = self._filter_visible
```

**Async Actions** - When you need to:

- Wait for I/O operations
- Call other async methods
- Use Textual's async APIs (`push_screen`, etc.)

```python
async def action_show_detail(self) -> None:
    """Open detail modal (async for screen push)."""
    row_data = self._get_selected_row()
    await self.push_screen(PlanDetailScreen(row_data))
```

## Overriding Screen Actions

When overriding built-in Screen actions, match the async signature:

**WRONG** ❌

```python
class MyScreen(Screen):
    def action_dismiss(self) -> None:
        # BAD: Base class is async, override must be too
        if self._should_block_dismiss():
            return
        super().action_dismiss()  # Type error!
```

**CORRECT** ✅

```python
class MyScreen(Screen):
    async def action_dismiss(self) -> None:
        """Override must be async to match base class."""
        if self._should_block_dismiss():
            return

        await super().action_dismiss()
```

## Common Async Screen Methods

These Screen methods are async and must be awaited:

| Method                    | Purpose                                  | Returns             |
| ------------------------- | ---------------------------------------- | ------------------- |
| `action_dismiss()`        | Close current screen                     | `None`              |
| `push_screen()`           | Show new screen as modal                 | `AwaitScreenResult` |
| `pop_screen()`            | Close current screen, return to previous | `Screen`            |
| `_flush_next_callbacks()` | Process pending callbacks                | `None`              |

**Example: Custom dismiss with cleanup:**

```python
async def action_dismiss(self) -> None:
    """Dismiss with cleanup."""
    await self._save_state()  # Custom async cleanup
    await self._flush_next_callbacks()  # Process any pending updates
    await super().action_dismiss()
```

## Testing Async Screens

Use `run_test()` context manager with `await pilot.pause()`:

```python
@pytest.mark.asyncio
async def test_async_action():
    app = MyApp()

    async with app.run_test() as pilot:
        # Wait for initial render
        await pilot.pause()

        # Trigger async action
        await pilot.press("enter")

        # Wait for async operation to complete
        await pilot.pause()

        # Assert results
        screen = app.screen_stack[-1]
        assert isinstance(screen, DetailScreen)
```

## Common Pitfalls

### 1. Forgetting to await async calls

```python
# BAD
self.push_screen(MyScreen())  # Returns awaitable, not executed!

# GOOD
await self.push_screen(MyScreen())
```

### 2. Mixing sync/async in action overrides

```python
# BAD: Base is async, override is sync
def action_submit(self) -> None:  # Type error
    ...

# GOOD: Match base signature
async def action_submit(self) -> None:
    ...
```

### 3. Not using pilot.pause() in tests

```python
# BAD: Test may pass but is flaky
async with app.run_test() as pilot:
    await pilot.press("enter")
    assert app.screen_stack[-1]  # May fail - action not done yet

# GOOD: Wait for UI to settle
async with app.run_test() as pilot:
    await pilot.press("enter")
    await pilot.pause()  # Let async action complete
    assert app.screen_stack[-1]
```

## Related Documentation

- [TUI Streaming Patterns](streaming-output.md)
- External: [Textual async guide](https://textual.textualize.io/guide/async/)
