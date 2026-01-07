---
title: GitHub Issue Auto-Close Behavior
read_when:
  - "implementing PR-to-issue linking"
  - "debugging why issues didn't auto-close after PR merge"
  - "understanding closing keyword behavior"
  - "working with plan issue closure detection"
---

# GitHub Issue Auto-Close Behavior

GitHub can automatically close issues when PRs containing closing keywords are merged. However, this feature has important quirks that affect erk's plan issue workflow.

## How Closing Keywords Work

When a PR body or commit message contains patterns like `Closes #123` or `Fixes owner/repo#456`, GitHub links the issue to the PR and auto-closes the issue when the PR merges.

### Supported Patterns

Same-repo references:

- `Closes #123`
- `Fixes #123`
- `Resolves #123`

Cross-repo references (for separate plans repo):

- `Closes owner/repo#123`
- `Fixes owner/repo#123`

## Critical Quirk: Timing of Closing Keywords

**Closing keywords must be present in the PR body at PR creation time.**

Adding `Closes #123` to a PR body after the PR is already created does NOT create the issue linkage. GitHub only parses closing keywords when:

1. The PR is first created
2. Commits are pushed that contain closing keywords

This means if a PR is created without the closing keyword, editing the body later to add it will NOT trigger auto-close.

### Why This Matters for Erk

When `erk pr submit` creates a PR, it includes `Closes #N` in the body. If this line is somehow missing or the PR was created manually:

- The issue won't be linked to the PR
- Merging the PR won't auto-close the issue
- Users will see a warning after landing

## Auto-Close is Asynchronous

When a PR merges, GitHub closes linked issues **asynchronously**. There's typically a 1-3 second delay between:

1. PR merge completing (merge API returns success)
2. Linked issues being closed

### Detection Strategy in Erk

`check_and_display_plan_issue_closure()` handles this by:

1. **If PR has closing reference + issue still open**: Retry up to 3 times with 1-second delays. This accounts for the async delay.

2. **If PR missing closing reference + issue still open**: Show a different warning explaining the issue won't auto-close (the bug case).

3. **If issue already closed**: Success regardless of PR body.

## Implementation Reference

- `src/erk/cli/commands/objective_helpers.py`: `check_and_display_plan_issue_closure()`
- `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`: `has_issue_closing_reference()`

## Debugging Tips

1. **Issue didn't auto-close?** Check if the PR body at creation time contained the closing keyword. Look at the first version of the PR body, not the current one.

2. **Manual workaround**: If the closing keyword was added after creation, manually close the issue or create a commit with `Fixes #N` in the message.

3. **Cross-repo issues**: Ensure the full reference format is used: `Closes owner/repo#123`, not just `Closes #123`.
