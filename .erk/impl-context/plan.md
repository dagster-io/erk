# Plan: Remove `erk-plan` label, rename `erk-core` → `erk-core-pr`, `erk-learn` → `erk-learn-pr`

Supersedes plan #9135.

## Context

With `erk-core` in place, the `erk-plan` label is redundant — plan-specific identification can use the `[erk-plan]` title prefix instead. Additionally, renaming `erk-core` → `erk-core-pr` and `erk-learn` → `erk-learn-pr` improves clarity by making it obvious these labels apply to PRs.

Final label scheme: `erk-pr`, `erk-core-pr`, `erk-learn-pr` (plus `erk-objective`, `erk-consolidated`, `erk-skip-learn` unchanged).

## Part 1: Remove `erk-plan` label

(Same as plan #9135 — see that plan for full details)

### 1a. Remove constant and definition
- `src/erk/cli/constants.py`: Remove `ERK_PLAN_LABEL`
- `packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py`: Remove `_LABEL_ERK_PLAN*` from definitions, `_ensure_labels_exist()`, `get_erk_label_definitions()`, `get_required_erk_labels()`

### 1b. Stop applying label (5 files)
- `src/erk/cli/commands/execute/scripts/plan_save.py`
- `src/erk/cli/commands/pr/create_cmd.py`
- `src/erk/cli/commands/one_shot_remote_dispatch.py`
- `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`
- `src/erk/cli/commands/exec/scripts/create_pr_from_session.py`

### 1c. Replace validation (4 files) — label check → title prefix check
- `packages/erk-shared/src/erk_shared/plan_workflow.py`
- `src/erk/cli/commands/pr/dispatch_cmd.py`
- `src/erk/cli/commands/implement.py`
- `src/erk/cli/commands/exec/scripts/objective_plan_setup.py`

### 1d. Replace query filters (5 files) — `["erk-pr", "erk-plan"]` → `["erk-core-pr"]` with client-side title filter where needed
- `src/erk/cli/commands/exec/scripts/get_plans_for_objective.py`
- `src/erk/cli/commands/wt/delete_cmd.py`
- `src/erk/cli/commands/run/list_cmd.py`
- `src/erk/cli/commands/pr/duplicate_check_cmd.py`
- `src/erk/tui/data/types.py`

### 1e. Keep as-is
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/types.py` — `BlockKeys.ERK_PLAN` is metadata, not a label
- `packages/erk-shared/src/erk_shared/plan_utils.py` — `get_title_tag()` returns `"[erk-plan]"` title prefix, not label

## Part 2: Rename `erk-core` → `erk-core-pr`

### 2a. Constants
- `src/erk/cli/constants.py`: `ERK_CORE_LABEL = "erk-core"` → `"erk-core-pr"`
- `packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py`: `_LABEL_ERK_CORE = "erk-core"` → `"erk-core-pr"`, update description

### 2b. Source files using `ERK_CORE_LABEL` or `"erk-core"` string
- `src/erk/cli/commands/pr/submit_pipeline.py` (line 576)
- `src/erk/cli/commands/pr/list_cmd.py` (lines 281, 400)
- `src/erk/cli/commands/pr/create_cmd.py` (line 80)
- `src/erk/cli/commands/exec/scripts/plan_save.py` (line 298)
- `src/erk/cli/commands/exec/scripts/create_pr_from_session.py` (line 105)
- `src/erk/cli/commands/exec/scripts/dash_data.py` (line 30)
- `src/erk/cli/commands/one_shot_remote_dispatch.py` (line 394)
- `src/erk/tui/views/types.py` (line 41)

### 2c. Tests referencing `"erk-core"`
Mechanical find-and-replace `"erk-core"` → `"erk-core-pr"` across:
- `tests/commands/test_dash_workflow_runs.py`
- `tests/commands/dash/test_filtering.py`
- `tests/commands/dash/test_workflow_run_state.py`
- `tests/commands/dash/test_pr_columns.py`
- `tests/commands/dash/test_action_state.py`
- `tests/commands/dash/test_impl_columns.py`
- `tests/commands/one_shot/test_one_shot_dispatch.py`
- `tests/commands/one_shot/test_one_shot_remote_dispatch.py`
- `tests/commands/pr/test_remote_paths.py`
- `tests/commands/pr/test_list.py`
- `tests/unit/core/test_health_checks_plans_repo_labels.py`
- `tests/unit/core/test_workflow_smoke_test.py`
- `tests/unit/objective_issues/test_label_definitions.py`
- `tests/unit/cli/commands/init/test_create_plans_repo_labels.py`
- `tests/unit/cli/commands/pr/submit_pipeline/test_label_code_pr.py`
- `tests/tui/views/test_types.py`

## Part 3: Rename `erk-learn` → `erk-learn-pr`

### 3a. Constants
- `src/erk/cli/constants.py`: `ERK_LEARN_LABEL = "erk-learn"` → `"erk-learn-pr"`
- `packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py`: `_LABEL_ERK_LEARN = "erk-learn"` → `"erk-learn-pr"`

### 3b. Source files using `"erk-learn"` string
- `src/erk/cli/commands/exec/scripts/plan_save.py` (line 295)
- `src/erk/cli/commands/consolidate_learn_plans_dispatch.py` (line 195)
- `src/erk/cli/commands/land_learn.py` (lines 231, 273)
- `packages/erk-shared/src/erk_shared/gateway/gt/operations/finalize.py` (line 32)
- `packages/erk-shared/src/erk_shared/plan_utils.py` (line 190)
- `src/erk/tui/views/types.py` (line 49)
- `src/erk/tui/data/real_provider.py` (line 728)

### 3c. Title prefix — keep `[erk-learn]` as-is?
The title prefix `[erk-learn]` in `plan_utils.py:get_title_tag()` is a display artifact, not a label. **Keep as-is** — changing it would require updating all existing PR titles on GitHub.

### 3d. Tests referencing `"erk-learn"`
Mechanical find-and-replace across:
- `tests/commands/consolidate_learn_plans/test_dispatch.py`
- `tests/unit/cli/commands/exec/scripts/test_plan_update.py`
- `tests/unit/cli/commands/land/test_land_learn.py`
- `packages/erk-shared/tests/unit/integrations/gt/operations/test_finalize.py`
- `tests/unit/objective_issues/test_label_definitions.py`
- `tests/unit/services/test_plan_list_service_http.py`
- `tests/tui/views/test_types.py`
- `tests/tui/app/test_view_switching.py`
- `tests/erk_shared/gateway/plan_data_provider/test_real_routing.py`
- `tests/unit/cli/commands/init/test_create_plans_repo_labels.py`
- `tests/unit/cli/commands/exec/scripts/test_add_plan_labels.py`
- `tests/unit/plan_store/test_planned_pr_backend.py`
- `tests/core/test_impl_folder.py`
- `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`
- `packages/erk-shared/tests/unit/github/test_objective_issues.py`

## Part 4: Update documentation

- `docs/learned/planning/label-scheme.md`: Update taxonomy table, assignment rules, query labels
- `src/erk/cli/commands/init/main.py`: Update user-facing label setup messages
- Various `.claude/commands/` files that mention label names in documentation
- `AGENTS.md` / skill docs that reference label names

## Part 5: NOT changed

- `erk-pr` label — unchanged
- `erk-objective`, `erk-consolidated`, `erk-skip-learn` — unchanged
- `[erk-plan]` / `[erk-learn]` title prefixes — unchanged (display only)
- `BlockKeys.ERK_PLAN` metadata key — unchanged (metadata, not a label)

## Verification

1. `make fast-ci` — unit tests pass
2. `make all-ci` — integration tests pass
3. `erk dash` shows plans correctly with new label queries
4. Plan creation applies correct labels (`erk-pr` + `erk-core-pr`)
5. Learn plan creation applies correct labels (`erk-pr` + `erk-learn-pr`)
6. `erk pr dispatch <plan>` validates by title prefix, not label
