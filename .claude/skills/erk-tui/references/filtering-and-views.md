---
name: erk-tui-filtering-and-views
description: Filter pipeline, toggle pattern, escape chain, view switching
---

# TUI Filtering and Views

**Read this when**: Adding filters, modifying view switching, or working with the escape chain.

## Filter Pipeline

Filters are applied in order: **Objective → Stack → Text → Sort**.

This order is intentional:

- **Objective** is broadest (cross-stack)
- **Stack** is mid-level
- **Text** is narrowest (final search refinement)
- **Sort** operates on the remaining rows

**Never change this order** — it produces unexpected results when reordered.

## Server-Side vs Client-Side Filters

| Type        | Examples                     | Cache behavior                                  |
| ----------- | ---------------------------- | ----------------------------------------------- |
| Server-side | `author`, `labels`           | Clears `_data_cache` and re-fetches from GitHub |
| Client-side | `text`, `stack`, `objective` | Re-filters cached rows without re-fetching      |

When toggling a server-side filter, the cache must be cleared because the GitHub query changes. Client-side filters only re-process existing cached data.

## Filter Toggle Pattern

Each filter follows a 6-component pattern:

1. **State field** on the app (e.g., `_stack_filter_branches: frozenset[str]`)
2. **Toggle action** (e.g., `action_toggle_stack_filter()`)
3. **Application logic** in `_apply_filter_and_sort()`
4. **Escape chain entry** in `action_exit_app()`
5. **Visual indicator** in the ViewBar
6. **Key binding** in `BINDINGS`

**Stack filter branches**: Uses `frozenset[str]` for immutability and efficient membership testing. Do not use `set` or `list`.

## Progressive Escape Chain

`action_exit_app()` peels back one filter layer per Escape press:

```
1. Clear objective filter if set → return
2. Clear stack filter if set → return
3. Clear text input if active → return
4. Quit app
```

**Rule**: Every new filter MUST add an entry to this chain, or the filter becomes stuck with no way for the user to clear it.

## View Mode Switching

Three views with instant switching via cache:

| View       | Label query     | Excludes    |
| ---------- | --------------- | ----------- |
| Plans      | `erk-plan`      | `erk-learn` |
| Learn      | `erk-learn`     | —           |
| Objectives | `erk-objective` | —           |

**Cache strategy**: `dict[tuple[str, ...], list[PlanRowData]]` keyed by label tuple. Plans and Learn have different labels, so switching between them requires re-fetch if the cache is cold. Each label tuple's data is cached independently.

**Label semantics**: GitHub GraphQL uses AND semantics for label arrays. Multiple labels in `ViewConfig.labels` means items must have ALL listed labels. Use `exclude_labels` for defense-in-depth deduplication (e.g., Plans view excludes `erk-learn`).

## ViewConfig

Every `ViewMode` must have a corresponding `ViewConfig` in `VIEW_CONFIGS`. Missing configs cause `KeyError` at runtime.

`ViewConfig` contains:

- `labels`: GitHub label query (AND semantics)
- `exclude_labels`: Labels to exclude from results
- `display_name`: Human-readable name for ViewBar

## ViewBar Widget

The ViewBar shows active view mode and filter indicators.

**Naming constraint**: Don't use `_render()` as a method name — Textual's LSP reserves it. Use `_refresh_display()` instead.

## PlanBodyScreen Content Type

`PlanBodyScreen` accepts `content_type: Literal["Plan", "Objective"]` controlling both UI labels and gateway method calls.

**Rule**: Content type is determined by `_view_mode` BEFORE pushing the screen, not derived inside:

- `content_type="Objective"` → calls `provider.fetch_objective_content()`
- `content_type="Plan"` → calls `provider.fetch_plan_content()`

## Source Documents

Distilled from: `tui/filter-pipeline`, `tui/filter-toggle-pattern`, `tui/view-switching`, `tui/view-mode-help`
