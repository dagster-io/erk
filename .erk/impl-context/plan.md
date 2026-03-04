# Fix: StatusBar MarkupError crash on subprocess error messages

## Context

`erk dash` crashes with `MarkupError` when a background operation's progress text contains Rich markup characters (`[`, `]`). This happens because `StatusBar` extends Textual's `Static` widget, which interprets content as Rich markup by default. When a `subprocess.CalledProcessError` message like `Command '['gh', 'api', ...]'` is displayed, Rich fails to parse the brackets as markup.

## Fix

**File:** `src/erk/tui/widgets/status_bar.py:42`

Pass `markup=False` to `super().__init__()` in `StatusBar.__init__`. No display strings in the status bar use Rich markup, so this is safe.

```python
# Before
super().__init__()

# After
super().__init__(markup=False)
```

Single-line change. No other files affected.

## Verification

1. Run `erk dash` — confirm it starts without errors
2. Trigger a background operation that fails (e.g., dispatch address for a PR) — confirm no `MarkupError` crash
