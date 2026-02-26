# Fix: plan-header metadata block lost silently in CI update flow

## Context

The warning `"failed to update lifecycle stage: plan-header block not found in PR body"` fires when
`erk pr submit` finalizes a `plnd/` branch PR. The `maybe_advance_lifecycle_to_impl` function
calls `update_metadata` which fetches the current PR body and looks for the `plan-header` metadata
block. If the block is missing, `PlanHeaderNotFoundError` is caught as `RuntimeError` and printed
as a warning.

The warning indicates that `assemble_pr_body` wrote the final PR body WITHOUT the plan-header. This
happens because `find_metadata_block(state.existing_pr_body, "plan-header")` returned `None` —
meaning the `plan-header` block was absent from the PR body captured by `capture_existing_pr_body`
BEFORE `gt submit` ran.

### Root cause chain

1. CI's `git-pr-push` pushes code, appends checkout footer (plan-header preserved ✓)
2. CI's `ci-update-pr-body --planned-pr` calls `find_metadata_block(pr_result.body, "plan-header")`
3. **If this returns `None`** (YAML parse failure or truly missing block): `metadata_text = ""`
   and the updated PR body is written WITHOUT the plan-header — **silently, no error raised**
4. User's `erk pr submit` → `capture_existing_pr_body` gets the corrupted body (no plan-header)
5. `assemble_pr_body` sees no plan-header → final body omits it
6. `maybe_advance_lifecycle_to_impl` tries and fails → warning fires

### Two contributing bugs

- **Bug A (primary)**: `ci_update_pr_body.py` silently writes a PR body without the plan-header
  when `plan_header is None` and `is_planned_pr=True`. No error is raised. No warning is logged.
  Corruption is completely invisible.

- **Bug B (enabling)**: `parse_metadata_blocks` in `metadata/core.py` drops blocks with YAML parse
  failures at DEBUG log level only. This makes upstream failures invisible in normal operation,
  preventing diagnosis of why `find_metadata_block` returned `None`.

## Files to modify

1. `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
2. `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`
3. `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

## Implementation steps

### Step 1: Fix `ci_update_pr_body.py` — fail loudly on missing plan-header

In `UpdateError.error` Literal (lines 80-88), add `"plan-header-not-found"` to the allowed values.

In `_update_pr_body_impl` (line ~263), insert an early return after `plan_header = find_metadata_block(...)`:

```python
if is_planned_pr:
    plan_header = find_metadata_block(pr_result.body, "plan-header")
    # NEW: fail loudly instead of silently dropping the plan-header
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

This converts silent corruption into a loud CI failure, enabling diagnosis and manual recovery
instead of a propagating broken state.

### Step 2: Fix `metadata/core.py` — raise log level for YAML parse failures

In `parse_metadata_blocks` (around line 557), change:
```python
logger.debug(f"Failed to parse metadata block '{raw_block.key}': {e}")
```
to:
```python
logger.warning(f"Failed to parse metadata block '{raw_block.key}': {e}")
```

YAML parse failures in metadata blocks are always programming errors or data corruption, not
expected behavior. WARNING makes them visible in normal operation. The existing `parse_metadata_blocks`
tests use `caplog.at_level(logging.DEBUG)` which still captures WARNING; no test assertions check
the specific log level.

### Step 3: Add regression test for `ci_update_pr_body` with missing plan-header

In `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`, add a test:

```python
def test_planned_pr_missing_plan_header_returns_error(...):
    """When --planned-pr is set but plan-header block is absent, returns error."""
    # Build PR body WITHOUT plan-header metadata block
    pr_body = "Some AI-generated content without metadata block"
    github = FakeGitHub(prs={...}, pr_details={pr_num: PRDetails(body=pr_body, ...)}, ...)
    # executor returns valid output
    result = runner.invoke(
        ci_update_pr_body, ["--plan-id", "123", "--planned-pr"], obj=context
    )
    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "plan-header-not-found"
    # PR body should NOT have been modified (no call to update_pr_title_and_body)
    assert len(github.updated_pr_bodies) == 0
```

Follow the existing test patterns in `test_ci_update_pr_body.py`: use `FakeGitHub`, `FakeGit`,
`FakePromptExecutor`, `CliRunner`, and `ErkContext.for_test(...)`.

## Key functions / reuse

- `find_metadata_block` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py:590`
- `parse_metadata_blocks` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py:557`
- `UpdateError` dataclass in `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py:75`
- `_update_pr_body_impl` in `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py:162`
- Existing test fixtures in `tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py`

## What this does NOT fix

- Does not add automatic plan-header reconstruction. Once lost, manual `gh pr edit` is needed.
- Does not fix the underlying cause of why `find_metadata_block` returned `None` (could be YAML
  parse failure, wrong `--planned-pr` flag, or PR body corruption from git-pr-push Step 7.5).
  The new ERROR message gives the operator visibility to investigate.
- Does not change behavior for non-`--planned-pr` calls (issue-based plans unaffected).

## Verification

```bash
# Run existing tests (must still pass)
pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py -v

# Run new test
pytest tests/unit/cli/commands/exec/scripts/test_ci_update_pr_body.py::test_planned_pr_missing_plan_header_returns_error -v

# Run metadata parsing tests (log level change must not break them)
pytest tests/unit/gateways/github/metadata_blocks/ -v

# Full fast CI
make fast-ci
```
