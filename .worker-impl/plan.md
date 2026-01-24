# Fix: TUI Not Displaying [erk-learn] Prefix in Plan Titles

## Problem

The TUI dashboard (`erk dash -i`) displays plan titles without the `[erk-learn]` prefix, even though GitHub issues have the correct title (e.g., `[erk-learn] Learn Plan: Issue #5770 - Fix: Add...`).

## Root Cause

In `src/erk/tui/widgets/plan_table.py:222`, the title is passed as a plain string:

```python
values: list[str | Text] = [plan_cell, row.title]
```

Textual's DataTable interprets plain strings as Rich markup. The `[erk-learn]` portion is treated as a Rich markup tag (like `[bold]` or `[red]`), which renders as invisible text since there's no "erk-learn" style defined.

## Fix

Wrap the title in a `Text` object to prevent Rich markup interpretation:

```python
values: list[str | Text] = [plan_cell, Text(row.title)]
```

## Files to Modify

- `src/erk/tui/widgets/plan_table.py` - Line 222 in `_row_to_values()` method

## Verification

1. Run `erk dash -i` and verify that learn plans show `[erk-learn]` prefix in the title column
2. Run existing TUI tests: `pytest tests/tui/`