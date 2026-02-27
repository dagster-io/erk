# Fix: Move impl-context cleanup from setup-impl to submit pipeline

## Context

When running `/erk:plan-implement`, `erk exec setup-impl` calls `cleanup_impl_context` which deletes `.erk/impl-context/` from disk, commits the deletion, and pushes to remote **before the agent starts implementing**. This removes plan tracking data that downstream tools need:

- `impl-signal started/ended` fail (can't find plan reference)
- `erk pr submit` can't discover `plan_id` → `effective_force` stays False → `gt submit` runs without `--force`
- `gt submit` rejects push because the raw `git push` from cleanup (bypassing Graphite) made the remote "updated remotely" from Graphite's perspective

**Fix**: Delay `.erk/impl-context/` cleanup until the submit pipeline, after `prepare_state` discovers `plan_id` but before `commit_wip` adds implementation changes.

## Changes

### 1. Remove cleanup from setup-impl

**File**: `src/erk/cli/commands/exec/scripts/setup_impl.py`

In `_handle_issue_setup` (line 307), remove the `ctx.invoke(cleanup_impl_context)` call. The cleanup import can also be removed.

### 2. Add cleanup step to submit pipeline

**File**: `src/erk/cli/commands/pr/submit_pipeline.py`

Add a new `cleanup_impl_for_submit` step that:
- Uses `impl_context_exists(state.repo_root)` to check if `.erk/impl-context/` exists
- Uses `git.status.has_tracked_files(repo_root, ".erk/impl-context")` to check if tracked (same guard as current cleanup)
- If tracked: calls `remove_impl_context(state.repo_root)`, stages deletions, commits
- Does NOT push (push happens in `push_and_create_pr`)
- If not found/not tracked: no-op, return state unchanged

Insert into pipeline AFTER `prepare_state` and BEFORE `commit_wip`:
```python
def _submit_pipeline():
    return (
        prepare_state,
        cleanup_impl_for_submit,  # NEW
        commit_wip,
        capture_existing_pr_body,
        push_and_create_pr,
        ...
    )
```

Also add to `_push_and_create_pipeline()` (used by `run_push_and_create_pipeline`).

Imports to add: `impl_context_exists`, `remove_impl_context` from `erk_shared.impl_context`.

### 3. Add branch-name fallback for plan detection

**File**: `src/erk/cli/commands/pr/submit_pipeline.py`

In `_graphite_first_flow`, add `plnd/` branch prefix as a fallback for `is_plan_impl` detection. This handles retries where cleanup already deleted `.erk/impl-context/` but the first attempt failed before pushing:

```python
is_plan_impl = state.plan_id is not None or state.branch_name.startswith("plnd/")
```

Import `PLANNED_PR_BRANCH_PREFIX` or use the literal `"plnd/"` (already available as `PLANNED_PR_TITLE_PREFIX` in constants — but that's for titles, not branches). Use the literal since there's no existing branch prefix constant.

### 4. Update tests

**File**: `tests/unit/cli/commands/pr/submit_pipeline/test_graphite_first_flow.py` — add test for branch-name fallback auto-force.

**File**: Tests for the new `cleanup_impl_for_submit` step — verify it deletes, stages, commits, and handles the no-op case.

**File**: Tests for `setup_impl` — update any tests that assert `cleanup_impl_context` is called.

## Verification

1. Run existing submit pipeline tests: `pytest tests/unit/cli/commands/pr/submit_pipeline/ -x`
2. Run setup-impl tests: `pytest tests/commands/ -k setup_impl -x`
3. Run full fast-ci: `make fast-ci`
