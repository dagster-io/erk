# Plan: Objective #9109, Nodes 3.1–3.3 — Rename TUI Plan Types to PR

## Context

Objective #9109 renames "plan" terminology to "pr" across all APIs. Phases 1–2 are complete (gateway ABC, core types, JSON output, Click args, help strings, config). This plan covers Phase 3 nodes 3.1–3.3: renaming the TUI data layer types and provider.

**Key decision**: The user confirmed that `plan_id` and `pr_number` represent the same entity (the PR). We will **drop `plan_id`** entirely, widen `pr_number` from `int | None` to `int`, merge `plan_url` into `pr_url`, and rename `plan_body` → `pr_body`.

## Scope

### Node 3.1: Rename PlanRowData → PrRowData + field collapse

**Type definition** (`src/erk/tui/data/types.py`):
- Rename class `PlanRowData` → `PrRowData`
- Remove `plan_id: int` field — replace with `pr_number: int` (widen from `int | None`)
- Remove `plan_url: str | None` field — keep `pr_url: str | None` (absorbs plan_url's value)
- Rename `plan_body: str` → `pr_body: str`
- Rename `PlanFilters` → `PrFilters`
- Rename `serialize_plan_row()` → `serialize_pr_row()`
- Update `FetchTimings.plan_parsing_ms` → `pr_parsing_ms`
- Update all docstrings

**Consumers in src/erk/tui/** — update all `.plan_id` → `.pr_number`, `.plan_url` → `.pr_url`, `.plan_body` → `.pr_body` references:
- `app.py` — row.plan_id references
- `widgets/plan_table.py` — plan_id in keys, display, dedup
- `screens/plan_detail_screen.py` — plan_id in commands, display, close operations
- `screens/plan_body_screen.py` — plan_id parameter
- `screens/objective_nodes_screen.py` — plan_id references
- `actions/navigation.py` — plan_id, plan_url, plan_body references
- `actions/palette.py` — plan_id references
- `commands/registry.py` — plan_id in command strings
- `commands/types.py` — PlanRowData type reference
- `filtering/logic.py` — plan_id in search
- `sorting/logic.py` — plan_id in sort keys
- `operations/workers.py` — plan_id parameters (note: these are conceptual, the param name may stay as it refers to the row's identifier)

**Consumers in src/erk/cli/**:
- `commands/pr/list_cmd.py` — PlanRowData, PlanFilters, serialize_plan_row imports
- `commands/pr/view_cmd.py` — plan_id references
- `commands/pr/shared.py` — plan_id references
- `commands/pr/duplicate_check_cmd.py` — plan_id
- `commands/pr/submit_cmd.py` — plan_id
- `commands/pr/submit_pipeline.py` — plan_id
- `commands/pr/rewrite_cmd.py` — plan_id
- `commands/pr/dispatch_cmd.py` — plan_url
- `commands/reconcile_cmd.py` — plan_id
- `commands/reconcile_pipeline.py` — plan_id
- `commands/land_pipeline.py` — plan_id
- `commands/land_stack.py` — plan_id
- `commands/land_learn.py` — plan_id
- `commands/learn/learn_cmd.py` — plan_id
- `commands/exec/scripts/push_and_create_pr.py` — plan_id
- `commands/exec/scripts/get_pr_context.py` — plan_id
- `commands/exec/scripts/dash_data.py` — PlanRowData, PlanFilters, serialize_plan_row
- `core/commit_message_generator.py` — plan_id

**Other src/ consumers**:
- `packages/erk-shared/src/erk_shared/gateway/pr_service/abc.py` — PlanRowData reference
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/` — re-export shims

### Node 3.2: Rename PlanDataProvider → PrDataProvider

**ABC** (`src/erk/tui/data/provider_abc.py`):
- Rename class `PlanDataProvider` → `PrDataProvider`
- Rename methods: `fetch_plans()` → `fetch_prs()`, `fetch_plans_by_ids(plan_ids)` → `fetch_prs_by_ids(pr_ids)`, `fetch_plans_for_objective()` → `fetch_prs_for_objective()`
- Update `fetch_branch_activity(rows: list[PlanRowData])` → `fetch_branch_activity(rows: list[PrRowData])`
- Update return types and docstrings

**Re-export shim** (`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`):
- Update to re-export `PrDataProvider`

### Node 3.3: Update real_provider.py and fake_provider.py

**Real provider** (`src/erk/tui/data/real_provider.py`):
- Rename `RealPlanDataProvider` → `RealPrDataProvider`
- Update method signatures to match new ABC
- Rename internal variables: `worktree_by_plan_id` → `worktree_by_pr_number`, local `plan_id` vars → `pr_number`
- Collapse the data model in `_build_row_data()`: use `pr_number=plan_id` (the issue/PR number) as the primary `pr_number` field, merge `plan_url` into `pr_url`

**Test fake (tests layer)** (`tests/fakes/tests/tui_plan_data_provider.py`):
- Rename `FakePlanDataProvider` → `FakePrDataProvider`
- Update method signatures
- Rename `make_plan_row()` → `make_pr_row()`
- Update parameter: `plan_id` → `pr_number`, `plan_url` → `pr_url`, `plan_body` → `pr_body`
- Update all `.plan_id` → `.pr_number` references

**Gateway fake** (`tests/fakes/gateway/plan_data_provider.py`):
- Same renames as test fake
- Update `close_plan()` → `close_pr()` params: `plan_id` → `pr_number`, `plan_url` → `pr_url`
- Update `dispatch_to_queue()` params similarly
- Update `fetch_plan_content()` → `fetch_pr_content()` params
- Update `fetch_objective_content()` params
- Update `_plan_content_by_plan_id` → `_pr_content_by_pr_number`
- Update `_objective_content_by_plan_id` → `_objective_content_by_pr_number`

**Re-export shim** (`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`):
- Update to re-export new name

### Test files to update

- `tests/tui/test_plan_table.py` — PlanRowData, make_plan_row imports
- `tests/tui/data/test_provider.py` — FakePlanDataProvider, plan_id refs
- `tests/tui/filtering/test_logic.py` — plan_id refs
- `tests/tui/screens/test_objective_nodes_screen.py` — PlanRowData refs
- `tests/tui/screens/test_objective_plans_fake_provider.py` — plan_id refs
- `tests/tui/commands/test_execute_command.py` — PlanRowData refs
- `tests/tui/app/test_view_switching.py` — plan_id refs
- `tests/tui/app/test_app_filtering.py` — plan_id refs
- `tests/tui/app/test_filter_mode.py` — plan_id refs
- `tests/tui/app/test_core.py` — PlanFilters, PlanDataProvider refs
- `tests/tui/app/test_actions.py` — refs
- `tests/tui/app/test_plan_detail_screen.py` — refs
- `tests/tui/app/test_plan_body_screen.py` — refs
- `tests/tui/app/test_command_palette.py` — refs
- `tests/tui/app/test_streaming.py` — refs
- `tests/tui/app/test_one_shot_prompt.py` — refs
- `tests/tui/app/test_operation_tracking.py` — refs
- `tests/tui/app/test_async_operations.py` — refs
- `tests/tui/app/test_incremental_dispatch.py` — refs
- `tests/tui/app/test_app_runs.py` — refs
- `tests/tui/data/test_real_provider_runs.py` — refs
- `tests/tui/screens/test_check_runs_screen.py` — refs
- `tests/tui/test_run_table.py` — PlanFilters refs
- `tests/unit/cli/commands/pr/submit_pipeline/` — plan_id refs
- `tests/unit/cli/commands/land/` — plan_id refs
- `tests/unit/cli/commands/exec/scripts/test_dash_data.py` — serialize_plan_row, PlanRowData
- `tests/core/test_plan_duplicate_checker.py` — plan_id refs
- `tests/core/test_plan_context_provider.py` — plan_id refs
- `tests/erk_shared/gateway/plan_data_provider/test_real_routing.py` — PlanDataProvider refs

## Implementation Strategy

Use `libcst-refactor` agent for batch Python identifier renames (class names, field names, variable names, method names). Follow up with manual grep for string literals (dict keys, display strings) that LibCST won't catch.

### Step 1: LibCST batch rename — types and class names
- `PlanRowData` → `PrRowData` (all files)
- `PlanFilters` → `PrFilters` (all files)
- `PlanDataProvider` → `PrDataProvider` (all files)
- `RealPlanDataProvider` → `RealPrDataProvider` (all files)
- `FakePlanDataProvider` → `FakePrDataProvider` (all files)
- `serialize_plan_row` → `serialize_pr_row` (all files)
- `make_plan_row` → `make_pr_row` (all files)
- `plan_parsing_ms` → `pr_parsing_ms` (all files)

### Step 2: LibCST batch rename — field/param/method names
- `.plan_id` → `.pr_number` (attribute access)
- `.plan_url` → `.pr_url` (attribute access — but must handle the existing `pr_url` field)
- `.plan_body` → `.pr_body` (attribute access)
- `fetch_plans` → `fetch_prs` (method name)
- `fetch_plans_by_ids` → `fetch_prs_by_ids` (method name)
- `fetch_plans_for_objective` → `fetch_prs_for_objective` (method name)
- `plan_ids` parameter → `pr_ids`
- `worktree_by_plan_id` → `worktree_by_pr_number`

### Step 3: Manual field collapse in PrRowData
In `src/erk/tui/data/types.py`:
- Remove the `plan_id: int` field declaration
- Change `pr_number: int | None` → `pr_number: int` (field already exists, just widen)
- Remove `plan_url: str | None` — the existing `pr_url: str | None` absorbs it
- Rename `plan_body: str` → `pr_body: str`

### Step 4: Update _build_row_data() in real_provider.py
- The current code sets `plan_id=plan_id` and `pr_number=pr_number` (from linked PR). After collapse, set `pr_number=plan_id` (the issue/PR number). The linked PR data (`pr_display`, `pr_title`, `pr_state`, `pr_head_branch`, `pr_url`) stays as-is since they describe the same entity.

### Step 5: Update make_pr_row() helpers
- Both in `tests/fakes/tests/tui_plan_data_provider.py` and `tests/fakes/gateway/plan_data_provider.py`
- Remove `plan_id` positional param, add `pr_number: int` as first positional
- Remove `plan_url` param, use `pr_url` for the URL
- Rename `plan_body` → `pr_body`

### Step 6: Post-rename grep sweep
- Grep for `plan_id`, `plan_url`, `plan_body`, `PlanRowData`, `PlanFilters`, `PlanDataProvider`, `make_plan_row`, `serialize_plan_row`, `plan_parsing_ms` in all Python files
- Fix any remaining string literals, dict keys, comments

### Step 7: Update documentation
- `src/erk/tui/AGENTS.md` — update type names and field references
- `docs/learned/tui/` — update references in architecture.md, plan-row-data.md, tripwires.md, data-contract.md, etc.
- Note: docs/learned updates are technically node 4.3, but we should fix TUI-specific docs that would be broken

## Verification

1. Run type checker: `make ty` — catches type mismatches from field changes
2. Run TUI tests: `uv run pytest tests/tui/ -x`
3. Run CLI command tests: `uv run pytest tests/unit/cli/ -x`
4. Run core tests: `uv run pytest tests/core/ -x`
5. Run erk-shared tests: `uv run pytest tests/erk_shared/ -x`
6. Grep for remaining `plan_id`, `PlanRowData`, `PlanDataProvider` in Python files
7. Run full CI: `make fast-ci`
