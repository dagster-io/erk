# Plan: Add conflicts list to RestackPreflightError

## Problem

When `restack-preflight` returns `error_type: "squash_conflict"`, the agent doesn't know which files have conflicts. This causes unnecessary diagnostic commands (6 in the observed session) before the agent can start resolving conflicts.

## Solution

Add a `conflicts` field to `RestackPreflightError` so squash conflicts return the same file list as restack conflicts.

---

## BLOCKING: Fix plan-save-to-issue bug first

The `plan-save-to-issue` command fails with:
```
AttributeError: 'ErkContext' object has no attribute 'github_issues'
```

Need to investigate `context_helpers.py:require_github_issues()` and how it's being called from `plan_save_to_issue.py`.

## Files to Modify

### 1. `packages/erk-shared/src/erk_shared/integrations/gt/types.py`

Add `conflicts` field to `RestackPreflightError`:

```python
@dataclass(frozen=True)
class RestackPreflightError:
    """Error result from restack preflight."""
    success: Literal[False]
    error_type: RestackPreflightErrorType
    message: str
    details: dict[str, str]
    conflicts: list[str] = field(default_factory=list)  # NEW
```

### 2. `packages/erk-shared/src/erk_shared/integrations/gt/operations/restack_preflight.py`

When squash fails with conflict, call `get_conflicted_files()` and include in error:

```python
if isinstance(result, SquashError):
    # Get conflicts if available (squash_conflict leaves rebase in progress)
    conflicts = []
    if result.error == "squash_conflict":
        conflicts = ops.git.get_conflicted_files(cwd)

    yield CompletionEvent(
        RestackPreflightError(
            success=False,
            error_type="squash_conflict" if result.error == "squash_conflict" else ...,
            message=result.message,
            details={"squash_error": result.error},
            conflicts=conflicts,  # NEW
        )
    )
```

### 3. Update tests

- `packages/dot-agent-kit/tests/unit/kits/gt/test_restack_operations.py` - Update existing tests
- `packages/dot-agent-kit/tests/unit/kits/gt/fake_ops.py` - May need to support conflict simulation

## Implementation Notes

- `get_conflicted_files()` uses `git status --porcelain` which works in worktrees
- The field has a default so existing code constructing `RestackPreflightError` without conflicts still works
- This matches the pattern in `RestackPreflightSuccess` and `RestackContinueSuccess`

## Validation

- Run `make fast-ci` to verify no regressions
- The JSON output will now include `"conflicts": [...]` even for squash_conflict errors