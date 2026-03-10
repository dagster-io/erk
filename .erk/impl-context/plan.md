# Plan: Update Test Fixtures and Assertions for Renamed Fields and Types

**Part of Objective #9109, Node 4.1**

## Context

Objective #9109 renamed "plan" terminology to "pr" across all APIs (26/27 nodes complete). The source code renames are done: types like `PrRowData`, `PrStatus`, `PrNumberEvent`, `CommandResult` now use `pr_number`/`pr_id`/`pr_url`/`pr_title` fields. However, ~302 references across ~71 test files still use old `plan_number`/`plan_id`/`plan_url`/`plan_title` names in fixtures, assertions, and fake implementations.

## Scope

### RENAME these patterns in tests:
- **Dataclass field access**: `.plan_number` → `.pr_number`, `.plan_id` → `.pr_id`, `.plan_url` → `.pr_url`
- **Dict/JSON keys**: `"plan_number"` → `"pr_number"`, `"plan_id"` → `"pr_id"`, etc.
- **Constructor kwargs**: `plan_number=42` → `pr_number=42`, `plan_id="42"` → `pr_id="42"`
- **Fake gateway params**: `plan_numbers: list[int]` → `pr_numbers: list[int]` in fake implementations
- **Test function names**: `test_*_plan_number` → `test_*_pr_number` (where they test renamed fields)
- **Variable names tracking renamed fields**: `plan_num` → `pr_num` in fake gateway loops

### DO NOT RENAME:
- `extract_plan_number()` — intentionally kept in `src/erk/cli/commands/run/shared.py`
- `extract_learn_plan_number()` — intentionally kept in `src/erk/tui/operations/logic.py`
- `validate_plan_title()` — intentionally kept in `erk_shared/naming.py`
- `plan_duplicate_checker` JSON parsing of `"plan_id"` key from LLM output — this is the LLM's response format
- "plan" as a noun (erk-plan concept, plan body, plan content, etc.)
- Class names like `PlanListService`, `PlanMetadata` that weren't renamed in source

## Implementation Phases

### Phase 1: Fake Gateway Implementations (3 files)

These are the test infrastructure that other tests depend on. Fix first.

| File | Changes |
|------|---------|
| `tests/fakes/gateway/github.py` | `plan_numbers` params → `pr_numbers`, loop vars `plan_num` → `pr_num`, comments |
| `tests/fakes/gateway/github_issues.py` | `plan_number` param → `pr_number` in method signatures |
| `tests/fakes/gateway/shell.py` | `extraction_plan_url` → `extraction_pr_url` (5 refs) |

### Phase 2: Test Helper Utilities (1 file)

| File | Changes |
|------|---------|
| `tests/test_utils/plan_helpers.py` | `plan_identifier` comment, `plan_id` loop var → `pr_id` |

### Phase 3: Core Test Files (~15 files)

| File | Key Changes |
|------|-------------|
| `tests/core/test_prompt_executor.py` | `"plan_number"` dict keys → `"pr_number"` |
| `tests/core/test_impl_folder.py` | `plan_number=` kwargs, `plan_id=` kwargs (~17 refs) |
| `tests/core/test_impl_issue_wt_workflow.py` | `plan_id="42"` → `pr_id="42"` |
| `tests/core/test_plan_duplicate_checker.py` | JSON `"plan_id"` in assertion strings (careful: LLM output keys stay) |
| `tests/unit/sessions/test_manifest.py` | `"plan_id"` dict key and assertion |
| `tests/unit/status/test_impl_collector.py` | `plan_id="42"` → `pr_id="42"` |
| `tests/unit/shared/test_plan_workflow.py` | `.plan_number` → `.pr_number` assertions |
| `tests/unit/shared/test_next_steps.py` | Test function names referencing plan_number |
| `tests/unit/gateways/github/metadata_blocks/test_round_trip.py` | `plan_number=42` → `pr_number=42` |
| `tests/unit/gateways/github/metadata_blocks/test_plan_issue_schema.py` | `plan_number=123` → `pr_number=123` |
| `tests/unit/plan_store/test_plan_backend_interface.py` | `plan_id` params and assertions (~39 refs) |
| `tests/unit/plan_store/test_planned_pr_lifecycle.py` | `plan_id`/`plan_number` refs |
| `tests/unit/core/test_display_utils.py` | Single plan_number ref |
| `tests/packages/erk_shared/test_impl_context.py` | `plan_id` refs (~23 occurrences) |

### Phase 4: Command Test Files (~20 files)

| File | Key Changes |
|------|-------------|
| `tests/commands/pr/test_log.py` | `plan_number=42` → `pr_number=42` (~9 refs) |
| `tests/commands/pr/test_prepare.py` | Test function name |
| `tests/commands/pr/test_dispatch.py` | `inputs["plan_id"]` → `inputs["pr_id"]` |
| `tests/commands/pr/test_remote_paths.py` | JSON keys, assertion keys, test function name |
| `tests/commands/pr/test_close.py` | Test function name |
| `tests/commands/pr/test_duplicate_check.py` | JSON `"plan_id"` key |
| `tests/commands/pr/test_list.py` | plan_number refs |
| `tests/commands/pr/test_rewrite.py` | Single ref |
| `tests/commands/pr/test_check.py` | Single ref |
| `tests/commands/dispatch/conftest.py` | `plan_identifier` param |
| `tests/commands/dash/conftest.py` | plan_number refs |
| `tests/commands/implement/test_target_detection.py` | Test function names |
| `tests/commands/land/test_plan_issue_closure.py` | Comment ref |
| `tests/commands/land/test_get_objective_for_branch.py` | Comment ref |
| `tests/commands/land/test_learn_skip_remote.py` | plan_number refs |
| `tests/commands/test_reconcile.py` | Single ref |
| `tests/commands/test_dash_workflow_runs.py` | plan_number refs |
| `tests/commands/run/test_shared.py` | **DO NOT RENAME** — tests `extract_plan_number` which was kept |

### Phase 5: TUI Test Files (~5 files)

| File | Key Changes |
|------|-------------|
| `tests/tui/app/test_async_operations.py` | `plan_number=None` kwargs, `extract_learn_plan_number` import (**keep import name**) |
| `tests/tui/app/test_operation_tracking.py` | `plan_number=None` → `pr_number=None` |
| `tests/tui/app/test_plan_body_screen.py` | Test function name |
| `tests/tui/data/test_real_provider_runs.py` | Single ref |
| `tests/tui/data/test_provider.py` | plan_number refs |

### Phase 6: Exec Script Tests (~12 files)

| File | Key Changes |
|------|-------------|
| `tests/unit/cli/commands/exec/scripts/test_impl_init.py` | `"plan_id"` JSON keys |
| `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` | `plan_id` refs (~13 occurrences) |
| `tests/unit/cli/commands/exec/scripts/test_plan_update.py` | plan_number refs |
| `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py` | plan_id refs |
| `tests/unit/cli/commands/exec/scripts/test_get_plan_info.py` | plan_number refs (~10 occurrences) |
| `tests/unit/cli/commands/exec/scripts/test_get_plans_for_objective.py` | plan_id refs |
| `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` | plan_number refs |
| `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_pr.py` | plan_id refs |
| `tests/unit/cli/commands/exec/scripts/test_upload_impl_session.py` | plan_id refs |
| `tests/unit/cli/commands/exec/scripts/test_land_execute_objective_detection.py` | plan_number refs |
| `tests/unit/cli/commands/exec/scripts/test_update_pr_description.py` | Single ref |
| Various other exec script tests | Single refs each |

### Phase 7: Remaining Files

| File | Key Changes |
|------|-------------|
| `tests/unit/cli/commands/pr/test_dispatch_cmd.py` | plan_id refs |
| `tests/unit/cli/commands/pr/submit_pipeline/test_prepare_state.py` | plan_number refs (~8 occurrences) |
| `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` | plan_number refs |
| `tests/unit/cli/commands/pr/submit_pipeline/test_link_pr_to_objective_nodes.py` | Single ref |
| `tests/unit/cli/commands/pr/test_metadata_helpers.py` | plan_number refs |
| `tests/unit/cli/commands/land/test_land_learn.py` | plan_number refs |
| `tests/unit/cli/commands/land/pipeline/test_create_learn_issue.py` | plan_number refs |
| `tests/unit/cli/commands/land/pipeline/test_resolve_plan_id.py` | plan_id refs |
| `tests/unit/cli/commands/test_admin_test_workflow.py` | plan_number refs |
| `tests/unit/commands/wt/test_list_helpers.py` | Single ref |
| `tests/commands/workspace/test_delete.py` | Single ref |

## Approach

Use `rename-swarm` skill for mechanical bulk renames where patterns are clear (e.g., `plan_number=` → `pr_number=` as constructor kwargs). For files needing judgment (plan_duplicate_checker tests, run/test_shared.py), handle manually.

## Verification

1. Run `make fast-ci` — all unit tests pass
2. Run `ruff check` — no lint errors
3. Run `ty` — no type errors
4. Grep `tests/` for remaining `plan_number|plan_id|plan_url|plan_title` — only intentional references remain (extract_plan_number tests, LLM JSON format, plan-as-noun)
