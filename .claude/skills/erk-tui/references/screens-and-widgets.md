---
name: erk-tui-screens-and-widgets
description: Modal screens, tables, status bar, keyboard shortcuts, status indicators
---

# TUI Screens and Widgets

**Read this when**: Building modal screens, adding keyboard shortcuts, working with status indicators, or implementing plan detail views.

## Modal Screen: 7-Element Checklist

Every modal screen requires these seven elements:

1. **`ModalScreen` subclass** with typed result
2. **CSS** for overlay (without it, clicking outside does nothing)
3. **`BINDINGS`** for dismiss and actions
4. **`@work(thread=True)`** for data fetching
5. **`call_from_thread()` bridge** for UI updates from worker
6. **Error boundary** (try/except in worker, report via `call_from_thread`)
7. **Loading placeholder** shown until data arrives

## Modal Event Handling

**Critical order**: `event.prevent_default()` + `event.stop()` BEFORE any dismiss logic. Without this, keystrokes leak to the underlying view.

**Dismiss pattern**: Use positive key check, not inverted:

```python
# WRONG — dismisses on VALID keys (inverted logic)
if event.key not in ("escape", "q"):
    self.dismiss()

# CORRECT — check for positive dismiss trigger
if event.key in ("escape", "q"):
    self.dismiss()
```

## Dismiss-Then-Delegate Pattern

When a modal command needs to show a toast or run background operations:

1. Modal calls `self.dismiss()` first
2. App shows toast at app level
3. App delegates to `@work(thread=True)` method

**Why**: Modal blocks the correct z-layer, so toasts must render at app level after dismissal.

## Keyboard Shortcuts

The `launch_key` field on `CommandDefinition` is the single source of truth. Only ACTION category commands have launch keys. OPEN and COPY commands have `launch_key=None`.

**Before adding new shortcuts**:

1. Check `ErkDashApp.BINDINGS` in `app.py` for conflicts
2. Check `keyboard-shortcuts.md` in docs/learned/tui/
3. Some keys are hidden but still active

**Naming convention**: `action_<verb>_<noun>` (e.g., `action_close_plan`, `action_open_pr`)

**Arrow key priority**: Use `priority=True` on arrow key bindings in DataTable screens to override widget defaults (j/k also get this behavior).

## Status Indicators

**Two rendering functions**:

- `compute_status_indicators()`: Standalone "sts" column display
- `format_lifecycle_with_status()`: Inline display with lifecycle

**Rule**: Indicators are computed from RAW PR state fields (`is_draft`, `has_conflicts`, `review_decision`), NOT extracted from the lifecycle display string.

**Safe emoji** (tested in terminals): 🥞 🚧 👀 💥 ✔ ❌ 🚀

**Never add emoji with variation selectors (`\ufe0f`)** — forces double-wide rendering in terminals, breaking column alignment. Test any new emoji in terminal first.

## Lifecycle Display

Stages are 8 chars max: `planned`, `impl`, `merged`, `closed`, `prompted`, `planning`.

**Stage detection**: Uses substring matching on `lifecycle_display` content, not color markup.

**Adding new stages**: Must update:

1. Abbreviation map (if stage > 8 chars)
2. `format_lifecycle_with_status()` stage detection
3. `compute_lifecycle_display()` stage-to-color mapping

## Stacked PR Indicator

- Pancake emoji (🥞) is informational — doesn't block rocket (🚀)
- Graphite `get_parent_branch()` is authoritative for stacked detection
- Falls back to GitHub `base_ref_name`

## Plan Title Rendering Pipeline

5-stage pipeline: GitHub API → Middleware prefix → Filtering → Service transform → Widget render

**Critical rule**: Prefix enrichment (`[erk-learn]`) MUST happen BEFORE filtering, not after. Otherwise metadata gets lost.

**Title truncation**:

1. Truncate BEFORE prefixing
2. Add prefix
3. Wrap in `Text()` to prevent Rich markup parsing

Calculate available space: `MAX_DISPLAY - PREFIX_LEN` (e.g., 50 - 12 for "[erk-learn] " = 38 for content)

Use `len(Text.from_markup(s).plain)` for visible character count vs string length.

## One-Shot Prompt Modal

- Use `TextArea` (not `Input`) for multi-line prompts, 32-line height
- Ctrl+Enter to submit (Enter inserts newlines)
- Use `time.monotonic_ns()` for operation IDs (reliable uniqueness vs `id()` recycling)
- Omit `q` from dismiss bindings — users need to type `q` in prompts

## Help Screen

`HelpScreen` accepts `view_mode: ViewMode` parameter and branches rendering:

- **Objectives view**: Shows objective-specific actions
- **Plans view**: Shows plan-specific actions

## Source Documents

Distilled from: `tui/keyboard-shortcuts`, `tui/status-indicators`, `tui/lifecycle-display`, `tui/stacked-pr-indicator`, `tui/one-shot-prompt-modal`, `tui/plan-title-rendering-pipeline`, `tui/title-truncation-edge-cases`
