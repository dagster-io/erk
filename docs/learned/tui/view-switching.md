---
title: TUI View Switching
read_when:
  - "adding a new view mode to the TUI"
  - "understanding how view switching and caching work"
  - "debugging data not appearing in a specific view"
  - "working with PlanBodyScreen content type parameterization"
tripwires:
  - action: "adding a new ViewMode without updating VIEW_CONFIGS"
    warning: "Every ViewMode must have a corresponding ViewConfig in VIEW_CONFIGS. Missing configs cause KeyError at runtime."
  - action: "using _render() as a method name in Textual widgets"
    warning: "Textual's LSP reserves _render(). Use _refresh_display() instead (see ViewBar)."
  - action: "pushing PlanBodyScreen without explicit content_type"
    warning: "Content type must come from view_mode at push time, not derived inside the screen."
  - action: "adding labels to ViewConfig.labels expecting OR semantics from GitHub API"
    warning: "GitHub GraphQL uses AND semantics for label arrays. Multiple labels in a single ViewConfig.labels means items must have ALL listed labels. Use separate views for separate label types. See github-graphql-label-semantics.md."
  - action: "assigning both erk-plan and erk-learn labels to the same issue"
    warning: "Labels must be mutually exclusive — a plan issue has either erk-plan or erk-learn, never both. Mutually exclusive labels make tab separation work via server-side filtering with no client-side exclusion needed."
last_audited: "2026-02-17 00:00 PT"
audit_result: edited
---

# TUI View Switching

The TUI supports three views — Plans, Learn, and Objectives — with instant switching via keyboard shortcuts. This document explains the view system architecture, the label-based filtering strategy, and the caching mechanism that enables sub-millisecond view switches.

## Core Types

<!-- Source: src/erk/tui/views/types.py -->

**ViewMode** enum defines the three views: `PLANS`, `LEARN`, `OBJECTIVES`.

**ViewConfig** frozen dataclass holds per-view configuration:

| Field          | Type              | Description                         |
| -------------- | ----------------- | ----------------------------------- |
| `mode`         | `ViewMode`        | Which view this config describes    |
| `display_name` | `str`             | Human-readable name (e.g., "Plans") |
| `labels`       | `tuple[str, ...]` | GitHub labels for API queries       |
| `key_hint`     | `str`             | Keyboard shortcut (e.g., "1")       |

**VIEW_CONFIGS** tuple defines all three views:

| View       | Labels               | Key |
| ---------- | -------------------- | --- |
| Plans      | `("erk-plan",)`      | `1` |
| Learn      | `("erk-learn",)`     | `2` |
| Objectives | `("erk-objective",)` | `3` |

Plans and Learn use **mutually exclusive** type-specific labels. Each plan issue has either `erk-plan` or `erk-learn`, never both. This makes tab separation work naturally via server-side label filtering — no client-side exclusion needed.

## Label-Based Filtering

Each view uses distinct type-specific labels for API queries:

- **Plans view**: Queries `erk-plan` label
- **Learn view**: Queries `erk-learn` label
- **Objectives view**: Queries `erk-objective` label

The labels are mutually exclusive, so server-side filtering alone provides clean separation between tabs.

## Cache Strategy

<!-- Source: src/erk/tui/app.py, _data_cache -->

Data is cached by label tuple: `dict[tuple[str, ...], list[PlanRowData]]`.

Plans and Learn use different labels (`("erk-plan",)` vs `("erk-learn",)`), so switching between them requires separate API calls. Each label tuple's data is cached independently for subsequent switches back to the same view.

Cache is populated in `_load_data()` after each successful fetch and looked up in `_switch_view()` before deciding whether to fetch.

## View Switching Flow

<!-- Source: src/erk/tui/app.py, _switch_view -->

`_switch_view(mode)` orchestrates the transition:

1. Skip if already on the requested view
2. Update `_view_mode` and notify ViewBar
3. Call `PlanDataTable.reconfigure()` to reset columns for the new view
4. Check cache for the new view's labels
5. If cached: filter rows for view, populate table, update status bar
6. If not cached: launch async `_load_data()` worker

## PlanDataTable.reconfigure()

<!-- Source: src/erk/tui/widgets/plan_table.py, reconfigure -->

`reconfigure()` preserves the widget instance while rebuilding its columns:

1. Resets all column index trackers (they're view-dependent)
2. Clears all columns and rows with `clear(columns=True)`
3. Calls `_setup_columns()` to rebuild columns for the new view

Objectives view uses enriched columns: plan, title, progress (prog), next node, deps, updated, author (7 columns). Plans and Learn views show the full column set including PR, checks, comments, learn status, and worktree columns.

## ViewBar

<!-- Source: src/erk/tui/widgets/view_bar.py -->

Renders `1:Plans  2:Learn  3:Objectives` with the active view in bold white and inactive views dimmed. Uses `_refresh_display()` (not `_render()` — Textual's LSP conflicts with that name).

## Arrow Key View Cycling

Left/right arrow keys cycle through views. This is delegated from `PlanDataTable` to the app:

<!-- Source: src/erk/tui/widgets/plan_table.py, action_cursor_left, action_cursor_right -->

`PlanDataTable` overrides `action_cursor_left` and `action_cursor_right` to delegate to `ErkDashApp.action_previous_view()` and `action_next_view()` respectively.

The app uses `get_next_view_mode()` and `get_previous_view_mode()` from `src/erk/tui/views/types.py` which cycle through `VIEW_CONFIGS` with wrapping (last -> first, first -> last).

## Race Condition Prevention

When a fetch is in progress and the user switches tabs, the fetched data could be applied to the wrong view. The `fetched_mode` guard prevents this — see [Async State Snapshot](async-state-snapshot.md) for the full pattern.

In brief: `_load_data()` snapshots `self._view_mode` at fetch start, and `_update_table()` only updates the display if the current view still matches the snapshot.

## Content Type Parameterization: PlanBodyScreen

<!-- Source: src/erk/tui/screens/plan_body_screen.py -->

`PlanBodyScreen` accepts a `content_type: Literal["Plan", "Objective"]` parameter that controls both the UI display labels and which gateway method is called:

<!-- Source: src/erk/tui/screens/plan_body_screen.py, PlanBodyScreen.__init__ -->

See `PlanBodyScreen.__init__()` in `src/erk/tui/screens/plan_body_screen.py`. Accepts `provider`, `plan_id`, `plan_body`, `full_title`, and `content_type: Literal["Plan", "Objective"]` keyword arguments.

**View-mode-aware routing:** The app determines `content_type` from `_view_mode` BEFORE pushing the screen — it is not derived from state inside the screen:

- `content_type="Objective"` -> calls `provider.fetch_objective_content()`
- `content_type="Plan"` -> calls `provider.fetch_plan_content()`

**Symmetric gateway API:** `fetch_plan_content()` and `fetch_objective_content()` follow the 5-place gateway pattern (ABC, real, fake, test helper, tests) with matching extraction functions.

**Display labels:** `content_type.lower()` is used for user-facing strings (e.g., "Loading plan content..." vs "Loading objective content...").

## Related Documentation

- [Async State Snapshot](async-state-snapshot.md) — Race condition prevention for async fetches
- [TUI Data Contract](data-contract.md) — PlanRowData fields including `is_learn_plan`

See also TUI category documentation for overall architecture and layer structure.
