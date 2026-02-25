# Plan: Simplify Learn Trigger in `erk land`

## Context

The async learn pipeline triggered by `erk land` is complex and fragile: session discovery → preprocessing → gist upload → branch creation → CI workflow dispatch → multi-agent analysis → plan-save → track-learn-result metadata. This caused 14 learn PRs to get auto-closed due to ephemeral base branch stacking, and metadata tracking consistently fails due to missing required fields.

The replan flow (`/local:replan-learn-plans` → `/erk:replan`) already exists and can consolidate/reprocess learn plan issues. We simplify by having `erk land` create a learn issue directly with preprocessed sessions, then relying on replan for analysis.

## New Flow

1. `erk land` merges the PR
2. If plan branch and not a learn plan: preprocess local sessions, create learn issue with `erk-learn` label
3. Replan flow (`/local:replan-learn-plans`) processes issues in batch

No CI workflow. No gist upload. No metadata tracking back to source plan. No interactive 4-option menu.

## Changes

### 1. Replace `check_learn_status` validation step with config-only check

**File**: `src/erk/cli/commands/land_pipeline.py`

Replace the `check_learn_status` step (lines 331-349) with a lightweight step that only resolves `plan_id` (needed for the execution step). Remove the call to `_check_learn_status_and_prompt` entirely — no more interactive prompt during validation.

```python
def resolve_plan_id(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Resolve plan ID for branch (used by create_learn_issue)."""
    plan_id = ctx.plan_backend.resolve_plan_id_for_branch(state.main_repo_root, state.branch)
    return dataclasses.replace(state, plan_id=plan_id)
```

Update `_validation_pipeline()` (line 491-498): replace `check_learn_status` with `resolve_plan_id`.

### 2. Replace `update_learn_plan` execution step with `create_learn_issue`

**File**: `src/erk/cli/commands/land_pipeline.py`

Remove `update_learn_plan` (lines 439-460). Add new `create_learn_issue` step:

```python
def create_learn_issue(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Create a learn plan issue with preprocessed sessions for the landed plan."""
    if state.plan_id is None or state.merged_pr_number is None:
        return state

    # Skip for learn plans (don't learn from learn plans)
    plan_result = ctx.plan_store.get_plan(state.main_repo_root, state.plan_id)
    if isinstance(plan_result, PlanNotFound):
        return state
    if "erk-learn" in plan_result.labels:
        return state

    # Check config (respect prompt_learn_on_land setting)
    if not _should_create_learn_issue(ctx):
        return state

    # Preprocess sessions and create issue
    _create_learn_issue_with_sessions(ctx, state)
    return state
```

Update `_execution_pipeline()` (line 501-507): replace `update_learn_plan` with `create_learn_issue`.

### 3. Implement `_create_learn_issue_with_sessions` in land_cmd.py

**File**: `src/erk/cli/commands/land_cmd.py`

New function that:
1. Discovers sessions via `ctx.plan_backend.find_sessions_for_plan()`
2. Preprocesses them locally (reuse `erk_shared.learn.extraction.session_preprocessing`)
3. Creates a learn plan issue via the gateway with:
   - Title: `[erk-learn] Learn: <source plan title>`
   - Body: preprocessed session XML + source plan reference + merged PR number
   - Labels: `erk-learn`, `erk-plan`
4. Fail-open: if anything errors, log warning and continue (don't block landing)

### 4. Remove dead code from land_cmd.py

**File**: `src/erk/cli/commands/land_cmd.py`

Remove the following functions (total ~300 lines):
- `_check_learn_status_and_prompt()` (lines 269-349)
- `_prompt_async_learn_and_continue()` (lines 352-434)
- `LearnPreprocessResult` / `LearnPreprocessError` types (lines 437-449)
- `_run_learn_preprocessing()` (lines 452-505)
- `_trigger_async_learn()` (lines 508-561)
- `_parse_trigger_error()` (lines 564+)
- `_preprocess_and_prepare_manual_learn()` (lines 621+)
- `_store_learn_materials_branch()` and related helpers
- `_update_parent_learn_status_if_learn_plan()` (lines 666-713) — no longer called from `update_learn_plan`

### 5. Remove stacking logic for learn plans

**File**: `src/erk/cli/commands/pr/dispatch_cmd.py`

Remove `get_learn_plan_parent_branch()` (lines 59-80) and its usage in dispatch (line 499). Learn plans no longer stack on parent branches — they target master like everything else.

### 6. Do NOT remove (keep for now)

- **`learn.yml` workflow**: Keep but stop triggering it. Can remove in a follow-up.
- **Exec scripts** (`trigger_async_learn.py`, `track_learn_result.py`, `track_learn_evaluation.py`): Keep for now. They become unused but removing them is a separate cleanup.
- **`/erk:learn` skill**: Still useful for manual local invocation.
- **Plan header schema learn fields**: Keep for backward compatibility. Existing issues have these fields.
- **`--learned-from-issue` option on plan-save**: Keep — the new learn issue creation may still use this for discoverability.
- **`erk-skip-learn` config/label**: Replaced by `prompt_learn_on_land` config check in the new step.

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/land_pipeline.py` | Replace 2 pipeline steps, update pipeline tuples |
| `src/erk/cli/commands/land_cmd.py` | Add `_create_learn_issue_with_sessions()`, remove ~300 lines of async learn code |
| `src/erk/cli/commands/pr/dispatch_cmd.py` | Remove `get_learn_plan_parent_branch()` and usage |
| Tests for land pipeline | Update to reflect new steps |
| Tests for land_cmd | Remove tests for deleted functions, add tests for new function |

## Verification

1. Run unit tests for land pipeline: `pytest tests/unit/cli/commands/land/`
2. Run unit tests for dispatch: `pytest tests/unit/cli/commands/pr/`
3. Manual test: land a plan branch, verify learn issue created with preprocessed sessions
4. Manual test: land a learn plan branch, verify no learn issue created (skip-learn-plans check)
5. Manual test: land with `prompt_learn_on_land=false`, verify no learn issue created
6. Verify `/local:replan-learn-plans` can pick up the new learn issues
