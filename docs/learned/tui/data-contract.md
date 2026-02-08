---
title: TUI Data Contract
read_when:
  - "building an alternate frontend consuming plan data"
  - "adding fields to PlanRowData or PlanDataProvider"
  - "understanding the display-vs-raw field duality"
  - "serializing plan data to JSON for external consumers"
tripwires:
  - action: "formatting display strings during table render"
    warning: "Display strings are pre-formatted at fetch time. Add new *_display fields to PlanRowData and format in RealPlanDataProvider._build_row_data(), not in the widget layer."
  - action: "adding a field to PlanRowData without updating make_plan_row"
    warning: "The fake's make_plan_row() helper must stay in sync. Add the new field with a sensible default there too, or all TUI tests will break."
  - action: "putting PlanDataProvider ABC in src/erk/tui/"
    warning: "The ABC lives in erk-shared so desktop-dash and other external consumers can depend on it without importing the full TUI package."
last_audited: "2026-02-08"
audit_result: regenerated
---

# TUI Data Contract

The TUI data layer is designed around a single frozen dataclass (`PlanRowData`) that carries both display-ready strings and raw identifiers. This document explains the design decisions behind the data contract, the cross-package split, and the pitfalls of JSON serialization — things that can't be learned by reading any single source file.

## Why Display and Raw Fields Coexist

<!-- Source: src/erk/tui/data/types.py, PlanRowData -->

`PlanRowData` carries two kinds of fields for the same data. For example, `pr_number` (raw `int | None`) and `pr_display` (pre-formatted `str` like `"#123 👀"`). This is deliberate:

- **Pre-formatted display fields** (`*_display`) are computed once at fetch time, not at render time. The Textual `DataTable` renders frequently (on scroll, resize, focus changes), so pushing formatting into the data fetch keeps rendering fast and eliminates formatting inconsistencies between refreshes.
- **Raw fields** exist because TUI actions (open URL, copy to clipboard, close plan) need actual identifiers and URLs, not display strings with emoji.

This duality means every new piece of displayable data requires two fields: a raw value for actions and a display string for rendering. The formatting logic lives in `RealPlanDataProvider._build_row_data()`, not in any widget.

## The Cross-Package Split

The data types and their provider ABC live in different packages:

| Artifact                                | Location                                             | Why                               |
| --------------------------------------- | ---------------------------------------------------- | --------------------------------- |
| `PlanRowData`, `PlanFilters`            | `src/erk/tui/data/types.py`                          | TUI-specific display types        |
| `PlanDataProvider` ABC                  | `packages/erk-shared/.../plan_data_provider/abc.py`  | Shared interface for any consumer |
| `RealPlanDataProvider`                  | `packages/erk-shared/.../plan_data_provider/real.py` | Production implementation         |
| `FakePlanDataProvider`, `make_plan_row` | `packages/erk-shared/.../plan_data_provider/fake.py` | Test doubles                      |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py, PlanDataProvider -->

The ABC lives in `erk-shared` (not `src/erk/tui/`) because external consumers like the desktop dashboard's `erk exec dash-data` command need to instantiate a `RealPlanDataProvider` without importing the full TUI package. If the ABC were in `src/erk/tui/`, the desktop-dash Electron app would transitively pull in Textual and all TUI widgets.

## Data Transformation Pipeline

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, RealPlanDataProvider.fetch_plans -->

`RealPlanDataProvider.fetch_plans()` transforms data through three stages:

1. **`IssueInfo`** — Raw GitHub API response (issue number, title, body, labels)
2. **`Plan`** — Domain model with parsed metadata (state, URL, assignees, timestamps)
3. **`PlanRowData`** — Display-ready with pre-formatted strings, worktree data, and PR linkages

The key assembly step is `_build_row_data()`, which merges data from four sources in a single pass: the `Plan` domain object, PR linkages from a batched GraphQL query, local worktree filesystem scan, and plan header metadata extracted from the issue body. Understanding this merging is essential when debugging why a field shows stale data — the bug could be in any of these four sources.

## JSON Serialization Gotchas

<!-- Source: src/erk/cli/commands/exec/scripts/dash_data.py, _serialize_plan_row -->

The `erk exec dash-data` command serializes `PlanRowData` to JSON for the desktop dashboard. `dataclasses.asdict()` handles most fields, but three types need manual conversion:

| Type                                | Problem                                                                                              | Fix                                                    |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| `datetime` fields                   | `asdict()` preserves `datetime` objects, which aren't JSON-serializable                              | Convert to ISO 8601 strings via `.isoformat()`         |
| `tuple[tuple[...]]` (`log_entries`) | JSON has no tuple type; `asdict()` converts to nested lists but nested tuples need explicit handling | Convert to list of lists                               |
| Display strings with emoji          | Emoji in `*_display` fields may cause encoding or rendering issues in some frontends                 | Frontend-specific; the contract doesn't normalize them |

The production serialization lives in `_serialize_plan_row()` in `dash_data.py`. Any new `PlanRowData` field with a non-primitive type will need a corresponding serialization handler there.

## Adding a New Field: Checklist

Adding a field to `PlanRowData` touches at minimum five places. Missing any one causes test failures or silent data loss:

1. **`PlanRowData`** in `src/erk/tui/data/types.py` — add the field definition
2. **`RealPlanDataProvider._build_row_data()`** — populate it from source data
3. **`make_plan_row()`** in the fake module — add a parameter with sensible default
4. **`_serialize_plan_row()`** in `dash_data.py` — handle if non-primitive type
5. **Widget layer** — consume the field for display or action (if applicable)

If the field is a display field, also add the raw counterpart (or vice versa) following the duality pattern.

## Related Documentation

- [TUI Architecture Overview](architecture.md) — Overall TUI structure and layer boundaries
- [TUI Action Command Inventory](action-inventory.md) — Commands that consume PlanRowData fields
- [Erk Desktop Dashboard](../desktop-dash/) — Alternate frontend consuming this data contract
