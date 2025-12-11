---
description: Update PR by staging changes, committing, restacking, and submitting
---

# Update PR

Streamlines updating an existing PR in a Graphite stack by auto-staging and committing changes, restacking the stack, and submitting updates.

## What This Command Does

1. **Check PR exists**: Verifies current branch has an associated PR
2. **Auto-stage and commit**: Commits any uncommitted changes with default message
3. **Restack**: Restacks the branch with conflict detection
4. **Submit**: Updates the existing PR

## Usage

```bash
/gt:update-pr
```

## Implementation

**IMPORTANT**: All git commands must be run from the repository root, not from subdirectories. Use absolute paths or ensure working directory is set to repo root before executing git operations.

When this command is invoked:

### Execute Update PR Command

Run the kit CLI command to handle all update-pr operations:

```bash
dot-agent run gt update-pr
```

**What this does:**

1. Gets current branch and checks for associated PR
2. Checks for uncommitted changes
3. If changes exist: stages and commits with message "Update changes"
4. Runs `gt restack --no-interactive` to restack the branch
5. Runs `gt submit` to update the PR
6. Returns JSON with PR info and status

**Parse the JSON output** to get:

- `success`: Boolean indicating success/failure
- `pr_number`: PR number (if success)
- `pr_url`: PR URL (if success)
- `branch_name`: Current branch name
- `had_changes`: Whether uncommitted changes were committed
- `message`: Human-readable status message

**Error handling:**

Parse the error JSON and handle by error_type:

- `no_pr`: No PR associated with current branch → Show error with suggestion to use /gt:submit-branch
- `commit_failed`: Failed to commit changes → Show error and exit
- `restack_failed`: Conflicts during restack → Show error with manual resolution instructions
- `submit_failed`: Failed to submit → Show error and exit

### Error Messages

**No PR Error:**

```
❌ No PR associated with current branch

Create one with:
  /gt:submit-branch
```

**Restack Conflict Error:**

```
❌ Conflicts occurred during restack

Resolve conflicts manually, then run this command again:
  /gt:update-pr
```

**Other Errors:**

Show the error message from the JSON output and exit.

### Success Output

After successful execution, show results:

```
✅ PR updated successfully

- **PR #**: [number]
- **URL**: [url]
- **Branch**: [branch_name]
- **Changes Committed**: [Yes/No based on had_changes]
```

## Example Output

### Success with Uncommitted Changes

```
Running update-pr command...
✓ Command completed successfully

✅ PR updated successfully

- **PR #**: 235
- **URL**: https://app.graphite.com/github/pr/dagster-io/erk/235
- **Branch**: gt-update-pr-command
- **Changes Committed**: Yes
```

### Success with No Uncommitted Changes

```
Running update-pr command...
✓ Command completed successfully

✅ PR updated successfully

- **PR #**: 235
- **URL**: https://app.graphite.com/github/pr/dagster-io/erk/235
- **Branch**: gt-update-pr-command
- **Changes Committed**: No
```

### No PR Error

```
Running update-pr command...
✗ Command failed

❌ No PR associated with current branch

Create one with:
  /gt:submit-branch
```

### Restack Conflict Error

```
Running update-pr command...
✗ Command failed

❌ Conflicts occurred during restack

Resolve conflicts manually, then run this command again:
  /gt:update-pr
```

## Notes

- Uses simple default commit message: "Update changes"
- Does NOT use AI-generated commit messages (optimized for speed)
- Aborts immediately on restack conflicts - requires manual resolution
- Uses `gh` CLI to check PR existence (requires GitHub CLI authentication)
- Uses `gt` CLI for restack and submit operations
