# Rename TUI "sts" column to "loc" and replace runner emoji with cloud

## Context

The TUI plan table has a column called "sts" (status) that shows:
- A laptop emoji (💻) when a plan has a local worktree checkout
- A runner emoji (🏃) when a plan has a remote workflow run

The column name "sts" is misleading since the column actually indicates *location* (local vs remote), not status. This plan renames the column header from "sts" to "loc" (location) and replaces the runner emoji (🏃) with a cloud emoji (☁️) to better represent remote execution.

## Changes

### 1. `src/erk/tui/widgets/plan_table.py`

**Column header rename** (line 176-177):

Change the comment and column header:
```python
# Before:
# Plans view: plan, obj, sts, title, branch, ...
self.add_column("sts", key="status")

# After:
# Plans view: plan, obj, loc, title, branch, ...
self.add_column("loc", key="status")
```

Note: The `key="status"` stays the same since it's a data binding key used internally, and changing it would require deeper refactoring with no user-facing benefit.

**Emoji replacement** (lines 309-314):

Change the comment and the runner emoji to a cloud emoji:
```python
# Before:
# Compact status emoji: 💻 = local checkout, 🏃 = remote run
status_parts: list[str] = []
if row.exists_locally:
    status_parts.append("\U0001f4bb")
if row.run_url is not None:
    status_parts.append("\U0001f3c3")

# After:
# Compact location emoji: 💻 = local checkout, ☁️ = remote run
status_parts: list[str] = []
if row.exists_locally:
    status_parts.append("\U0001f4bb")
if row.run_url is not None:
    status_parts.append("\u2601\ufe0f")
```

The cloud emoji is `☁️` which is Unicode `U+2601` (CLOUD) + `U+FE0F` (variation selector for emoji presentation). In Python: `"\u2601\ufe0f"`.

### 2. `tests/tui/test_plan_table.py`

**Update test section comment** (line 605):
```python
# Before:
# --- Tests for compact status emoji column ---

# After:
# --- Tests for compact location emoji column ---
```

**Update test for remote-only** (line 631-639):
```python
# Before (test_row_to_values_status_remote_only):
assert values[2] == "\U0001f3c3"

# After:
assert values[2] == "\u2601\ufe0f"
```

**Update test for both** (line 642-650):
```python
# Before (test_row_to_values_status_both):
assert values[2] == "\U0001f4bb\U0001f3c3"

# After:
assert values[2] == "\U0001f4bb\u2601\ufe0f"
```

Also update the docstrings in these test functions to say "cloud emoji" instead of "runner emoji".

## Files NOT Changing

- `src/erk/tui/data/types.py` — No changes to `PlanRowData` fields. The `exists_locally` and `run_url` fields remain as-is since they correctly model the data.
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` — No changes to data population logic. The data source is the same; we're only changing display.
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py` — No changes needed since `make_plan_row()` helper doesn't deal with the emoji rendering.
- No other files reference the "sts" header string or the runner emoji.

## Verification

1. Run `pytest tests/tui/test_plan_table.py -k "status"` — all four status/location tests should pass with the updated emoji values
2. Run `pytest tests/tui/test_plan_table.py` — full plan table test suite passes
3. Run `ruff check src/erk/tui/widgets/plan_table.py` — no lint issues
4. Run `ty check src/erk/tui/widgets/plan_table.py` — no type errors