# Fix: plan-header metadata block lost silently in CI update flow

## Context

The warning "failed to update lifecycle stage: plan-header block not found in PR body" fires when `erk pr submit` finalizes a `plnd/` branch PR. The root cause is that `ci_update_pr_body.py` silently writes a PR body without the plan-header when `find_metadata_block` returns None for a planned PR. This corruption is invisible — no error, no warning — and propagates downstream.

## Files to modify

1. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
2. `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`
3. `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

## Implementation steps

### Step 1: Fix ci_update_pr_body.py — fail loudly on missing plan-header

- Add `"plan-header-not-found"` to the `UpdateError.error` Literal (line ~80-87)
- In the `is_planned_pr` block (line ~263), insert an early return before `extract_plan_content` when `plan_header is None`:

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

In `parse_metadata_blocks` (line 584), change:

```python
logger.debug(f"Failed to parse metadata block '{raw_block.key}': {e}")
```

to:

```python
logger.warning(f"Failed to parse metadata block '{raw_block.key}': {e}")
```

Also fix the misleading docstring that says "logs warnings" (it was already claiming warning-level behavior).

### Step 3: Add regression test

In `test_ci_update_pr_body.py`, add a test that verifies:

- `--planned-pr` + PR body missing plan-header → `UpdateError` with `error="plan-header-not-found"`
- No PR body modification occurs (gh pr edit not called)

## What this does NOT fix

- No automatic plan-header reconstruction (manual `gh pr edit` needed once lost)
- Does not identify the exact cause of the initial plan-header loss

## Verification

```
pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py -v
pytest tests/unit/gateways/github/metadata_blocks/ -v
make fast-ci
```
