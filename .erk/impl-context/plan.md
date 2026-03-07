# Audit: Make TUI help screen view-mode-aware

## Context

The `erk dash` TUI has three views (Plans, Learn, Objectives) but the help screen (`?`) shows a single flat list of shortcuts. Many shortcuts are plan-specific and don't apply in Objectives view (e.g., `c` for comments, `h` for checks, `n` for CI run, `i` for implement, `t` for stack filter). Conversely, `b` (view nodes) only works in Objectives view. The help screen should reflect what's actually available in the current view.

Additionally, `n` (open CI run) and `←/→` (switch views) are missing from help entirely.

## Findings

### Binding applicability by view mode

**Universal (all views):** `q/Esc`, `r`, `?`, `j/k`, `↑/↓`, `Home/End`, `Enter/Space`, `1/2/3`, `←/→`, `/`, `a`, `s`, `Ctrl+P`, `v`, `l`, `x`, `o` (objective filter)

**Plans/Learn only** (meaningless in Objectives — objectives don't have PRs, runs, branches):
- `p` — Open PR in browser
- `n` — Open CI run in browser
- `i` — Show implement command
- `c` — View unresolved comments
- `h` — View failing checks
- `t` — Filter to Graphite stack

**Objectives only** (no-op outside Objectives view):
- `b` — View objective nodes
- `p` — Open objective in browser (same key, different meaning)

### Missing from help entirely
- `n` — Open CI run (`show=True` in BINDINGS but absent from help)
- `←/→` — Switch views

## Plan

### 1. Make `HelpScreen` accept `view_mode` parameter

**File:** `src/erk/tui/screens/help_screen.py`

- Add `view_mode: ViewMode` parameter to `__init__`
- Store as `self._view_mode`
- In `compose()`, conditionally render the **Actions** section based on view mode:

**Plans/Learn Actions:**
```
Enter   View plan details
Ctrl+P  Commands (opens detail modal)
v       View plan text
p       Open PR in browser
n       Open CI run in browser      ← NEW
i       Show implement command
c       View unresolved comments
h       View failing checks
l       Launch actions menu
x       Dispatch one-shot prompt
```

**Objectives Actions:**
```
Enter   View objective details
Ctrl+P  Commands (opens detail modal)
v       View objective text
p       Open objective in browser
b       View objective nodes
l       Launch actions menu
x       Dispatch one-shot prompt
```

- Conditionally render the **Filter & Sort** section:
  - Plans/Learn: show `t` (stack filter) and `o` (objective filter)
  - Objectives: hide `t` and `o` (neither applies)

- Add `←/→   Switch views` to **Views** section (both modes)

### 2. Pass `view_mode` when pushing `HelpScreen`

**File:** `src/erk/tui/actions/navigation.py` (line 77)

Change:
```python
self.push_screen(HelpScreen())
```
To:
```python
self.push_screen(HelpScreen(view_mode=self._view_mode))
```

## Files to modify

1. `src/erk/tui/screens/help_screen.py` — Accept `view_mode`, conditionally render sections
2. `src/erk/tui/actions/navigation.py` — Pass `self._view_mode` to `HelpScreen()`

## Verification

1. Run `erk dash -i`, switch to Plans view, press `?` — confirm plan-specific shortcuts shown (including `n`)
2. Switch to Objectives view (`3`), press `?` — confirm objectives-specific shortcuts shown (`b`, no `c`/`h`/`n`/`i`/`t`)
3. Confirm `←/→` appears in Views section in both modes
4. Run existing TUI tests: `pytest tests/tui/ -x`
