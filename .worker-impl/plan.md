# Plan: Add Clickable Workflow Run URL to `erk learn --async`

## Summary

Change `erk learn --async` to print a clickable GitHub Actions workflow run URL instead of just the raw run ID.

**Current Output**:
```
Async learn job enqueued successfully
Issue: #123
Workflow run ID: 21211631092

Learn status: pending
```

**Desired Output**:
```
Async learn job enqueued successfully
Issue: #123
Workflow run: https://github.com/dagster-io/erk/actions/runs/21211631092

Learn status: pending
```

## Files to Modify

1. `src/erk/cli/commands/learn/learn_cmd.py` - Update output to include full URL

## Implementation

### Step 1: Update `_handle_async_mode()` signature

Pass `GitHubRepoId | None` to `_handle_async_mode()` so it can construct the URL:

```python
def _handle_async_mode(
    ctx: ErkContext,
    repo_root: Path,
    issue_number: int,
    github_repo: GitHubRepoId | None,  # Add this parameter
) -> None:
```

### Step 2: Import `construct_workflow_run_url`

Add import at top of file:
```python
from erk_shared.github.parsing import construct_workflow_run_url
from erk_shared.github.types import GitHubRepoId
```

### Step 3: Update the output line

Change line 96 from:
```python
user_output(f"Workflow run ID: {result.run_id}")
```

To:
```python
if github_repo is not None:
    workflow_url = construct_workflow_run_url(
        github_repo.owner, github_repo.repo, result.run_id
    )
    user_output(f"Workflow run: {workflow_url}")
else:
    user_output(f"Workflow run ID: {result.run_id}")
```

### Step 4: Update call site

Update the call at line 189:
```python
_handle_async_mode(ctx, repo_root, issue_number, repo.github)
```

### Step 5: Update test

Update `tests/commands/learn/test_display.py` test `test_async_flag_triggers_workflow` to verify URL format:
```python
assert "https://github.com/owner/repo/actions/runs/" in result.output
```

## Verification

1. Run affected test: `pytest tests/commands/learn/test_display.py -k async`
2. Manual test: Run `erk learn --async` on a plan issue and verify clickable URL appears