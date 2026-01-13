# Fix `erk admin test-erk-impl-gh-workflow` PR Creation Bug

## Problem

The command fails with HTTP 422 when creating a draft PR because the test branch is identical to master. GitHub rejects PRs with "No commits between master and test-branch".

**Root cause:** Line 211 pushes `master:test_branch`, creating a branch pointing to the same commit as master.

## Solution

Add an empty commit to the test branch before creating the PR.

## File to Modify

`/Users/schrockn/code/erk/src/erk/cli/commands/admin.py`

## Changes

### 1. Update docstring (lines 164-176)

Update step list to include the new step:
```
1. Ensuring the current branch exists on remote
2. Finding or creating a test issue
3. Creating a test branch from master
4. Adding an empty commit (required for PR creation)
5. Creating a draft PR
6. Triggering the workflow with --ref set to your branch
7. Outputting the run URL
```

### 2. Add empty commit logic (after line 212)

Insert after "Test branch created" message:

```python
# Step 4: Add an empty commit to the test branch
# GitHub rejects PRs with no commits between base and head
user_output(f"Adding initial commit to '{test_branch}'...")
ctx.git.fetch_branch(repo.root, "origin", test_branch)
ctx.git.checkout_branch(repo.root, test_branch)
ctx.git.commit(repo.root, "Test workflow run")
ctx.git.push_to_remote(repo.root, "origin", test_branch)
ctx.git.checkout_branch(repo.root, current_branch)
user_output(click.style("✓", fg="green") + f" Initial commit added to '{test_branch}'")
```

### 3. Renumber subsequent steps

- "Step 4: Create draft PR" → "Step 5: Create draft PR"
- "Step 5: Trigger workflow" → "Step 6: Trigger workflow"
- "Step 6: Get run URL" → "Step 7: Get run URL"

## Verification

1. Run type checker: `ty src/erk/cli/commands/admin.py`
2. Run related tests: `pytest tests/ -k admin`
3. Manual test in dagster-compass repo:
   ```bash
   cd /Users/schrockn/code/dagster-compass
   erk admin test-erk-impl-gh-workflow --issue 1986
   ```
   Should complete without HTTP 422 error.