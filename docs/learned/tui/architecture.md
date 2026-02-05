---
title: TUI Architecture Overview
read_when:
  - "understanding TUI structure"
  - "implementing TUI components"
  - "working with TUI data providers"
last_audited: "2026-02-05"
audit_result: edited
---

# TUI Architecture Overview

The erk TUI is built with Textual and follows a layered architecture separating data fetching, filtering, and rendering.

## Directory Structure

```
src/erk/tui/
├── app.py              # Main Textual App (ErkDashApp)
├── data/               # Data layer
│   └── types.py        # Data types (PlanRowData, PlanFilters)
├── filtering/          # Filter layer
│   ├── logic.py        # Filter application logic
│   └── types.py        # Filter types (FilterState, FilterMode)
├── sorting/            # Sort layer
│   ├── logic.py        # Sort application logic
│   └── types.py        # Sort types (SortKey, SortState, BranchActivity)
├── commands/           # Command palette layer
│   ├── provider.py     # Command providers for palette
│   ├── registry.py     # Command registration
│   └── types.py        # Command types (CommandDefinition, CommandContext)
├── screens/            # Modal screens
│   ├── help_screen.py
│   ├── issue_body_screen.py
│   └── plan_detail_screen.py
├── widgets/            # UI components
│   ├── plan_table.py   # Plan list table
│   ├── status_bar.py   # Status bar component
│   ├── command_output.py
│   ├── clickable_link.py
│   └── copyable_label.py
├── styles/             # Textual CSS
│   └── dash.tcss
└── jsonl_viewer/       # Separate JSONL viewer app
```

The `PlanDataProvider` ABC and its fake live in `erk_shared` (not in `src/erk/tui/`):

- ABC: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`
- Fake: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`
- Command executor ABC/real: `packages/erk-shared/src/erk_shared/gateway/command_executor/`

## Data Layer

### PlanDataProvider (ABC)

Abstract interface for fetching plan data. Follows the same ABC/Fake pattern as gateways. Defined in `erk_shared.gateway.plan_data_provider.abc`.

Key methods: `fetch_plans()`, `close_plan()`, `submit_to_queue()`, `fetch_branch_activity()`, `fetch_plan_content()`. Also exposes `repo_root`, `clipboard`, and `browser` properties. See the ABC source for the full interface.

### PlanRowData

Frozen dataclass containing both:

- **Display strings**: Pre-formatted for rendering (`pr_display`, `checks_display`, `run_state_display`)
- **Raw data**: For actions and sorting (`pr_number`, `issue_number`, timestamps)

This separation ensures:

- Table rendering is fast (no formatting during render)
- Actions have access to raw IDs/URLs
- Data is immutable (consistent table state)

### PlanFilters

Frozen dataclass specifying query filters. Defined in `erk.tui.data.types`. Fields: `labels`, `state`, `run_state`, `limit`, `show_prs`, `show_runs`, `creator`. See source for details and the `default()` factory method.

## Command Execution Layer

See [Command Execution](command-execution.md) for detailed patterns on:

- Sync vs streaming execution
- Background thread handling
- Cross-thread UI updates

The command palette is powered by `CommandDefinition` / `CommandContext` types in `erk.tui.commands.types` and providers in `erk.tui.commands.provider`. The `CommandExecutor` ABC and `RealCommandExecutor` live in `erk_shared.gateway.command_executor`.

## Widget Layer

### PlanDataTable

DataTable subclass (class `PlanDataTable` in `erk.tui.widgets.plan_table`) displaying plans. Columns are dynamic based on `PlanFilters.show_prs` and `show_runs` flags. Core columns: plan, title, obj, lrn, local-wt, local-impl. With PRs: adds pr, chks, comments. With runs: adds remote-impl, run-id, run-state.

Supports click events on individual columns (plan, pr, objective, learn, local-wt, run-id) which post typed messages handled by `ErkDashApp`. See `_setup_columns()` and `on_click()` in the source for full column logic.

### StatusBar

Shows plan count, sort mode, last update time with fetch duration, countdown to next refresh, action messages, and key binding hints. See `StatusBar._update_display()` in `erk.tui.widgets.status_bar` for the exact layout.

## Testing Strategy

### Unit Testing TUI Components

Use fake providers instead of mocking. `FakePlanDataProvider` lives in `erk_shared.gateway.plan_data_provider.fake` and accepts keyword-only arguments (`plans`, `clipboard`, `browser`, `repo_root`, `fetch_error`). The `make_plan_row()` helper in the same module creates test `PlanRowData` instances with sensible defaults.

### Testing Async Operations

See [Textual Async Testing](textual-async.md) for patterns on testing async TUI code.

## Data Shape at Each Layer

Understanding the data shape at each pipeline stage helps debug rendering issues.

### Layer 1: GitHub API Response

Raw JSON from GitHub. Issue titles are plain strings without prefixes:

```json
{
  "number": 123,
  "title": "Add dark mode",
  "labels": [{ "name": "erk-plan" }, { "name": "erk-learn" }],
  "body": "<!-- erk-metadata: {...} -->\n\n# Plan content..."
}
```

### Layer 2: Gateway/Service Response

The data provider fetches GitHub issue data and transforms it into `PlanRowData` directly. There is no intermediate `Plan` dataclass in the TUI pipeline.

### Layer 3: PlanRowData (Widget Consumption)

Frozen dataclass with both raw data and pre-formatted display strings. The full type has 30+ fields spanning issue data, PR data, worktree data, run data, learn workflow data, objective data, and comment data. See `PlanRowData` in `erk.tui.data.types` for the complete field list and docstring.

Key design: display fields (e.g., `pr_display`, `checks_display`, `learn_display_icon`) are pre-formatted at fetch time so the table widget never does string formatting during render. Raw fields (e.g., `pr_number`, `issue_url`, `run_url`) are available for actions like opening URLs.

### Layer 4: DataTable Cell

Individual cell values passed to `add_row()`:

- Strings are interpreted as Rich markup by default
- `[bracketed]` text treated as style tags
- Wrap user data in `Text()` to escape - see [DataTable Markup Escaping](../textual/datatable-markup-escaping.md)

## Design Principles

1. **Frozen Data Types**: All data types are frozen dataclasses to ensure immutability during table rendering
2. **Pre-formatted Display**: Format strings at fetch time, not render time
3. **ABC Providers**: Use ABC/Fake pattern for testability (same as integrations)
4. **Layered Architecture**: Data → Filtering → Rendering separation

## Related Documentation

- [Command Execution](command-execution.md) - Sync vs streaming execution patterns
- [Streaming Output](streaming-output.md) - Real-time command output display
- [Textual Async](textual-async.md) - Async testing patterns
- [Erk Architecture](../architecture/erk-architecture.md) - Architecture patterns
