# Rename TUI "sts" column to "loc" and replace runner emoji with cloud

## Context

The TUI plans view has a column called "sts" (status) that shows location-related emojis: a laptop (💻) for local worktree and a runner (🏃) for remote GitHub Actions run. The column's purpose is purely about *location* — where the plan's work exists — not general "status." This plan renames the column header to "loc" (location) and replaces the runner emoji (🏃) with a cloud emoji (☁) to better represent "remote/cloud."

## Changes

### 1. `src/erk/tui/widgets/plan_table.py`

**Column header rename** (line 176-177):
- Change the comment from `# Plans view: plan, obj, sts, title, branch, ...` to `# Plans view: plan, obj, loc, title, branch, ...`
- Change `self.add_column("sts", key="status")` to `self.add_column("loc", key="status")`

Note: The `key="status"` stays the same — it's the internal data binding key, not the display label. Only the display header changes.

**Replace runner emoji with cloud** (lines 309-314):
- Change the comment from `# Compact status emoji: 💻 = local checkout, 🏃 = remote run` to `# Compact location emoji: 💻 = local checkout, ☁ = remote/cloud run`
- Change `status_parts.append("\U0001f3c3")` (🏃 runner) to `status_parts.append("\u2601")` (☁ cloud)

The cloud emoji is U+2601 (☁), a simple cloud character that clearly conveys "cloud/remote."

### 2. `tests/tui/test_plan_table.py`

**Update test assertions** (lines 631-650):

In `test_row_to_values_status_remote_only` (line 631):
- Update docstring from `"runner emoji"` to `"cloud emoji"`
- Change assertion from `assert values[2] == "\U0001f3c3"` to `assert values[2] == "\u2601"`

In `test_row_to_values_status_both` (line 642):
- Change assertion from `assert values[2] == "\U0001f4bb\U0001f3c3"` to `assert values[2] == "\U0001f4bb\u2601"`

## Files NOT Changing

- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`** — The `exists_locally` and `run_url` fields in `PlanRowData` are unchanged. The data layer is unaffected.
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`** — No ABC changes needed.
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`** — No fake changes needed.
- **`src/erk/cli/commands/run/list_cmd.py`** — Has its own unrelated `status_cell` for CLI run listing.
- **CHANGELOG.md** — Never modify directly.

## Implementation Details

- The `key="status"` parameter on `add_column` must NOT change — it's the data binding key used internally, not the display label. Only the first positional argument (the column header text) changes from `"sts"` to `"loc"`.
- Use `"\u2601"` (lowercase hex, 4-digit) for the cloud emoji, not the full `"\U0001f3c3"` 8-digit form — U+2601 fits in the BMP.
- The laptop emoji `"\U0001f4bb"` stays exactly as-is.

## Verification

1. Run `pytest tests/tui/test_plan_table.py` — the three status tests should pass with updated assertions
2. Run `ty` for type checking
3. Run `ruff check` for linting
4. Visually confirm: the column header in the plans view now reads "loc" instead of "sts"
5. Visually confirm: remote runs show ☁ instead of 🏃