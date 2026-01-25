# Fix: Remote Implementation Creates Wrong Branch

## Problem

When `erk-impl.yml` workflow runs:
1. Workflow checks out PR branch (e.g., `P5893-...-01-24-2229`)
2. Workflow copies `.worker-impl/` to `.impl/`
3. Workflow runs `/erk:plan-implement` with NO arguments
4. **Agent misbehavior**: Claude extracts issue `5893` from branch name and calls `setup-impl-from-issue 5893`
5. **Code bug**: `setup-impl-from-issue` generates NEW branch name with `datetime.now(UTC)`
6. Creates NEW branch (e.g., `P5893-...-01-25-0431`), orphaning PR

**Why it hasn't happened before**: Agent behavior is probabilistic. Most runs, Claude correctly follows Step 1b (check existing `.impl/`). This run, Claude "helpfully" extracted the issue number.

## Solution

Make `setup-impl-from-issue` defensive: detect when already on a matching branch and reuse it instead of creating new one. No flag needed - automatic detection.

## Files to Modify

### 1. `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

Add automatic branch detection after getting current branch (line ~105):

```python
current_branch = _get_current_branch(git, cwd)

# Check if already on a branch for this issue - reuse it
expected_prefix = f"P{issue_number}-"
if current_branch.startswith(expected_prefix):
    click.echo(f"Already on branch for issue #{issue_number}: {current_branch}", err=True)
    branch_name = current_branch
    # Skip branch creation, just ensure .impl/ exists
else:
    # Generate new branch name (existing logic)
    timestamp = datetime.now(UTC)
    branch_name = generate_issue_branch_name(issue_number, plan.title, timestamp)
    # ... existing branch creation logic
```

Full refactored logic:
1. If current branch matches `P{issue_number}-*`: use it, skip branch creation
2. If branch name already exists locally: checkout it (existing behavior)
3. Else: create new branch (existing behavior)

### 2. `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py`

Add test:
- Test reuses current branch when on matching `P{issue}-*` branch

## Verification

1. Run unit tests: `devrun` agent with `pytest tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py -v`
2. Manual test: Create a branch like `P9999-test-branch`, run `erk exec setup-impl-from-issue 9999`, verify it says "Already on branch" and doesn't create new branch
3. End-to-end: Re-dispatch PR #5894's workflow after fix is merged