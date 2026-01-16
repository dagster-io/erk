# Plan: Add PR Number Argument to fix-conflicts-remote

## Summary

Enhance `erk pr fix-conflicts-remote` to accept an optional PR number argument, allowing users to trigger remote conflict resolution for any PR without needing to checkout the branch locally.

## Current Behavior

The command requires being on the branch with the PR:
1. Gets current branch from git
2. Looks up PR for that branch
3. Triggers rebase workflow

## Proposed Change

Add optional `pr_number` positional argument:
- If provided: Look up PR directly by number
- If not provided: Use current behavior (current branch → PR lookup)

## Implementation

### File: `src/erk/cli/commands/pr/fix_conflicts_remote_cmd.py`

**Changes:**

1. Add optional argument:
```python
@click.argument("pr_number", type=int, required=False)
```

2. Branch the logic:
   - If `pr_number` is provided: Call `ctx.github.get_pr(repo.root, pr_number)` to get `PRDetails`
   - If `pr_number` is None: Use existing current-branch logic

3. Extract branch name from `PRDetails.head_ref_name` instead of current branch

**Updated flow:**
```python
if pr_number is not None:
    # Direct PR lookup
    pr = ctx.github.get_pr(repo.root, pr_number)
    # Validate PR exists and is OPEN
    branch_name = pr.head_ref_name
else:
    # Existing behavior: get from current branch
    current_branch = Ensure.not_none(ctx.git.get_current_branch(ctx.cwd), ...)
    pr = ctx.github.get_pr_for_branch(repo.root, current_branch)
    branch_name = current_branch
```

### Updated Help Text

```
Usage: erk pr fix-conflicts-remote [OPTIONS] [PR_NUMBER]

  Trigger remote rebase with AI-powered conflict resolution.

  If PR_NUMBER is provided, triggers rebase for that PR.
  Otherwise, uses the PR for the current branch.
```

## Verification

1. Test with PR number: `erk pr fix-conflicts-remote 123`
2. Test without PR number (existing behavior): `erk pr fix-conflicts-remote`
3. Test error cases:
   - Invalid PR number
   - Closed/merged PR
   - PR not found

## Files to Modify

- `src/erk/cli/commands/pr/fix_conflicts_remote_cmd.py`

## Tests

Add unit tests in `tests/unit/cli/commands/pr/` for:
- PR number argument provided → uses `get_pr()` path
- No argument → uses existing `get_pr_for_branch()` path
- Error handling for PRNotFound with explicit PR number