# Fix: Decouple Objectives Screen Columns from Plans Screen

## Context

PR #7763 added draft_pr-mode columns (`sts`, `stage`, `created`) to `_setup_columns()` **before** the objectives view early-return check at line 172. The objectives screen now inherits 3 unwanted columns. Since `_row_to_values()` for objectives returns only 6 values but there are now 10 columns, the data shifts left into the wrong columns and the rightmost 4 columns are empty.

**Screenshot confirms**: progress ("0/5") appears under `sts`, next_node ("1.1 Chang...") under `stage`, deps ("ready") under `created`, updated ("7h ag") under `obj`, and author ("schro") under `prog`. Columns `next node`, `deps`, `updated`, `author` are empty.

## Plan

### Step 1: Move objectives block before draft_pr/obj columns

**File**: `src/erk/tui/widgets/plan_table.py` — `_setup_columns()` (~line 147)

Move the objectives `if` block to immediately after the `plan` column, before any draft_pr or `obj` column logic:

```python
self.add_column(plan_col_header, key="plan", width=6)
col_index += 1

# Objectives view: fully independent column set, return early
if self._view_mode == ViewMode.OBJECTIVES:
    self.add_column("prog", key="progress", width=5)
    col_index += 1
    self.add_column("next node", key="next_node", width=30)
    col_index += 1
    self.add_column("deps", key="deps", width=12)
    col_index += 1
    self.add_column("updated", key="updated", width=7)
    col_index += 1
    self.add_column("author", key="author", width=9)
    col_index += 1
    return

# Plans view: draft_pr columns, obj, etc. (unchanged below)
if self._plan_backend == "draft_pr":
    ...
self.add_column("obj", key="objective", width=5)
...
```

**No changes to `_row_to_values()`** — it already returns the correct 6 values for objectives: `(plan_cell, progress, next_node, deps, updated, author)`.

### Step 2: Update tests

Update any tests in `tests/tui/test_plan_table.py` that assert on objectives column setup (e.g., column count, column keys, presence of `obj` column in objectives view).

## Critical files

- `src/erk/tui/widgets/plan_table.py` — main fix
- `tests/tui/test_plan_table.py` — test updates

## Verification

1. Run TUI tests: `pytest tests/tui/`
2. Run `erk dash -i`, switch to tab 3 (Objectives)
3. Confirm columns are: `pr`, `prog`, `next node`, `deps`, `updated`, `author`
4. Confirm data displays correctly in each column
5. Switch between tabs 1/2/3 to verify no regressions
