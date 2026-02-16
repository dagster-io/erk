---
title: Plan Data Provider Design
description: When to add fields to Plan vs pass as parameters to _build_row_data()
read_when:
  - adding new fields to TUI data pipeline
  - deciding where data belongs in Plan architecture
  - working with PlanRowData and RealPlanDataProvider
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# Plan Data Provider Design

## The Decision

When adding data to the TUI:

### Add to Plan dataclass

Data that ALL providers could supply, regardless of data source.

Examples: plan title, status, timestamps, file paths

### Pass as parameter to \_build_row_data()

Data that is provider-specific (only available from certain sources).

Examples: `issue.author` from GitHub, file modification time from local files

## Rationale

The `Plan` type is provider-agnostic - it should work whether plans come from GitHub issues, local files, or other sources. Provider-specific data like GitHub issue author should be passed as parameters.

## Example

<!-- Source: src/erk/tui/providers/provider.py, RealPlanDataProvider._build_row_data -->

See `author` parameter in `RealPlanDataProvider._build_row_data()` - extracted from `IssueInfo.author` and passed through rather than added to the `Plan` dataclass.
