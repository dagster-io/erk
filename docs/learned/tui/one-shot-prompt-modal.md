---
title: One-Shot Prompt Modal
read_when:
  - "adding a new modal or input screen to the TUI"
  - "working with the one-shot dispatch workflow in erk dash"
  - "adding global keybindings that trigger modals"
---

# One-Shot Prompt Modal

The `x` keybinding in erk dash opens a modal for dispatching one-shot prompts. This is a global action — no row selection is required.

## Screen Implementation

<!-- Source: src/erk/tui/screens/one_shot_prompt_screen.py -->

`OneShotPromptScreen(ModalScreen[str | None])` at `src/erk/tui/screens/one_shot_prompt_screen.py`:

- **Widget**: `TextArea` (not `Input`) for multi-line prompt support, 32-line height
- **Submit**: Ctrl+Enter dispatches the prompt (returns stripped text)
- **Cancel**: Escape dismisses (returns `None`)
- **No `q` binding**: The screen deliberately omits a `q` keybinding since users need to type `q` in prompts

### Design Decision: TextArea vs Input

`TextArea` was chosen over `Input` to allow multi-line prompts. One-shot prompts often contain detailed instructions spanning multiple lines. The 32-line height provides ample space without overwhelming the screen.

### Design Decision: Ctrl+Enter vs Enter

Ctrl+Enter (not Enter) submits because Enter inserts newlines in the `TextArea`. This avoids interfering with multi-line editing.

## App Integration

<!-- Source: src/erk/tui/actions/palette.py, action_one_shot_prompt -->

### Global Action

The `x` keybinding pushes `OneShotPromptScreen` with a result callback.

### Result Handling

The callback handles the modal result:

1. Returns early if `prompt_text` is `None` (user cancelled)
2. Creates operation ID using `time.monotonic_ns()` for reliable uniqueness
3. Starts a visible operation via the operations pattern
4. Dispatches asynchronously in a background thread

### Async Dispatch

Runs in a background thread via `@work(thread=True)`:

- **Command**: `["erk", "one-shot", prompt_text]`
- **Success**: Shows toast "One-shot dispatched" and refreshes the dashboard
- **Failure**: Shows error toast with the last output line

### Design Decision: Op ID

Uses `time.monotonic_ns()` instead of `id()` for the operation ID. Monotonic nanoseconds provide reliable uniqueness across the process lifetime, while `id()` can recycle IDs from garbage-collected objects.

## Related Documentation

- [TUI Operations Pattern](operations-pattern.md) — How `_start_operation` / `_finish_operation` work
