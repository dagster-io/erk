---
description: Four-step pattern for adding a filterable field to TUI
read_when:
  - adding a new filterable field to erk dash
  - extending filter_plans() function
  - search filter needs to match additional fields
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Filter Extension Pattern

## The Four Steps

When adding a new filterable field:

### 1. Add field to dataclass

Add the field to `PlanRowData` dataclass.

<!-- Source: src/erk/tui/providers/provider.py, PlanRowData -->

See the `PlanRowData` dataclass in `src/erk/tui/providers/provider.py`.

### 2. Thread through data pipeline

Extract from source (`IssueInfo`) and pass as parameter to `_build_row_data()`.

<!-- Source: src/erk/tui/providers/provider.py, RealPlanDataProvider._build_row_data -->

See `RealPlanDataProvider._build_row_data()` which receives provider-specific parameters.

### 3. Add filter logic

Add case-insensitive matching in `filter_plans()`.

<!-- Source: src/erk/tui/providers/filter.py, filter_plans -->

See `filter_plans()` in `src/erk/tui/providers/filter.py`.

### 4. Update tests

- Add parameter to test helper with distinct default
- Update tests that might now match multiple fields
- Test both inclusion (field matches) and exclusion (field doesn't match)

## Provider-Agnostic vs Provider-Specific

**Provider-agnostic** (add to Plan dataclass): Data all providers can supply
**Provider-specific** (pass as parameter): Data only GitHub provider has (like `issue.author`)

<!-- Source: src/erk/tui/providers/provider.py, RealPlanDataProvider._build_row_data -->

See the parameter design in `_build_row_data()` for the distinction.
