# Plan: Add --json to erk pr list and erk pr view

**Part of Objective #9009, Node 2.1 (pr-read-json)**
**Depends on:** PR #9013 (nodes 1.1-1.3: `@json_output` decorator, structured errors, one-shot JSON)

## Context

Agents consuming `erk pr list` and `erk pr view` currently get human-readable Rich tables and styled text. The underlying data is already available as JSON via exec scripts (`dash-data` and `get-plan-info`), but the CLI commands don't expose it. This plan adds `--json` flags to both commands using the `@json_output` decorator from PR #9013, passing through the existing exec script JSON output.

## Step 1: Add `--json` to `erk pr list`

**File:** `src/erk/cli/commands/pr/list_cmd.py`

Apply `@json_output` decorator to `pr_list` command. When `json_mode=True`, serialize the `PlanRowData` rows to JSON using the existing `_serialize_plan_row()` helper from `dash_data.py` and emit via `emit_json()`.

Changes:
- Import `json_output`, `emit_json` from `erk.cli.json_output`
- Import `_serialize_plan_row` from `erk.cli.commands.exec.scripts.dash_data` (or extract to shared location)
- Add `@json_output` above `@click.command("list")`
- Add `json_mode: bool` parameter to `pr_list()`
- Pass `json_mode` into `_pr_list_impl()` (add parameter)
- In `_pr_list_impl()`, after sorting, if `json_mode`: call `emit_json({"plans": [_serialize_plan_row(r) for r in rows], "count": len(rows)})` and return

**Decision: Reuse `_serialize_plan_row`** — Extract it from `dash_data.py` to a shared module (`src/erk/tui/data/serialization.py`) so both `dash_data.py` and `list_cmd.py` import from the same place. This avoids duplication and keeps the output format identical.

### Output shape (matches `dash-data` exec script):
```json
{"success": true, "plans": [{...PlanRowData fields...}], "count": 5}
```

## Step 2: Add `--json` to `erk pr view`

**File:** `src/erk/cli/commands/pr/view_cmd.py`

Apply `@json_output` decorator to `pr_view` command. When `json_mode=True`, serialize plan data to JSON matching the `get-plan-info` exec script output shape.

Changes:
- Import `json_output`, `emit_json` from `erk.cli.json_output`
- Add `@json_output` above `@click.command("view")`
- Add `json_mode: bool` parameter to `pr_view()`
- After building `plan` and `header_info`, if `json_mode`: emit JSON and return (skip `_display_plan()`)

### Output shape (matches `get-plan-info` exec script, with header info):
```json
{
  "success": true,
  "plan_id": "42",
  "title": "...",
  "state": "OPEN",
  "labels": [...],
  "url": "...",
  "objective_id": null,
  "header": {
    "created_by": "...",
    "worktree_name": "...",
    "objective_issue": 9009,
    ...
  },
  "body": "..."
}
```

Note: Always include `body` in JSON mode (unlike human mode which requires `--full`). Agents always want the full content.

## Step 3: Extract `_serialize_plan_row` to shared module

**New file:** `src/erk/tui/data/serialization.py`

Move `_serialize_plan_row()` from `dash_data.py` to this shared module. Update both `dash_data.py` and `list_cmd.py` to import from the new location.

## Step 4: Tests

### `tests/unit/cli/commands/pr/test_pr_list_json.py` (NEW)

Test `pr_list --json` via `CliRunner`:
- `test_json_output_success` — Returns valid JSON with `success`, `plans`, `count`
- `test_json_output_empty` — Returns `{"success": true, "plans": [], "count": 0}` when no plans
- `test_json_output_error` — Error serialized as JSON when `--json` active

Uses fakes for `RealPlanDataProvider` — follow `fake-driven-testing` patterns.

### `tests/unit/cli/commands/pr/test_pr_view_json.py` (NEW)

Test `pr_view --json` via `CliRunner`:
- `test_json_output_success` — Returns valid JSON with plan fields
- `test_json_output_includes_body` — Body always included in JSON mode
- `test_json_output_not_found` — Error JSON for missing plan

### `tests/unit/tui/data/test_serialization.py` (NEW)

Test extracted `_serialize_plan_row`:
- `test_datetime_serialization` — Datetimes converted to ISO 8601
- `test_tuple_to_list` — Tuple fields (log_entries, objective_deps_plans) become lists

## Files to Modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/pr/list_cmd.py` | Add `@json_output`, `json_mode` branch |
| `src/erk/cli/commands/pr/view_cmd.py` | Add `@json_output`, `json_mode` branch |
| `src/erk/tui/data/serialization.py` | NEW — extracted `serialize_plan_row()` |
| `src/erk/cli/commands/exec/scripts/dash_data.py` | Import from shared serialization |
| `tests/unit/cli/commands/pr/test_pr_list_json.py` | NEW |
| `tests/unit/cli/commands/pr/test_pr_view_json.py` | NEW |
| `tests/unit/tui/data/test_serialization.py` | NEW |

## Verification

1. Run `erk pr list --json` and confirm valid JSON matching `dash-data` output shape
2. Run `erk pr view 42 --json` and confirm valid JSON matching `get-plan-info` output shape
3. Run `erk pr list --json --state closed` and confirm filters work with JSON mode
4. Run `erk pr view 99999 --json` and confirm error JSON output
5. Run unit tests: `pytest tests/unit/cli/commands/pr/test_pr_list_json.py tests/unit/cli/commands/pr/test_pr_view_json.py tests/unit/tui/data/test_serialization.py`
6. Run `make fast-ci` to confirm no regressions
