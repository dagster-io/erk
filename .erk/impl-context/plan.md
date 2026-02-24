# Plan: Prototype Approach B -- Business Objects with Native JSON + Rich Adapter

**Part of Objective #8088, Node 1.2**

## Context

Objective #8088 compares three approaches for standardized `--json` output across the erk CLI. Node 1.1 (plan #8090) prototypes Approach A (IR types + pluggable renderers). This plan prototypes **Approach B**: frozen dataclass business objects that serve as both the JSON serialization source (`dataclasses.asdict()`) and the input to a thin Rich adapter for human output.

**Core thesis**: The business object IS the canonical representation. No separate IR layer. Two representations (business objects + rendered output) instead of three (PlanRowData + IR + rendered output).

**Scope**: Apply to `plan list` and `plan view` commands, same as Approach A.

## Architecture

```
PlanRowData / Plan+metadata
        |
   builders (extract raw data)
        |
        v
  Business Objects (frozen dataclasses, JSON-clean)
        |
        +---> json.dumps(asdict(obj))   -->  stdout (--json-output)
        |
        +---> Rich adapter functions     -->  stderr (human output)
```

## Implementation

### 1. CREATE `src/erk/cli/commands/plan/business_objects.py`

Frozen dataclasses with JSON-serializable primitives only (str, int, bool, None, list). No datetime objects, emoji, or Rich markup.

**List view types** (nested for natural JSON structure):
- `PlanListPR` — number, url, state, title, head_branch, resolved_comments, total_comments
- `PlanListWorkflowRun` — run_id, status, conclusion, url
- `PlanListLearn` — status, plan_issue, plan_pr, run_url
- `PlanListObjective` — issue, url, done_nodes, total_nodes
- `PlanListEntry` — plan_id, plan_url, title, state, author, created_at (ISO str), updated_at (ISO str), labels, branch, exists_locally, pr (PlanListPR | None), workflow_run (PlanListWorkflowRun | None), learn (PlanListLearn), objective (PlanListObjective | None), lifecycle_stage

**View types** (richer metadata):
- `PlanViewHeader` — created_by, schema_version, worktree_name, source_repo, objective_issue, branch_name
- `PlanViewImpl` — last_local_at, last_local_event, last_local_session, last_local_user, last_remote_at
- `PlanViewLearn` — status, plan_issue, plan_pr, workflow_url
- `PlanViewEntry` — plan_id, title, state, url, labels, assignees, created_at, updated_at, body (None unless --full), header, implementation, learn

### 2. CREATE `src/erk/cli/commands/plan/business_object_builders.py`

Factory functions that construct business objects from existing data sources:

- `build_plan_list_entry(row: PlanRowData) -> PlanListEntry` — Extracts raw fields from PlanRowData, discards `*_display` fields. Converts `datetime` to ISO strings. Constructs nested `PlanListPR`, `PlanListObjective`, etc.
- `build_plan_view_entry(plan: Plan, *, header_info: dict[str, object], include_body: bool) -> PlanViewEntry` — Builds from Plan object + metadata dict (same sources as current `view_plan()`). Uses schema constants from `erk_shared.gateway.github.metadata.schemas` (BRANCH_NAME, CREATED_BY, LEARN_STATUS, etc.).

### 3. CREATE `src/erk/cli/commands/plan/rich_adapter.py`

Pure functions that convert business objects to Rich renderables:

- `render_plan_list_table(entries: list[PlanListEntry], *, show_pr_column: bool) -> Table` — Mirrors existing `_build_static_table()` column layout but derives ALL cell values from business object fields (not PlanRowData display fields). Adds Rich links, emoji, and styling here.
- `render_plan_view(entry: PlanViewEntry, *, full: bool) -> list[str]` — Mirrors existing `view_plan()` output format. Returns formatted lines for `user_output()`.

Private helpers: `_pr_cell()`, `_run_cell()`, `_learn_cell()`, `_objective_cell()`, `_lifecycle_cell()`.

### 4. MODIFY `src/erk/cli/commands/plan/list_cmd.py`

- Add `--json-output` / `json_mode` flag to `list_plans` command (matches `objective view` pattern)
- Pass `json_mode` through to `_list_plans_impl()`
- In `_list_plans_impl()`, after fetching and sorting rows:
  - Convert: `entries = [build_plan_list_entry(row) for row in rows]`
  - If `json_mode`: `click.echo(json.dumps([asdict(e) for e in entries]))`
  - If human: `table = render_plan_list_table(entries, show_pr_column=False)` then existing Console.print() path

### 5. MODIFY `src/erk/cli/commands/plan/view.py`

- Add `--json-output` / `json_mode` flag to `view_plan` command
- After fetching `plan` and `header_info` (line ~282):
  - Build: `entry = build_plan_view_entry(plan, header_info=header_info, include_body=full)`
  - If `json_mode`: `click.echo(json.dumps(asdict(entry)))`
  - If human: `lines = render_plan_view(entry, full=full)` then `user_output()` each line

### 6. CREATE `tests/commands/plan/test_list_json.py`

CLI-level tests using existing pattern (CliRunner + `build_workspace_test_context`):
- `test_plan_list_json_output_basic` — valid JSON, expected top-level list, correct fields
- `test_plan_list_json_output_no_display_strings` — no Rich markup, no emoji in JSON
- `test_plan_list_json_output_with_filters` — respects --state, --limit
- `test_plan_list_json_output_empty` — returns `[]`

### 7. CREATE `tests/commands/plan/test_view_json.py`

- `test_plan_view_json_output_basic` — valid JSON with expected structure
- `test_plan_view_json_output_with_full` — body populated
- `test_plan_view_json_output_without_full` — body is null
- `test_plan_view_json_output_with_header` — header metadata included

### 8. CREATE `tests/unit/cli/commands/plan/test_business_objects.py`

Unit tests for builders (Layer 4):
- `test_build_plan_list_entry_extracts_raw_data` — verify raw fields, not display
- `test_build_plan_list_entry_pr_fields` — nested PlanListPR populated
- `test_build_plan_list_entry_no_pr` — pr is None
- `test_plan_list_entry_asdict_json_serializable` — `json.dumps(asdict(entry))` doesn't raise
- `test_build_plan_view_entry_with_header` — header metadata extracted

### 9. CREATE `tests/unit/cli/commands/plan/test_rich_adapter.py`

Unit tests for adapter (Layer 4):
- `test_render_plan_list_table_returns_table` — returns Rich Table
- `test_render_plan_view_returns_formatted_lines` — returns list of strings

## Key Files Reference

| File | Role |
|------|------|
| `src/erk/tui/data/types.py` | PlanRowData definition (46 fields) |
| `src/erk/cli/commands/plan/list_cmd.py:228-311` | `_list_plans_impl()` — integration point |
| `src/erk/cli/commands/plan/view.py:222-335` | `view_plan()` — integration point |
| `src/erk/cli/commands/objective/view_cmd.py:128-164` | Reference `--json-output` pattern |
| `erk_shared/gateway/github/metadata/schemas.py` | Schema constants (BRANCH_NAME, LEARN_STATUS, etc.) |
| `erk_shared/gateway/plan_data_provider/fake.py:212` | `make_plan_row()` test helper |
| `erk_shared/plan_store/types.py` | `Plan`, `PlanState` types |
| `tests/commands/plan/test_list.py` | Existing list tests (pattern reference) |
| `tests/commands/plan/test_view.py` | Existing view tests (pattern reference) |
| `tests/test_utils/context_builders.py` | `build_workspace_test_context()` |
| `tests/test_utils/env_helpers.py` | `erk_inmem_env()` |

## Conventions

- `--json-output` flag name (not `--json`) — matches `objective check`/`objective view`
- JSON to stdout via `click.echo(json.dumps(...))` — NOT `user_output()` (which goes to stderr)
- All dataclasses `@dataclass(frozen=True)`, no default parameter values
- Timestamps as ISO 8601 strings in business objects (not datetime)
- LBYL: `if row.pr_number is not None:` not try/except
- Absolute imports only

## Comparison Points vs Approach A (for Node 1.4)

| Dimension | Approach A | Approach B |
|-----------|-----------|-----------|
| Representations | 3 (PlanRowData + IR + rendered) | 2 (business objects + rendered) |
| JSON serialization | Custom dict builder functions | `dataclasses.asdict()` (zero custom code) |
| Human rendering uses same types as JSON? | No (human bypasses IR) | Yes (adapter takes business objects) |
| Adding a new field | 3 places (IR + JSON renderer + human renderer) | 2 places (business object + adapter; JSON is automatic) |
| Drift risk | IR and human renderer can diverge | Both paths forced through same objects |

## Verification

1. **Unit tests**: `pytest tests/unit/cli/commands/plan/test_business_objects.py tests/unit/cli/commands/plan/test_rich_adapter.py`
2. **CLI tests**: `pytest tests/commands/plan/test_list_json.py tests/commands/plan/test_view_json.py`
3. **Type check**: `ty check src/erk/cli/commands/plan/`
4. **Lint**: `ruff check src/erk/cli/commands/plan/`
5. **Manual smoke test**: `erk plan list --json-output | python -m json.tool` and `erk plan view 8088 --json-output | python -m json.tool`
6. **Existing tests still pass**: `pytest tests/commands/plan/test_list.py tests/commands/plan/test_view.py`
