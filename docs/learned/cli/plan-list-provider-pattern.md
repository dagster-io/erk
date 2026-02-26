---
title: Plan List Provider Pattern
read_when:
  - "modifying erk pr list output"
  - "understanding how plan list and TUI share data providers"
  - "adding columns to plan list display"
tripwires:
  - action: "adding a column to plan list without checking PlanDataTable._setup_columns()"
    warning: "Column order in list_cmd.py must mirror plan_table.py for consistency between CLI and TUI. Check both files when modifying columns."
---

# Plan List Provider Pattern

Both `erk pr list` (CLI) and `erk dash` (TUI) use `RealPlanDataProvider` to fetch and display plan data. This shared provider pattern ensures consistent data across interfaces.

## Architecture

```
RealPlanDataProvider
  ├── erk pr list (CLI)     → Rich static table
  └── erk dash (TUI/Textual)  → PlanDataTable widget
```

### Shared Components

| Component              | Location                       | Purpose                       |
| ---------------------- | ------------------------------ | ----------------------------- |
| `RealPlanDataProvider` | `packages/erk-shared/`         | Fetches plan data from GitHub |
| `sort_plans()`         | `src/erk/tui/sorting/logic.py` | Reused by both CLI and TUI    |
| `PlanRowData`          | `packages/erk-shared/`         | Shared row data structure     |

### CLI-Specific Components

| Component                 | Location                                | Purpose                      |
| ------------------------- | --------------------------------------- | ---------------------------- |
| `_build_static_table()`   | `src/erk/cli/commands/plan/list_cmd.py` | Builds Rich table from rows  |
| `_row_to_static_values()` | `src/erk/cli/commands/plan/list_cmd.py` | Converts rows to cell values |

## Fake Dependencies for Non-Critical Services

The CLI `list` command doesn't need clipboard, browser, or HTTP operations, so it injects fakes:

<!-- Source: src/erk/cli/commands/plan/list_cmd.py, list_cmd -->

The CLI list command instantiates `RealPlanDataProvider` with fake implementations for clipboard, browser, and HTTP — services unused in the CLI context. See `list_cmd()` in `src/erk/cli/commands/plan/list_cmd.py` for the actual instantiation pattern. This is the fake-driven pattern: non-critical service dependencies get fakes in contexts where they're unused, avoiding unnecessary initialization.

## Column Alignment

The static table in `list_cmd.py` mirrors the TUI's `PlanDataTable._setup_columns()` to ensure users see consistent column order regardless of interface.

## Draft PR Backend

The plan data provider uses the draft-PR backend exclusively. This is the only supported backend for plan storage.

## Related Topics

- [Plan Lifecycle](../planning/lifecycle.md) - Full lifecycle documentation
