# Fix: Modal dismiss keys (Esc/q/Space) broken

## Context

Commit `0d105f359` ("Fix modal keystroke leakage to underlying view") added `on_key()` handlers to three modal screens to prevent keystrokes from leaking through to the underlying view. However, the dismiss logic is **inverted** — the handlers dismiss on every key *except* the dismiss keys (Esc, q, Space), making those keys non-functional.

The bug: `on_key()` calls `event.prevent_default()` + `event.stop()`, which prevents Textual BINDINGS from firing. The handler then checks `if event.key not in ("escape", "q", "space")` before calling `dismiss()` — so the dismiss keys are consumed silently and never trigger dismissal.

## Changes

### 1. `src/erk/tui/screens/plan_body_screen.py` (line 193)

Change `not in` to `in`:

```python
# Before:
if event.key not in ("escape", "q", "space"):
    self.dismiss()

# After:
if event.key in ("escape", "q", "space"):
    self.dismiss()
```

### 2. `src/erk/tui/screens/help_screen.py` (line 107)

Change `not in` to `in`:

```python
# Before:
if event.key not in ("escape", "q", "question_mark"):
    self.dismiss()

# After:
if event.key in ("escape", "q", "question_mark"):
    self.dismiss()
```

### 3. `src/erk/tui/screens/launch_screen.py` (lines 126-129)

Simplify — dismiss with None for any non-command key (including Esc/q):

```python
# Before:
if event.key in self._key_to_command_id:
    self.dismiss(self._key_to_command_id[event.key])
elif event.key not in ("escape", "q"):
    self.dismiss(None)

# After:
if event.key in self._key_to_command_id:
    self.dismiss(self._key_to_command_id[event.key])
else:
    self.dismiss(None)
```

## Verification

1. Run TUI tests: `pytest tests/tui/`
2. Manual: `erk dash -i`, open a plan detail view, confirm Esc/q/Space close it
3. Manual: Confirm random keys do NOT leak through to the underlying view (the original bug the commit fixed)
