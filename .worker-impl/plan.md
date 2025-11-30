# Plan: Remove unnecessary dirty branch check from `erk submit`

## Problem

`erk submit` errors with "You have uncommitted changes" when run on a dirty branch, but this check is unnecessary because the command operates entirely on a fresh branch from `origin/{trunk_branch}`.

## Root Cause

Lines 174-179 in `src/erk/cli/commands/submit.py`:

```python
if ctx.git.has_uncommitted_changes(repo.root):
    user_output(
        click.style("Error: ", fg="red")
        + "You have uncommitted changes. Please commit or stash them first."
    )
    raise SystemExit(1)
```

## Why the check is unnecessary

The `erk submit` workflow:

1. Records `original_branch`
2. Creates new branch from `origin/{trunk_branch}` (NOT from current branch)
3. Adds `.worker-impl/` folder content
4. Commits and pushes
5. Creates draft PR
6. Switches back to `original_branch`
7. Deletes the temporary local branch

Since git preserves uncommitted working directory changes when switching branches (as long as there are no conflicts), the user's dirty state is unaffected.

## Implementation

### Step 1: Remove the uncommitted changes check

Delete lines 174-179 in `src/erk/cli/commands/submit.py`:

```python
if ctx.git.has_uncommitted_changes(repo.root):
    user_output(
        click.style("Error: ", fg="red")
        + "You have uncommitted changes. Please commit or stash them first."
    )
    raise SystemExit(1)
```

### Step 2: Update docstring

Remove the line "- Working directory must be clean (no uncommitted changes)" from the `Requires:` section in the docstring (around line 155).

## Files to modify

- `src/erk/cli/commands/submit.py`

## Testing

Manual verification: Run `erk submit <issue_number>` with uncommitted changes to verify it works.
