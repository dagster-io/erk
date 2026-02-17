# Fix: Missing branch_name in plan-header causes PR lookup failure during learn

## Context

When running `erk land`, the `trigger-async-learn` step fails to find the PR for the plan because `branch_name` is missing from the plan-header metadata. This happens when implementation runs remotely via CI — the `update-plan-remote-session` command records session info but not the branch name. The `_get_pr_for_plan_direct` function in `trigger_async_learn.py` has no fallback for this case, unlike the standalone `get_pr_for_plan.py` which infers the branch from current git context.

Two bugs:
1. `trigger_async_learn.py`'s `_get_pr_for_plan_direct` lacks the branch-inference fallback that `get_pr_for_plan.py` has
2. `update_plan_remote_session.py` doesn't set `branch_name` even though it's available in CI

## Changes

### Bug 1: Add branch-inference fallback to `_get_pr_for_plan_direct`

**File:** `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

Add git branch inference when `branch_name` is missing from metadata, matching the pattern in `get_pr_for_plan.py:89-94`:

```python
def _get_pr_for_plan_direct(
    *,
    github_issues,
    github,
    git,           # NEW: add git parameter
    repo_root: Path,
    issue_number: int,
) -> dict[str, object] | None:
```

At line 296-298, replace the simple `return None` with the fallback:

```python
branch_name = block.data.get("branch_name")
if branch_name is None:
    # Fallback: infer from current git branch (matches get_pr_for_plan.py pattern)
    current_branch = git.branch.get_current_branch(repo_root)
    if current_branch is not None and current_branch.startswith(f"P{issue_number}-"):
        branch_name = current_branch
if branch_name is None:
    return None
```

Add `require_git` to imports (line 52-58) and obtain it in `trigger_async_learn` (after line 351):

```python
git = require_git(ctx)
```

Update the call site at line 477-482 to pass `git`:

```python
pr_result = _get_pr_for_plan_direct(
    github_issues=github_issues,
    github=github,
    git=git,
    repo_root=repo_root,
    issue_number=issue_number,
)
```

### Bug 2: Add `--branch-name` to `update-plan-remote-session`

**File:** `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py`

Add optional `--branch-name` parameter:

```python
@click.option(
    "--branch-name",
    type=str,
    default=None,
    help="Branch name to store in plan-header metadata",
)
```

Include in metadata dict when provided:

```python
metadata: dict[str, object] = {
    "last_remote_impl_at": timestamp,
    "last_remote_impl_run_id": run_id,
    "last_remote_impl_session_id": session_id,
}
if branch_name is not None:
    metadata["branch_name"] = branch_name
```

**File:** `.github/workflows/plan-implement.yml`

Update the call site (lines 254-258) to pass branch name:

```yaml
run: |
  erk exec update-plan-remote-session \
    --issue-number "$ISSUE_NUMBER" \
    --run-id "$RUN_ID" \
    --session-id "$SESSION_ID" \
    --branch-name "$BRANCH_NAME"
```

Add `BRANCH_NAME` to the env block:

```yaml
env:
  GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
  ISSUE_NUMBER: ${{ inputs.issue_number }}
  RUN_ID: ${{ github.run_id }}
  SESSION_ID: ${{ steps.session.outputs.session_id }}
  BRANCH_NAME: ${{ inputs.branch_name }}
```

## Critical files

- `src/erk/cli/commands/exec/scripts/trigger_async_learn.py` — `_get_pr_for_plan_direct` (lines 270-315), call site (lines 477-482)
- `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py` — reference implementation of fallback (lines 88-94)
- `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` — add `--branch-name` option
- `.github/workflows/plan-implement.yml` — pass `$BRANCH_NAME` at line 246-258
- `docs/learned/planning/branch-name-inference.md` — existing doc on this exact pattern

## Tests

### Bug 1 test
**File:** `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`

Add test: when plan-header has no `branch_name` but current git branch matches `P{issue}-` prefix, `_get_pr_for_plan_direct` should still find the PR. Use `FakeGit(current_branches={...})` pattern from `test_get_pr_for_plan.py:308-336`.

### Bug 2 test
**File:** `tests/unit/cli/commands/exec/scripts/test_update_plan_remote_session.py`

Add test: when `--branch-name` is passed, the updated plan-header metadata should contain `branch_name`. When omitted, `branch_name` should not be added.

## Verification

1. Run unit tests for both modified scripts via devrun
2. Verify the fallback works end-to-end: create a plan issue without `branch_name` in metadata, be on the matching branch, and confirm `trigger-async-learn` finds the PR