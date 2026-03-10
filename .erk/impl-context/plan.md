# Plan: Sweep plan_id/plan_url/plan_title refs in submit pipeline, dispatch, and PlanContext

**Objective:** #9109, Node 3.6.2
**Scope:** Rename `plan_id`, `plan_url`, and `plan_title` field/parameter/variable names in the submit pipeline, dispatch infrastructure, PlanContext, and their direct consumers.

## Context

Part of the "plan → pr" terminology rename (objective #9109). Node 3.6.1 (in progress, #9178) covers land pipeline, implement, and core modules. This node covers the submit pipeline, dispatch command, and PlanContext — the other major cluster of `plan_*` identifiers.

**Out of scope:**
- `erk_shared` package functions (`build_impl_context_files(plan_id=)`, `save_plan_ref(plan_id=)`) — cross-package API, separate rename
- Workflow YAML input keys (`plan_id`, `plan_title` in `.github/workflows/`) — CI scope, must stay in sync with Python dict keys
- Exec scripts (node 3.6.3), land pipeline (node 3.6.1), test-only changes beyond CI green (node 4.1)

## Rename Mapping

| Current | New | Type | Rationale |
|---------|-----|------|-----------|
| `PlanContext.plan_id` | `PlanContext.pr_id` | field (str) | Core type, avoids name collision |
| `SubmitState.plan_id` | `SubmitState.pr_id` | field (str\|None) | Direct rename |
| `DispatchResult.plan_title` | `DispatchResult.pr_title` | field (str) | Direct rename |
| `DispatchResult.plan_url` | `DispatchResult.pr_url` | field (str) | Direct rename |
| `_build_workflow_run_url(plan_url=)` | `_build_workflow_run_url(pr_url=)` | parameter | Direct rename |
| `_build_pr_url(plan_url=)` | `_build_pr_url(pr_url=)` | parameter | Direct rename |
| `maybe_advance_lifecycle_to_impl(plan_id=)` | `maybe_advance_lifecycle_to_impl(pr_id=)` | parameter | Direct rename |
| `recover_plan_header(plan_id=)` | `recover_plan_header(pr_id=)` | parameter | Direct rename |
| `_detect_plan_number_from_context()` | `_detect_pr_number_from_context()` | function name | Direct rename |
| Local `plan_id` variables | `pr_id` | local vars | Throughout all in-scope files |
| Local `plan_url` variables | `pr_url` | local vars | In submit_pipeline.py |
| Local `plan_id_for_lifecycle` | `pr_id_for_lifecycle` | local var | In submit_pipeline.py:879 |

**Keep as-is (workflow contract):**
- Dict keys `"plan_id"`, `"plan_title"` in dispatch_cmd.py workflow input dicts (lines 287, 289, 514, 516) — must match GitHub Actions YAML inputs
- `build_impl_context_files(plan_id=)` and `save_plan_ref(plan_id=)` kwargs — erk_shared API

## Source Files (6 files)

### Phase 1: Type definitions (2 files)

**1. `src/erk/core/plan_context_provider.py`** (3 occurrences)
- Rename `PlanContext.plan_id` field → `pr_id`
- Update docstring (line 21) and constructor call (line 73: `plan_id=result.pr_identifier` → `pr_id=result.pr_identifier`)

**2. `src/erk/cli/commands/pr/dispatch_cmd.py`** (~25 occurrences)
- Rename `DispatchResult.plan_title` → `pr_title`, `DispatchResult.plan_url` → `pr_url` (lines 92-93)
- Rename functions: `_build_workflow_run_url(plan_url)` → `(pr_url)`, `_build_pr_url(plan_url)` → `(pr_url)` (lines 100, 117)
- Rename function `_detect_plan_number_from_context` → `_detect_pr_number_from_context` (line 596)
- Rename local `plan_id` → `pr_id` in `_detect_pr_number_from_context` (lines 622-624)
- Update constructor calls: `plan_title=validated.title` → `pr_title=`, `plan_url=validated.url` → `pr_url=` (lines 374-375, 587-588)
- Update output strings: `r.plan_title` → `r.pr_title`, `r.plan_url` → `r.pr_url` (lines 837-838)
- **Keep** dict keys `"plan_id"`, `"plan_title"` (lines 287, 289, 514, 516) — workflow input contract
- **Keep** `build_impl_context_files(plan_id=str(pr_number))` (lines 243, 489) — erk_shared API

### Phase 2: Consumer modules (4 files)

**3. `src/erk/cli/commands/pr/submit_pipeline.py`** (~19 occurrences)
- Rename `SubmitState.plan_id` field → `pr_id` (line 104)
- Rename all local `plan_id` → `pr_id` in `prepare_state()` (lines 161, 164, 174, 205)
- Rename local `plan_url` → `pr_url` (line 177)
- Update `state.plan_id` → `state.pr_id` references (lines 278, 567)
- Update `state.plan_context.plan_id` → `state.plan_context.pr_id` (lines 819, 881)
- Rename `plan_id_for_lifecycle` → `pr_id_for_lifecycle` (lines 879-889)
- Update initial state: `plan_id=None` → `pr_id=None` (line 1108)
- **Keep** `save_plan_ref(plan_id=plan_id)` kwarg name (line 181) — erk_shared API; update value: `plan_id=pr_id`

**4. `src/erk/cli/commands/pr/shared.py`** (7 occurrences)
- Rename parameters: `maybe_advance_lifecycle_to_impl(plan_id:)` → `pr_id:` (line 150), `recover_plan_header(plan_id:)` → `pr_id:` (line 190)
- Update all `plan_id` → `pr_id` in function bodies (lines 161, 170, 201)
- Update `plan_context.plan_id` → `plan_context.pr_id` (lines 128, 248)

**5. `src/erk/core/commit_message_generator.py`** (1 occurrence)
- Update template string: `plan_context.plan_id` → `plan_context.pr_id` (line 217)

**6. `src/erk/cli/commands/pr/metadata_helpers.py`** (3 occurrences)
- Local `plan_id = str(plan_number)` → `pr_id = str(plan_number)` (line 43)
- Update calls: `plan_backend.get_plan(repo_root, plan_id)` → `...pr_id` (line 44)
- Update all `plan_id` → `pr_id` in both functions (lines 43-51, 85-104)
- Note: `plan_number` parameter on line 29 stays — it's a Click param renamed in node 2.3

## Test Files (~18 files)

### Submit pipeline tests (15 files)
All files in `tests/unit/cli/commands/pr/submit_pipeline/` that construct `SubmitState` with `plan_id=`:
- test_prepare_state.py — `plan_id=`, `result.plan_id` assertions (~8 places)
- test_finalize_pr.py — `plan_id=` kwargs (~5 places)
- test_graphite_first_flow.py — `plan_id=` kwargs (~4 places)
- test_label_code_pr.py — `plan_id=` kwargs (~2 places)
- test_link_pr_to_objective_nodes.py — `plan_id=` kwargs (~2 places)
- test_run_pipeline.py — `state.plan_id` assertion
- test_cleanup_impl_for_submit.py, test_commit_wip.py, test_core_submit_flow.py, test_enhance_with_graphite.py, test_extract_diff.py, test_extract_diff_and_fetch_plan_context.py, test_fetch_plan_context.py, test_generate_description.py, test_capture_existing_pr_body.py — `plan_id=` in `_make_state()` helpers

### PlanContext tests (3 files)
- `tests/core/test_plan_context_provider.py` — `plan_id=` in PlanContext construction, `.plan_id` assertions
- `tests/unit/cli/commands/pr/test_shared.py` — `plan_id=` in PlanContext + `recover_plan_header(plan_id=)`
- `tests/core/test_commit_message_generator.py` — `plan_id=` in PlanContext construction

## Key Decisions

1. **Workflow input dict keys stay as-is**: `"plan_id"` and `"plan_title"` in dispatch_cmd.py must match `.github/workflows/plan-implement.yml` YAML inputs. Renaming both sides is CI scope.
2. **erk_shared kwarg names stay as-is**: `build_impl_context_files(plan_id=)` and `save_plan_ref(plan_id=)` are cross-package APIs in `packages/erk-shared/`. Only update the value variable names.
3. **`PlanContext.plan_id` → `pr_id`**: Consistent with `LandState.pr_id` from node 3.6.1.
4. **`DispatchResult` fields**: `plan_title` → `pr_title`, `plan_url` → `pr_url` — straightforward.

## Implementation Order

1. `plan_context_provider.py` — PlanContext.plan_id field (ripple effects everywhere)
2. `dispatch_cmd.py` — DispatchResult fields + function renames
3. `submit_pipeline.py` — SubmitState.plan_id + all consumers
4. `shared.py` — function parameters + plan_context.plan_id usage
5. `commit_message_generator.py` — template string
6. `metadata_helpers.py` — local variables
7. All test files — update kwargs and assertions
8. Verify with CI

## Verification

1. **Unit tests**: `make fast-ci` (runs ruff, ty, unit tests)
2. **Grep check**: Search for remaining `plan_id`, `plan_url`, `plan_title` in the 6 source files (excluding expected workflow dict keys and erk_shared kwargs)
3. **Full CI**: `make all-ci` for integration tests
