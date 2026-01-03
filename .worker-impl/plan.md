---
steps:
  - name: "Fix 2 ignores in sync_cmd.py"
  - name: "Fix 5 ignores in preflight.py"
  - name: "Fix 7 ignores in get_pr_discussion_comments.py"
  - name: "Mark 1B.4 as done (already fixed)"
  - name: "Run type checker to verify"
  - name: "Update objective #3816"
---

# Plan: Phase 1B - Sentinel Narrowing Fixes

**Part of Objective #3816, Steps 1B.1-1B.4**

## Goal

Fix 14 `# type: ignore` comments across 3 files using assert-based type narrowing after error-exit paths.

**Note:** Step 1B.4 (`get_pr_review_comments.py`) is already fixed - it now uses `_ensure_pr_result()` helper pattern.

## Pattern to Apply

After a guard clause that calls a NoReturn function (like `exit_with_error`, `sys.exit`), add an assert to help the type checker narrow:

```python
# Before:
if isinstance(result, SentinelError):
    exit_with_error(...)
value = result.attribute  # type: ignore[possibly-missing-attribute]

# After:
if isinstance(result, SentinelError):
    exit_with_error(...)
assert not isinstance(result, SentinelError)  # Type narrowing after NoReturn
value = result.attribute  # Now type-safe
```

## Files to Modify

### 1. `src/erk/cli/commands/pr/sync_cmd.py` (2 ignores)

**Lines 42-43:**
```python
Ensure.invariant(not isinstance(squash_result, SquashError), squash_result.message)  # type: ignore
user_output(click.style("✓", fg="green") + f" {squash_result.message}")  # type: ignore
```

**Fix:** Add assert after Ensure.invariant:
```python
Ensure.invariant(not isinstance(squash_result, SquashError), squash_result.message)
assert not isinstance(squash_result, SquashError)  # Type narrowing after invariant
user_output(click.style("✓", fg="green") + f" {squash_result.message}")
```

### 2. `packages/erk-shared/src/erk_shared/gateway/gt/operations/preflight.py` (5 ignores)

**Lines 257-259 (in `_execute_submit_only`):**
After the `isinstance(pr_result, PRNotFound)` check returns early, add assert:
```python
if isinstance(pr_result, PRNotFound):
    yield CompletionEvent(PostAnalysisError(...))
    return
assert not isinstance(pr_result, PRNotFound)  # Type narrowing after early return
yield ProgressEvent(f"PR info retrieved (PR #{pr_result.number})", style="success")
pr_number = pr_result.number
pr_url = pr_result.url
```

**Line 325 (in `execute_preflight`):**
After the `isinstance(submit_result, PostAnalysisError)` check returns early:
```python
if submit_result is None or isinstance(submit_result, PostAnalysisError):
    if submit_result is not None:
        yield CompletionEvent(submit_result)
    return
assert not isinstance(submit_result, PostAnalysisError)  # Type narrowing
assert submit_result is not None
pr_number, pr_url, graphite_url, branch_name = submit_result
```

**Line 378 (in `execute_preflight`):**
After `pre_result` is checked for None/PreAnalysisError earlier:
```python
assert not isinstance(pre_result, PreAnalysisError)  # Already checked at line 303
...
commit_messages=pre_result.commit_messages,
```

### 3. `src/erk/cli/commands/exec/scripts/get_pr_discussion_comments.py` (7 ignores)

**Lines 77-84:** Create helper function similar to `get_pr_review_comments.py`:
```python
def _ensure_branch(branch_result: str | BranchDetectionFailed) -> str:
    """Ensure branch was detected, exit with error if not."""
    if isinstance(branch_result, BranchDetectionFailed):
        exit_with_error(branch_result.error_type, branch_result.message)
    assert not isinstance(branch_result, BranchDetectionFailed)
    return branch_result

def _ensure_pr_result(
    pr_result: PRDetails | NoPRForBranch | PRNotFoundError,
) -> PRDetails:
    """Ensure PR lookup succeeded, exit with appropriate error if not."""
    if isinstance(pr_result, (NoPRForBranch, PRNotFoundError)):
        exit_with_error(pr_result.error_type, pr_result.message)
    assert not isinstance(pr_result, (NoPRForBranch, PRNotFoundError))
    return pr_result

def _ensure_comments(
    comments_result: list[IssueComment] | GitHubAPIFailed,
) -> list[IssueComment]:
    """Ensure comments fetch succeeded, exit with error if not."""
    if isinstance(comments_result, GitHubAPIFailed):
        exit_with_error(comments_result.error_type, comments_result.message)
    assert not isinstance(comments_result, GitHubAPIFailed)
    return comments_result
```

Then refactor main function to use helpers:
```python
if pr is None:
    branch_result = GitHubChecks.branch(get_current_branch(ctx))
    branch = _ensure_branch(branch_result)
    pr_details = _ensure_pr_result(GitHubChecks.pr_for_branch(github, repo_root, branch))
else:
    pr_details = _ensure_pr_result(GitHubChecks.pr_by_number(github, repo_root, pr))

comments = _ensure_comments(GitHubChecks.issue_comments(github_issues, repo_root, pr_details.number))
```

## Test Requirements

- Run `make ty` (or `uv run ty check`) to verify type checker passes
- No behavior changes, so existing tests should pass
- No new tests needed (pure type annotation changes)

## Related Documentation

- Skills: `dignified-python` (type safety patterns)
- Existing pattern: `src/erk/cli/commands/exec/scripts/get_pr_review_comments.py:68-89`