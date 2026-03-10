---
name: erk-tui
description: >
  Erk TUI development patterns for the Textual-based dashboard. Use when adding
  commands, columns, filters, modal screens, or async operations to erk dash.
  Covers architecture, data contracts, command registration, filter pipeline,
  widget lifecycle, streaming output, and Textual framework quirks.
---

# Erk TUI Development

**Use this skill when**: Working on `src/erk/tui/`, adding commands/columns/filters to `erk dash`, building modal screens, implementing async operations, or debugging Textual framework issues.

**Prerequisites**: Load `dignified-python` for Python coding standards. Load `fake-driven-testing` for test patterns (TUI tests use the 5-layer architecture with `FakePlanDataProvider`).

## Architecture Overview

```
┌─────────────────────────────────────┐
│  Action Layer (commands, keys)      │  ← Operates on selected rows
├─────────────────────────────────────┤
│  Widget Layer (PlanDataTable)       │  ← Displays filtered rows
├─────────────────────────────────────┤
│  Filter Layer (PlanFilters)         │  ← Controls what data appears
├─────────────────────────────────────┤
│  Display Layer (PlanRowData)        │  ← Pre-formatted display strings
├─────────────────────────────────────┤
│  Data Layer (PlanDataProvider)      │  ← Fetches from GitHub API
└─────────────────────────────────────┘
```

**Data flow**: GitHub API → `IssueInfo` → `Plan` → `PlanRowData` (frozen dataclass with raw + display fields) → `PlanDataTable` renders pre-formatted strings.

**Key principle**: All formatting happens at fetch time in `_build_row_data()`, never during render. This keeps scrolling and resizing sub-millisecond.

**Mixin architecture**: `ErkDashApp` uses mixins for logical grouping, but `@on()` decorated event handlers MUST stay on the concrete `ErkDashApp` class (Textual's `_MessagePumpMeta` only scans `class.__dict__`, not MRO).

## Quick Decision: What Should I Read?

**Adding a new command?**
→ Read `commands.md` for the 3-place registration pattern and dual-handler architecture

**Adding a new column?**
→ Read `data-layer.md` for the 5-step column addition checklist

**Adding or modifying filters?**
→ Read `filtering-and-views.md` for the filter pipeline and toggle pattern

**Building a modal screen or widget?**
→ Read `screens-and-widgets.md` for the 7-element modal checklist

**Adding async operations or streaming output?**
→ Read `async-operations.md` for `@work(thread=True)` patterns and thread safety

**Hitting Textual framework issues?**
→ Read `textual-quirks.md` for DataTable, CSS, Rich markup, and testing gotchas

**Understanding the data model?**
→ Read `data-layer.md` for `PlanRowData`, `PlanFilters`, and the cross-package split

**Understanding overall architecture?**
→ Read `architecture.md` for layers, mixins, directory structure, and design principles

## When to Read Each Reference Document

### `architecture.md`

**Read when**: Understanding or modifying the TUI's layered architecture, mixin structure, or directory layout.

**Contents**: Layer diagram, mixin metaclass constraint, data flow pipeline, directory structure, design principles, Runs tab architecture.

### `data-layer.md`

**Read when**: Adding columns, modifying `PlanRowData`, changing data contracts, or working with the provider ABC.

**Contents**: `PlanRowData` display-vs-raw duality, 5-step column addition checklist, `PlanFilters` construction, cross-package data contract split, JSON serialization gotchas, frozen dataclass field management.

### `commands.md`

**Read when**: Adding or modifying TUI commands, working with the command palette, or implementing command execution.

**Contents**: 3-place registration coordination, dual-handler pattern, three-layer validation, category semantics (ACTION/OPEN/COPY), view-aware filtering, clipboard text generation, `CommandPalette` integration.

### `filtering-and-views.md`

**Read when**: Adding filters, modifying view switching, or working with the escape chain.

**Contents**: Filter pipeline order, server-side vs client-side filters, toggle pattern, progressive escape chain, view mode switching, cache strategy, label semantics.

### `screens-and-widgets.md`

**Read when**: Building modal screens, adding keyboard shortcuts, working with status indicators, or implementing plan detail views.

**Contents**: 7-element modal checklist, dismiss-then-delegate pattern, keyboard shortcut inventory, status indicator rendering, lifecycle display stages, title rendering pipeline, truncation edge cases.

### `async-operations.md`

**Read when**: Adding background operations, streaming subprocess output, or implementing multi-operation tracking.

**Contents**: `@work(thread=True)` pattern, `call_from_thread()` threading requirement, streaming Popen setup, multi-operation tracking with op IDs, async state snapshot for race prevention, `action_refresh()` after completion.

### `textual-quirks.md`

**Read when**: Hitting Textual framework issues, working with DataTable, CSS styling, Rich markup, or writing TUI tests.

**Contents**: DataTable cursor type initialization, `Text()` wrapping for markup escaping, `_render()` name conflict, `get_system_commands()` override location, background worker patterns, test app configuration, `ModalScreen` callback typing.

## Critical Tripwires

These are the highest-impact gotchas. Violating any causes bugs that are hard to diagnose.

1. **`@on()` handlers on mixins are silently ignored** — Textual's metaclass only scans `class.__dict__`. Keep all `@on()` handlers on `ErkDashApp`.

2. **Wrap DataTable cell values in `Text()`** — `[brackets]` in user data are parsed as Rich markup and disappear. Always use `Text(value)`.

3. **`call_from_thread()` for ALL UI updates from `@work` threads** — Direct widget calls from background threads cause silent UI corruption.

4. **`stdin=subprocess.DEVNULL` for all TUI subprocesses** — Child processes inherit TUI's stdin, causing deadlocks when they prompt for input.

5. **Snapshot `_view_mode` before async fetch** — User may switch tabs during fetch. Cache under `fetched_mode`, display only if it still matches current view.

6. **`finish_operation()` in BOTH success and error paths** — Missing calls leave ghost operations in the status bar. Use try/finally.

7. **Prefix enrichment BEFORE filtering** — `[erk-learn]` prefix must be added before filtering/sorting stages or metadata gets lost.

8. **5-step column addition** — Missing any of the 5 coordinated changes (types, real provider, table, fake provider, serialization) causes failures.

9. **Three-layer validation for commands with optional fields** — Registry predicate + handler guard + app-level helper. Predicates alone can become stale.

10. **Progressive escape chain** — New filters must add an entry to `action_exit_app()` or they become stuck with no way to clear.

11. **No emoji variation selectors (`\ufe0f`)** — Forces double-wide rendering in terminals, breaking column alignment. Test new emoji in terminal first.

12. **Modal `event.prevent_default()` + `event.stop()` BEFORE dismiss logic** — Without this, keystrokes leak to the underlying view.

13. **`_refresh_display()` not `_render()`** — Textual's LSP reserves `_render()`. Use `_refresh_display()` for widget refresh methods.

14. **`run_worker(exclusive=True)` to cancel previous workers** — Prevents duplicate concurrent operations.

15. **`bufsize=1` with `text=True` for streaming Popen** — Without it, output is block-buffered and doesn't stream line-by-line.

## Key Principles

1. **Format at fetch, not render** — All `*_display` fields are computed in `_build_row_data()`. The widget layer only renders pre-formatted strings.

2. **One registry, two contexts** — Commands are defined once but executed from both the main list and detail modal. The duplication in execution handlers is intentional.

3. **Data-driven availability** — Command visibility is controlled by `is_available` predicates on `PlanRowData` field presence, not runtime checks.

4. **Immutable data** — `PlanRowData` and `PlanFilters` are frozen dataclasses. Use `dataclasses.replace()` for modifications.

5. **Thread safety through message passing** — `call_from_thread()` is the only safe way to update UI from background threads.

6. **View isolation** — Plans, Learn, and Objectives views have independent label queries and caches. View predicates guarantee command mutual exclusivity.

## Source Documents

This skill is the authoritative reference for TUI development patterns. Originally distilled from 40 documents that have since been consolidated into this skill.
