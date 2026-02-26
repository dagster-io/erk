# Address PR #8252 Review: Add `.ensure()` to NonIdealState classes

## Context

PR #8252 reviewer comment on `get_pr_feedback.py:78` asks to eliminate the four `_ensure_*` helper functions by adding a `.ensure()` method to non-ideal state classes. Currently every exec script that handles non-ideal states must define per-type helper functions — four in this file alone, with similar boilerplate in `reply_to_discussion_comment.py` and `get_pr_discussion_comments.py`.

## Plan

### 1. Add `NonIdealStateError` and `.ensure()` to `packages/erk-shared/src/erk_shared/non_ideal_state.py`

Add exception class:
```python
class NonIdealStateError(Exception):
    """Raised by NonIdealState.ensure() when a non-ideal state is encountered."""
    def __init__(self, state: NonIdealState) -> None:
        self.error_type = state.error_type
        super().__init__(state.message)
```

Add `.ensure()` to the `NonIdealState` Protocol:
```python
def ensure(self) -> NoReturn:
    raise NonIdealStateError(self)
```

Since Protocol can have default method implementations, all four concrete classes (`BranchDetectionFailed`, `NoPRForBranch`, `PRNotFoundError`, `GitHubAPIFailed`, `SessionNotFound`) inherit it automatically — no per-class changes needed.

### 2. Add `handle_non_ideal_exit` decorator to `src/erk/cli/script_output.py`

```python
def handle_non_ideal_exit(func):
    """Click command decorator: catches NonIdealStateError → JSON error exit."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NonIdealStateError as e:
            exit_with_error(e.error_type, str(e))
    return wrapper
```

### 3. Update `src/erk/cli/commands/exec/scripts/get_pr_feedback.py`

- Delete all four `_ensure_*` functions (lines 44-78)
- Add `@handle_non_ideal_exit` decorator to the click command
- Replace call sites with inline isinstance + `.ensure()`:

```python
# Before:
branch = _ensure_branch(GitHubChecks.branch(get_current_branch(ctx)))
pr_details = _ensure_pr_for_branch(GitHubChecks.pr_for_branch(github, repo_root, branch))

# After:
branch = GitHubChecks.branch(get_current_branch(ctx))
if isinstance(branch, NonIdealState):
    branch.ensure()
pr_details = GitHubChecks.pr_for_branch(github, repo_root, branch)
if isinstance(pr_details, NonIdealState):
    pr_details.ensure()
```

## Files Modified

- `packages/erk-shared/src/erk_shared/non_ideal_state.py` — Add `NonIdealStateError`, add `.ensure()` to Protocol
- `src/erk/cli/script_output.py` — Add `handle_non_ideal_exit` decorator
- `src/erk/cli/commands/exec/scripts/get_pr_feedback.py` — Delete 4 functions, use `.ensure()` pattern

## Verification

1. `ty` type checking — confirm type narrowing works after `.ensure()` (NoReturn)
2. `pytest tests/unit/cli/commands/exec/scripts/` — existing tests pass
3. `erk exec get-pr-feedback --pr 8252` — returns valid JSON
