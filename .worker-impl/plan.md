# Fix: Graphite create_branch fails when parent branch is untracked

## Problem

When `erk plan submit` stacks a plan on a parent branch that exists locally but isn't tracked with Graphite, the command fails with an unhelpful error:

```
ERROR: Cannot perform this operation on untracked branch P5611-address-pr-review-comment-01-22-1451.
You can track it by specifying its parent with gt track.
```

**Root cause**: `GraphiteBranchManager.create_branch()` calls `graphite_branch_ops.track_branch()` without first checking if the parent branch is tracked with Graphite.

## Solution

This is a "Non Ideal State" - not an error in the code, but a situation where the user's environment isn't set up for the requested operation. Handle it gracefully with clear user feedback, not a scary exception.

**Approach**: Add LBYL check in the CLI layer (`submit.py`) before calling `create_branch`. Display a friendly message and exit cleanly if the parent isn't tracked.

## Implementation

### File: `src/erk/cli/commands/submit.py`

**Change**: In `_submit_single_issue()` (around line 575), before calling `create_branch`, check if the parent is tracked:

```python
# Before creating the stacked branch, verify parent is tracked by Graphite
parent_branch = base_branch.removeprefix("origin/")
if not ctx.graphite.is_branch_tracked(repo.root, parent_branch):
    user_output(
        f"Cannot stack on branch '{parent_branch}' - it's not tracked by Graphite.\n\n"
        f"To fix this:\n"
        f"  1. gt checkout {parent_branch}\n"
        f"  2. gt track --parent <parent-branch>\n\n"
        f"Then retry your command.",
        style="warning"
    )
    raise SystemExit(1)

ctx.branch_manager.create_branch(repo.root, branch_name, f"origin/{base_branch}")
```

### Test File: `tests/commands/test_submit_cmd.py`

Add test case:
- `test_submit_exits_cleanly_when_parent_untracked` - verify friendly message is displayed and exits with code 1 (not an exception traceback)

## Verification

1. Run unit tests: `make test-unit` (via devrun agent)
2. Run type checker: `make ty` (via devrun agent)
3. Manual test: Reproduce the original bug scenario to confirm clean exit with helpful message