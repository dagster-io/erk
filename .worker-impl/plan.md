# Preserve Local Branches During Plan Submit

## Problem

When `erk plan submit` creates a branch, pushes it to remote, and creates a PR, it then **deletes the local branch**:

```python
# In _create_branch_and_pr (lines 441-445):
user_output("Restoring local state...")
ctx.branch_manager.checkout_branch(repo.root, original_branch)
ctx.branch_manager.delete_branch(repo.root, branch_name, force=True)
user_output(click.style("✓", fg="green") + " Local branch cleaned up")
```

This breaks Graphite's lineage tracking because:
1. Graphite needs local branches to exist to show stack relationships
2. `gt ls` and `gt log` won't show the submitted branch
3. Users get confused when the branch exists on remote but not locally

## Solution

Preserve the local branch after submit. The user is switched back to their original branch, but the new branch remains locally, maintaining Graphite stack visibility.

## Changes

### File: `src/erk/cli/commands/submit.py`

**Location 1: `_create_branch_and_pr` (around line 441)**

Remove:
```python
# Restore local state
user_output("Restoring local state...")
ctx.branch_manager.checkout_branch(repo.root, original_branch)
ctx.branch_manager.delete_branch(repo.root, branch_name, force=True)
user_output(click.style("✓", fg="green") + " Local branch cleaned up")
```

Replace with:
```python
# Switch back to original branch (keep the new branch for Graphite lineage)
ctx.branch_manager.checkout_branch(repo.root, original_branch)
```

**Location 2: `_submit_single_issue` (around line 562)**

Same change - remove the `delete_branch` call and update the comment.

## Test Impact

No test changes needed - verified no tests assert `delete_branch` is called.

## Verification

1. Run existing tests: `pytest tests/commands/pr/test_submit.py`
2. Run `erk plan submit <issue>` on a test issue
3. After completion, verify `git branch` shows the new branch locally
4. Verify `gt ls` shows the branch in the Graphite stack