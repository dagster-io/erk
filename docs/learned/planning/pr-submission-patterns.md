---
title: PR Submission Patterns
read_when:
  - "creating PRs programmatically"
  - "implementing idempotent PR submission"
  - "handling retry logic for PR operations"
---

# PR Submission Patterns

Patterns for reliable, idempotent PR creation and submission.

## Idempotent PR Submission

PR submission operations should be idempotent: running them multiple times produces the same result as running once.

### The Problem

Without idempotency checks:

1. First run: Creates PR #123
2. Hook blocks → retry
3. Second run: Creates duplicate PR #124
4. Now have two PRs for same work

### The Solution: Existing PR Detection

Before creating a PR, check if one already exists for the branch:

```bash
# Check for existing PR by branch name
EXISTING_PR=$(gh pr list --head "$BRANCH_NAME" --json number -q '.[0].number' 2>/dev/null || echo "")

if [ -n "$EXISTING_PR" ]; then
  echo "PR #$EXISTING_PR already exists for branch $BRANCH_NAME"
  # Update existing PR instead of creating new one
  gh pr edit "$EXISTING_PR" --title "$TITLE" --body "$BODY"
else
  # Create new PR
  gh pr create --title "$TITLE" --body "$BODY"
fi
```

### Branch-Based Discovery

Use `--head` flag for branch-based PR discovery:

| Method            | Reliability | Notes                      |
| ----------------- | ----------- | -------------------------- |
| `--head $BRANCH`  | High        | Exact match on branch name |
| Body text search  | Low         | Can match unrelated PRs    |
| PR number storage | Medium      | Requires persistent state  |

### Session-Scoped Idempotency

For session-aware operations (like plan-save), track created artifacts by session ID:

1. Check if artifact was created for this session ID
2. If found, return existing artifact
3. If not found, create and record

This prevents duplicate issues when retry loops occur.

## PR Body Generation

### Consistent Structure

PR bodies should follow a consistent structure:

```markdown
## Summary

[Brief description of changes]

## Plan

#123 <!-- Links to plan issue -->

## Changes

- Change 1
- Change 2

---

<!-- Footer with checkout instructions -->
```

### Checkout Footer Pattern

Include checkout instructions in a standard format:

```markdown
`gh pr checkout 456`
```

**Important:** Use plain text backtick format, not HTML `<details>` tags. The `has_checkout_footer_for_pr()` validation expects the backtick format.

### Closing Reference

Ensure PRs include issue closing keywords in the commit message (not just PR body):

- Commit message: `Implements feature X\n\nCloses #123`
- PR body: `**Plan:** #123` (for reference, not closing)

GitHub only auto-closes issues from merge commit messages, not PR bodies.

## Concurrent Submission Safety

When multiple submissions might occur simultaneously:

### Race Condition Avoidance

```bash
# Use atomic check-and-create pattern
# Note: This is pseudo-code - actual implementation may vary

# 1. Check for existing PR
PR_NUMBER=$(gh pr list --head "$BRANCH" --json number -q '.[0].number')

# 2. If not found, attempt creation
if [ -z "$PR_NUMBER" ]; then
  PR_NUMBER=$(gh pr create ... --json number -q '.number')
fi

# 3. Use PR_NUMBER for all subsequent operations
gh pr edit "$PR_NUMBER" ...
```

### Retry Strategy

For operations that might fail transiently:

1. **Check existing first**: Always check for existing artifact before creating
2. **Create if missing**: Only create when check confirms nothing exists
3. **Update on conflict**: If creation fails due to conflict, fall back to update

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Full plan lifecycle including PR creation
- [Submit Branch Reuse](submit-branch-reuse.md) - Branch reuse detection in plan submit
