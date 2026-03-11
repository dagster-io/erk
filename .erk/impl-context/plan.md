# Plan: Deterministic planning run ID from structured metadata

## Context

The TUI dashboard shows a "planning run ID" for plans created by GitHub Actions workflows. Currently, for plans without a dispatched workflow run, the run ID is extracted by **parsing the URL** from `created_from_workflow_run_url` — splitting by "/" and checking if the last segment is a digit (`real_provider.py:667-676`). This is fragile and non-deterministic. We should store the run ID as a first-class structured field and read it directly.

## Approach

Add a `created_from_workflow_run_id` field to the plan header schema. The workflows already have `github.run_id` available — we'll pass it as a separate env var and CLI flag alongside the existing URL. The TUI reads the ID field directly instead of parsing the URL.

## Changes

### 1. Schema: Add `CREATED_FROM_WORKFLOW_RUN_ID` field

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

- Add `"created_from_workflow_run_id"` to `PlanHeaderFieldName` Literal union
- Add `CREATED_FROM_WORKFLOW_RUN_ID: Literal["created_from_workflow_run_id"] = "created_from_workflow_run_id"` constant
- Add `CREATED_FROM_WORKFLOW_RUN_ID` to `PlanHeaderSchema.validate()` `optional_fields` set

### 2. Plan header: Thread new field through creation functions

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py`

- Add `created_from_workflow_run_id: str | None` parameter to `create_plan_header_block()`
- Add `created_from_workflow_run_id: str | None` parameter to `format_plan_header_body()`
- Store in data dict (same pattern as `created_from_workflow_run_url`)
- Add import of `CREATED_FROM_WORKFLOW_RUN_ID`

### 3. CLI: Add `--created-from-workflow-run-id` option to plan-save

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py`

- Add `--created-from-workflow-run-id` Click option
- Pass through to metadata dict alongside the URL

### 4. TUI: Read structured field instead of URL parsing

**File:** `src/erk/tui/data/real_provider.py`

- Import `CREATED_FROM_WORKFLOW_RUN_ID`
- Replace URL-parsing fallback (lines 667-676) with direct read of `created_from_workflow_run_id`
- Still use `created_from_workflow_run_url` for the `run_url` link

### 5. Workflows: Pass `WORKFLOW_RUN_ID` env var

**Files:**
- `.github/workflows/one-shot.yml` — add `WORKFLOW_RUN_ID: ${{ github.run_id }}` to planning step env
- `.github/workflows/learn.yml` — add `WORKFLOW_RUN_ID: ${{ github.run_id }}` to learn step env

### 6. Commands: Pass `--created-from-workflow-run-id`

**Files:**
- `.claude/commands/erk/system/one-shot-plan.md` — add `--created-from-workflow-run-id "$WORKFLOW_RUN_ID"` to plan-save invocation
- `.claude/commands/erk/learn.md` — add `--created-from-workflow-run-id "$WORKFLOW_RUN_ID"` alongside the URL flag

### 7. Other callers of `format_plan_header_body` / `create_plan_header_block`

These callers need the new parameter added (as `None`):
- `src/erk/cli/commands/pr/create_cmd.py`
- `src/erk/cli/commands/one_shot_remote_dispatch.py`
- `src/erk/cli/commands/land_learn.py`
- `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`
- `src/erk/cli/commands/exec/scripts/create_pr_from_session.py`
- `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py`

### 8. Tests

**File:** `tests/test_utils/plan_helpers.py`
- Add `created_from_workflow_run_id: str | None = None` to `format_plan_header_body_for_test()`

**File:** `tests/tui/data/test_provider.py`
- Update `TestPlanningRunIdFallback` to use `created_from_workflow_run_id` field
- Rename class to reflect it's no longer a "fallback"
- Test: plan with `created_from_workflow_run_id` shows it directly
- Test: plan with only URL but no ID still shows "-" (no URL parsing fallback)
- Test: dispatched run still takes precedence

**File:** `tests/unit/gateways/github/metadata_blocks/test_round_trip.py`
- Add round-trip test for the new field

## Verification

1. Run `uv run pytest tests/tui/data/test_provider.py -x` — TUI provider tests pass
2. Run `uv run pytest tests/unit/gateways/github/metadata_blocks/ -x` — metadata round-trip tests pass
3. Run `uv run pytest tests/test_utils/ -x` — plan helpers still work
4. Run ty and ruff checks
