---
description: Update PR by staging changes, committing, restacking, and submitting
---

# Update PR

Streamlined workflow to update an existing PR with fail-fast execution and natural error messages.

## Usage

```bash
/gt:pr-update
```

## Output

**Success:**

```json
{
  "success": true,
  "pr_number": 123,
  "pr_url": "https://github.com/org/repo/pull/123"
}
```

**Error:**

```json
{
  "success": false,
  "error": "No PR associated with current branch"
}
```

## When to Use

- Update an existing PR with new changes
- Quick iteration on PR feedback

## Implementation

When this command is invoked:

### Step 1: Execute Update Workflow

Delegate to the gt-update-pr-submitter agent:

```
Task(
    subagent_type="gt-update-pr-submitter",
    description="Update PR workflow",
    prompt="Execute the pr-update workflow to update the existing PR with new changes"
)
```

The agent executes a single atomic command and reports results.

### Step 2: Validate PR Rules

If Step 1 succeeded, run the PR check command to validate the PR:

```bash
erk pr check
```

This validates:

- Issue closing reference (Closes #N) is present when `.impl/issue.json` exists
- PR body contains the standard checkout footer

If any checks fail, display the output and warn the user.
