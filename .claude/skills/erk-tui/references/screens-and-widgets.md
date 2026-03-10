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
2. Check the Keyboard Shortcut Inventory in `commands.md` (this skill)
3. Some keys are hidden but still active

**Naming convention**: `action_<verb>_<noun>` (e.g., `action_close_plan`, `action_open_pr`)

**Arrow key priority**: Use `priority=True` on arrow key bindings in DataTable screens to override widget defaults (j/k also get this behavior).

## Status Indicators

**Two rendering functions** in `packages/erk-shared/.../plan_data_provider/lifecycle.py`:

- `compute_status_indicators()`: Standalone "sts" column display (4-char width, planned_pr view only)
- `format_lifecycle_with_status()`: Inline display — appends indicators inside Rich markup tags

**Rule**: Indicators are computed from RAW PR state fields (`is_draft`, `has_conflicts`, `review_decision`), NOT extracted from the lifecycle display string.

**Indicator logic table**:

| Emoji | Meaning | When Shown |
| --- | --- | --- |
| 🥞 | Stacked PR | Any stage when `is_stacked=True` (informational, doesn't block 🚀) |
| 🚧 | Draft PR | Active stages when `is_draft=True` |
| 👀 | Published PR | Active stages when `is_draft=False` |
| 💥 | Merge conflicts | impl/review when `has_conflicts=True` |
| ✔ | Approved | Review stage when `review_decision="APPROVED"` |
| ❌ | Changes requested | Review stage when `review_decision="CHANGES_REQUESTED"` |
| 🚀 | Ready to merge | impl stage when checks pass, no unresolved comments, no conflicts, no blocking indicators |

**Safe emoji** (tested in terminals): 🥞 🚧 👀 💥 ✔ ❌ 🚀

**Never add emoji with variation selectors (`\ufe0f`)** — forces double-wide rendering in terminals, breaking column alignment. Test any new emoji in terminal first.

## Lifecycle Display

**Stage inference** (in `compute_lifecycle_display()`): Reads `lifecycle_stage` from plan header. If absent, infers from PR state:

| `is_draft` | `pr_state` | Inferred Stage |
| --- | --- | --- |
| `True` | `"OPEN"` | `planned` |
| `False` | `"OPEN"` | `impl` |
| `False` | `"MERGED"` | `merged` |
| `False` | `"CLOSED"` | `closed` |

When resolved stage is `planned` and a workflow run exists, upgrades to `impl`.

**Abbreviation/color map** (8-char column width):

| Stage | Color | Markup |
| --- | --- | --- |
| `prompted` | magenta | `[magenta]prompted[/magenta]` |
| `planning` | magenta | `[magenta]planning[/magenta]` |
| `planned` | dim | `[dim]planned[/dim]` |
| `impl` | yellow | `[yellow]impl[/yellow]` |
| `merged` | green | `[green]merged[/green]` |
| `closed` | dim red | `[dim red]closed[/dim red]` |

**Stage detection**: Uses substring matching on `lifecycle_display` content, not color markup.

**Adding new stages**: Must update: (1) abbreviation map if > 8 chars, (2) `format_lifecycle_with_status()` stage detection, (3) `compute_lifecycle_display()` stage-to-color mapping.

## Stacked PR Indicator

- Pancake emoji (🥞) is informational — doesn't block rocket (🚀)
- **Primary**: Graphite `get_parent_branch()` (authoritative, reflects actual stack topology)
- **Fallback**: GitHub `base_ref_name` (only when Graphite returns None — branch not tracked locally)
- Graphite preferred because GitHub's `base_ref_name` can become stale after parent PR merges

## Plan Title Rendering Pipeline

5-stage pipeline: GitHub API → Middleware prefix → Filtering → Service transform → Widget render

**Critical rule**: Prefix enrichment (`[erk-learn]`) MUST happen BEFORE filtering, not after. Otherwise metadata gets lost.

**Title truncation**:

1. Truncate BEFORE prefixing
2. Add prefix
3. Wrap in `Text()` to prevent Rich markup parsing

Calculate available space: `MAX_DISPLAY - PREFIX_LEN` (e.g., 50 - 12 for "[erk-learn] " = 38 for content)

Use `len(Text.from_markup(s).plain)` for visible character count vs string length.

**Three strip functions** (don't confuse them): `_strip_plan_prefixes` (PR creation), `_strip_plan_markers` (plan creation), `strip_plan_from_filename` (filename handling).

## Modal Widget Embedding

When reusing complex widgets (like `PlanDataTable`) inside modal screens:

- `PlanDataTable` does NOT accept `id=` kwarg — use `self.query_one(PlanDataTable)` instead of `self.query_one("#my-table")`
- Always guard optional gateway fields (`plan_body`, `objective_content`) with null checks before accessing in event handlers — modals often operate on partially-loaded data
- Reference implementation: `ObjectivePlansScreen` embeds `PlanDataTable` in a modal

## Reference Implementations

| Screen | Pattern | Key Features |
| --- | --- | --- |
| `UnresolvedCommentsScreen` | Standard modal | Fetches PR review comments |
| `PlanBodyScreen` | Content display | `content_type` parameterization |
| `PlanDetailScreen` | Detail + commands | Markdown rendering, command execution |
| `ObjectiveNodesScreen` | Complex modal | Async loading, phase separators, PR enrichment, next-node highlighting |
| `LaunchScreen` | Command dispatch | Dynamic key map, dismisses on unmapped keys |

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
