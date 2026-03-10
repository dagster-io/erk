# Plan: Sweep remaining plan_number/plan_id references in src/

**Part of Objective #9109, Node 3.6**

## Context

Objective #9109 renames "plan" terminology to "pr" across all APIs. Phases 1-2 are complete (PRs #9110, #9120, #9130, #9140, #9144, #9146 merged). Phase 3 nodes 3.1-3.5 are in progress (#9152 covers TUI layer). Node 3.6 sweeps for any remaining `plan_number`, `plan_id`, `plan_url`, `plan_title` references in `src/erk/` that should have been renamed.

**Key distinction**: Only rename fields/params where "plan_number" means "the PR number of an erk-plan". Do NOT rename conceptual references to "plan" (plan mode, plan files, plan save workflow, plan labels).

## Scope

86 files in `src/erk/` still contain `plan_number|plan_id|plan_url|plan_title`. After excluding TUI files (covered by #9152), ~70 files remain. Many are intentional (plan-as-concept). The sweep must categorize each and rename only the "PR identifier" uses.

## Rename Rules

| Old | New | When to rename |
|-----|-----|----------------|
| `plan_number` (param/field) | `pr_number` | When it holds a GitHub issue/PR number |
| `plan_id` (param/field) | `pr_id` | When it's a string plan identifier (resolves to PR number) |
| `plan_url` (param/field) | `pr_url` | When it holds a GitHub URL |
| `plan_title` (param/field) | `pr_title` | When it holds a PR/issue title |
| `"plan_number"` (string literal) | `"pr_number"` | Target type discriminators |
| `"plan_url"` (string literal) | `"pr_url"` | Target type discriminators |

**DO NOT rename:**
- File/module names (e.g., `plan_save.py`, `plan_context_provider.py`)
- Class names for plan concepts (`PlanContext`, `PlanValidationSuccess`)
- Functions operating on plan.md files (`extract_plan_title()` in exit_plan_mode_hook.py)
- Plan label operations (`add_plan_label`, `add_plan_labels`)
- Schema migration code that intentionally references old field names
- Comments explaining plan concepts (not field names)

## Implementation Phases

### Phase A: Core pipeline files (highest impact)

These files have dataclass fields and function signatures that propagate through the codebase:

1. **`src/erk/cli/commands/implement_shared.py`**
   - `TargetInfo.plan_number` -> `pr_number`
   - `target_type="plan_number"` -> `"pr_number"` string literal
   - `target_type="plan_url"` -> `"pr_url"` string literal
   - Update docstring

2. **`src/erk/cli/commands/land_pipeline.py`**
   - `LandState.plan_id` -> `pr_id`
   - `resolve_plan_id()` -> `resolve_pr_id()`
   - All internal references to `state.plan_id` -> `state.pr_id`

3. **`src/erk/cli/commands/pr/submit_pipeline.py`**
   - `SubmitState.plan_id` (line 104) -> `pr_id`
   - `plan_id` in workflow dispatch dicts (lines 287, 489, 514)
   - `plan_title` in dispatch dicts (lines 289, 516)
   - `_detect_plan_number_from_context()` -> `_detect_pr_number_from_context()`
   - `plan_url` in DispatchResult construction (lines 177, 182)

4. **`src/erk/cli/commands/pr/dispatch_cmd.py`**
   - `DispatchContext.plan_title` -> `pr_title`
   - `DispatchContext.plan_url` -> `pr_url`
   - `_build_workflow_run_url(plan_url=...)` -> `pr_url`
   - `_build_pr_url(plan_url=...)` -> `pr_url`
   - Dispatch dict keys `"plan_id"`, `"plan_title"` -> `"pr_number"`, `"pr_title"`

### Phase B: Command files

5. **`src/erk/cli/commands/implement.py`**
   - `plan_number` parameter (line 137) -> `pr_number`
   - `target_info.plan_number` references -> `pr_number`
   - String `"plan_number"` / `"plan_url"` target type checks (lines 451, 457)

6. **`src/erk/cli/commands/land_cmd.py`**
   - `plan_id` local variables -> `pr_id`
   - `plan_number=int(plan_id)` -> `pr_number=int(pr_id)` (line 1098)

7. **`src/erk/cli/commands/objective_helpers.py`**
   - `plan_number` variable -> `pr_number` (lines 38, 42, 46, 51)
   - `plan_number: int` parameter (line 79) -> `pr_number`
   - `plan_id` from resolve call (line 34) -> `pr_id`

8. **`src/erk/cli/commands/exit_plan_mode_hook.py`**
   - `HookInput.plan_saved_plan_number` -> `saved_pr_number`
   - `HookInput.plan_number` -> `pr_number`
   - `HookInput.plan_title` -> `pr_title` (but only if it means PR title, not plan.md title)
   - `extract_plan_title()` - KEEP (extracts from plan.md file)

### Phase C: Exec scripts

9. **Exec scripts using `plan_id`/`plan_number` as PR identifiers** - sweep each:
   - `plan_save.py`, `push_and_create_pr.py`, `close_pr.py`, `close_prs.py`
   - `incremental_dispatch.py`, `post_workflow_started_comment.py`
   - `land_execute.py`, `setup_impl.py`, `setup_impl_from_pr.py`
   - `get_plan_info.py`, `get_plan_metadata.py`, `get_pr_for_plan.py`
   - `upload_impl_session.py`, `impl_init.py`
   - `detect_plan_from_branch.py`, `register_one_shot_plan.py`
   - For each: rename `plan_id`/`plan_number` params/variables that represent PR numbers

### Phase D: Remaining files

10. **Other CLI commands:**
    - `land_learn.py`, `land_stack.py`, `reconcile_cmd.py`, `reconcile_pipeline.py`
    - `one_shot_remote_dispatch.py`, `one_shot/cli.py`
    - `consolidate_learn_plans_dispatch.py`
    - `branch/checkout_cmd.py`, `branch/create_cmd.py`
    - `wt/delete_cmd.py`, `wt/create_cmd.py`
    - `pr/` subcommands: `shared.py`, `close_cmd.py`, `checkout_cmd.py`, `log_cmd.py`, `check_cmd.py`, `rewrite_cmd.py`, `metadata_helpers.py`, `submit_cmd.py`, `view/operation.py`, `view/cli.py`, `list/cli.py`

11. **Core modules:**
    - `github_parsing.py`: `parse_plan_number_from_url` usage
    - `core/plan_context_provider.py`: field renames inside PlanContext class
    - `core/commit_message_generator.py`
    - `core/file_utils.py`
    - `admin.py`
    - `learn/learn_cmd.py`

### Phase E: Workflow dispatch dict keys

Many exec scripts and dispatch commands emit JSON with `"plan_id"`, `"plan_number"`, `"plan_title"` keys. These are consumed by GitHub Actions workflows and Claude commands/skills. Changes here require coordinating with:
- `.github/workflows/` (already covered by node 4.x PRs)
- `.claude/commands/` and `.claude/skills/` (covered by node 4.2-4.3)

**Strategy**: Rename the dict keys in src/ now. Workflow/skill consumers will be updated in Phase 4 nodes.

## Files to modify

~50-60 files in `src/erk/cli/` and `src/erk/core/` (excluding `src/erk/tui/` which is handled by #9152).

## Verification

1. Run `ruff check src/` - no lint errors
2. Run `ty check src/` - no type errors
3. Run `pytest tests/unit/ -x` - all unit tests pass
4. Run `pytest tests/integration/ -x` - all integration tests pass
5. Grep sweep: `grep -r "plan_number\|plan_id\b\|plan_url\|plan_title" src/erk/ --include="*.py"` should only show:
   - TUI files (covered by #9152)
   - Intentional plan-concept references (plan mode, plan files, plan labels)
   - Schema migration backwards-compat code
