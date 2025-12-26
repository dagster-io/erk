---
description: Create git commit and submit current branch with Graphite
argument-hint: <description>
---

# Submit Branch

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/gt:submit-branch "Add user authentication feature"

# Without argument (will analyze changes automatically)
/gt:submit-branch
```

## What This Command Does

Delegates the complete submit-branch workflow to the `gt-branch-submitter` agent, which handles:

1. Check for uncommitted changes and commit them if needed
2. Run pre-analysis phase (squash commits, get branch info)
3. Analyze all changes and generate commit message
4. Run post-analysis phase (amend commit, submit branch, update PR)
5. Report results

## Implementation

When this command is invoked, delegate to the gt-branch-submitter agent:

```
Task(
    subagent_type="gt-branch-submitter",
    description="Submit branch workflow",
    prompt="Execute the complete submit-branch workflow for the current branch"
)
```

The agent handles all workflow orchestration, error handling, and result reporting.
