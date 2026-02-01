# Plan: Close review PR when plan implementation starts

## Problem

When a plan has a review PR (created via `/erk:plan-review`), that review PR stays open even after the plan is prepared and implemented via `erk implement`. It should be auto-closed when implementation begins.

## Fix

Add a call to `cleanup_review_pr()` in `_implement_from_issue()` in `src/erk/cli/commands/implement.py`. This is a one-line integration — the `cleanup_review_pr` function already exists, is well-tested, and is fail-open (errors don't block implementation).

## Changes

### 1. `src/erk/cli/commands/implement.py`

Add import at top:

```python
from erk.cli.commands.review_pr_cleanup import cleanup_review_pr
```

In `_implement_from_issue()`, after the plan is fetched (line ~107, `plan = result`) and before creating `.impl/` (line ~141):

```python
# Close any open review PR (implementation supersedes review)
cleanup_review_pr(
    ctx,
    repo_root=repo.root,
    issue_number=int(issue_number),
    reason=f"the plan (issue #{issue_number}) was submitted for implementation",
)
```

No test needed for this integration — `cleanup_review_pr` is already thoroughly tested in `tests/commands/plan/test_review_pr_cleanup.py` (5 tests covering happy path, no review PR, no plan header, issue not found, and close failure). The new call site is just wiring.

## Also: close review PR #6397 for issue #6396

After implementing, manually close the review PR that prompted this fix:

```
gh pr close 6397 -c "Closed: plan was submitted for implementation"
```

## Verification

1. Read the modified file to confirm the call is placed correctly
2. `make fast-ci` passes
