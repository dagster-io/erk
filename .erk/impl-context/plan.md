# Fix: plan-header metadata block lost silently in CI update flow

## Context

The warning "failed to update lifecycle stage: plan-header block not found in PR body" fires when `erk pr submit` finalizes a `plnd/` branch PR. The `maybe_advance_lifecycle_to_impl` function calls `update_metadata` which fetches the current PR body and looks for the plan-header metadata block. If the block is missing, `PlanHeaderNotFoundError` is caught as `RuntimeError` and printed as a warning.

The warning indicates that `assemble_pr_body` wrote the final PR body WITHOUT the plan-header. This happens because `find_metadata_block(state.existing_pr_body, "plan-header")` returned `None` — meaning the plan-header was absent from the PR body captured by `capture_existing_pr_body` BEFORE `gt submit` ran.

### Root cause chain

1. CI's `git-pr-push` pushes code, appends checkout footer (plan-header preserved)
2. CI's `ci-update-pr-body --planned-pr` calls `find_metadata_block(pr_result.body, "plan-header")`
3. If this returns `None` (YAML parse failure or truly missing block): `metadata_text = ""` and the updated PR body is written WITHOUT the plan-header — silently, no error raised
4. User's `erk pr submit` → `capture_existing_pr_body` gets the corrupted body (no plan-header)
5. `assemble_pr_body` sees no plan-header → final body omits it
6. `maybe_advance_lifecycle_to_impl` tries and fails → warning fires

### Two contributing bugs

- **Bug A (primary):** `ci_update_pr_body.py` silently writes a PR body without the plan-header when `plan_header is None` and `is_planned_pr=True`. No error is raised. Corruption is invisible.
- **Bug B (enabling):** `parse_metadata_blocks` in `metadata/core.py` drops blocks with YAML parse failures at DEBUG log level only. This prevents diagnosis of why `find_metadata_block` returned `None`.

## Files to modify

1. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
2. `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`
3. `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

## Implementation steps

### Step 1: Fix ci_update_pr_body.py — fail loudly on missing plan-header

Add `"plan-header-not-found"` to `UpdateError.error` Literal (line ~79), then insert early return when `plan_header is None` before the current `metadata_text` ternary (line ~269):

```python
if is_planned_pr:
    plan_header = find_metadata_block(pr_result.body, "plan-header")
    if plan_header is None:
        return UpdateError(
            success=False,
            error="plan-header-not-found",
            message=(
                "plan-header metadata block not found in PR body for planned-PR plan. "
                "The plan-header was lost in a previous step. "
                "Inspect the PR body and check for earlier CI step failures."
            ),
            stderr=None,
        )
    plan_content = extract_plan_content(pr_result.body)
    ...
```

### Step 2: Fix metadata/core.py — raise log level for YAML parse failures

In `parse_metadata_blocks` (line ~584), change:
```python
logger.debug(f"Failed to parse metadata block '{raw_block.key}': {e}")
```
to:
```python
logger.warning(f"Failed to parse metadata block '{raw_block.key}': {e}")
```

YAML failures in metadata blocks are always bugs/corruption, not expected behavior.

### Step 3: Add regression test

In `test_ci_update_pr_body.py`, add a test in the planned-PR section (~line 728+) that verifies: `--planned-pr` + missing plan-header → returns `UpdateError` with `error="plan-header-not-found"` and no PR body modification occurs.

Follow existing test patterns using `FakeGit`, `FakeGitHub`, `FakePromptExecutor`.

## What this does NOT fix

- No automatic plan-header reconstruction (manual `gh pr edit` needed once lost)
- Does not identify the exact cause of the initial plan-header loss — the new loud error gives operators visibility to investigate

## Verification

```
pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py -v
pytest tests/unit/gateways/github/metadata_blocks/ -v
make fast-ci
```
