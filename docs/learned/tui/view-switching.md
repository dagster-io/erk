---
title: TUI View Switching
read_when:
  - "adding a new view mode to the TUI"
  - "understanding how view switching and caching work"
  - "debugging data not appearing in a specific view"
tripwires:
  - action: "adding a new ViewMode without updating VIEW_CONFIGS"
    warning: "Every ViewMode must have a corresponding ViewConfig in VIEW_CONFIGS. Missing configs cause KeyError at runtime."
  - action: "using _render() as a method name in Textual widgets"
    warning: "Textual's LSP reserves _render(). Use _refresh_display() instead (see ViewBar)."
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# TUI View Switching

The TUI supports three views — Plans, Learn, and Objectives — with instant switching via keyboard shortcuts. This document explains the view system architecture, the two-tier filtering strategy, and the caching mechanism that enables sub-millisecond view switches.

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
| Learn      | `("erk-plan",)`      | `2` |
| Objectives | `("erk-objective",)` | `3` |

Plans and Learn share the same API label — this is intentional for the two-tier filtering strategy.

## Two-Tier Filtering

The view system uses two levels of filtering because GitHub's GraphQL API doesn't support negative label filtering:

**Tier 1 — API labels**: The `labels` tuple in ViewConfig determines which issues are fetched from GitHub. Plans and Learn both fetch `erk-plan` issues; Objectives fetches `erk-objective` issues.

**Tier 2 — Client-side `is_learn_plan`**: After fetching, `_filter_rows_for_view()` separates plans from learn plans:

- **Plans view**: Excludes rows where `is_learn_plan == True`
- **Learn view**: Includes only rows where `is_learn_plan == True`
- **Objectives view**: Returns all rows unchanged

<!-- Source: src/erk/tui/app.py:260-276 -->

This design allows Plans and Learn views to share cached API data while displaying different subsets.

## Cache Strategy

<!-- Source: src/erk/tui/app.py:129 -->

Data is cached by label tuple: `dict[tuple[str, ...], list[PlanRowData]]`.

Since Plans and Learn share the label `("erk-plan",)`, switching between them is instant — the cached data is reused and only the client-side filter changes. Switching to Objectives requires a fresh API call (different label tuple) but the data is then cached for subsequent switches.

Cache is populated in `_load_data()` after each successful fetch and looked up in `_switch_view()` before deciding whether to fetch.

## View Switching Flow

<!-- Source: src/erk/tui/app.py:340-390 -->

`_switch_view(mode)` orchestrates the transition:

1. Skip if already on the requested view
2. Update `_view_mode` and notify ViewBar
3. Call `PlanDataTable.reconfigure()` to reset columns for the new view
4. Check cache for the new view's labels
5. If cached: filter rows for view, populate table, update status bar
6. If not cached: launch async `_load_data()` worker

## PlanDataTable.reconfigure()

<!-- Source: src/erk/tui/widgets/plan_table.py:103-123 -->

`reconfigure()` preserves the widget instance while rebuilding its columns:

1. Resets all column index trackers (they're view-dependent)
2. Clears all columns and rows with `clear(columns=True)`
3. Calls `_setup_columns()` to rebuild columns for the new view

Objectives view uses simplified columns (plan, title, created, author only). Plans and Learn views show the full column set including PR, checks, comments, learn status, and worktree columns.

## ViewBar

<!-- Source: src/erk/tui/widgets/view_bar.py -->

Renders `1:Plans  2:Learn  3:Objectives` with the active view in bold white and inactive views dimmed. Uses `_refresh_display()` (not `_render()` — Textual's LSP conflicts with that name).

## Related Documentation

- [TUI Data Contract](data-contract.md) — PlanRowData fields including `is_learn_plan`
- [TUI Architecture](architecture.md) — Overall TUI layer structure
