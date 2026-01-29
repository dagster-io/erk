---
title: PR Creation Decision Logic
read_when:
  - "creating a PR programmatically"
  - "detecting if a PR already exists for a branch"
  - "implementing PR creation in exec scripts"
---

# PR Creation Decision Logic

When workflows create PRs programmatically, they must handle the case where a PR already exists for the current branch. Creating a duplicate PR causes confusion and orphaned PRs.

## Existing PR Detection Pattern

Before creating a new PR, check if one already exists:

```bash
gh pr view --json number --jq '.number' 2>/dev/null
```

- **Exit 0 with number**: PR exists — update it instead of creating a new one
- **Non-zero exit**: No PR exists — safe to create

This is the "Step 6.5" pattern from the learn workflow: always check before creating.

## Decision Flow

1. Check if current branch has an open PR
2. If PR exists: update title/body with `gh pr edit`
3. If no PR: create with `gh pr create`

## Reusable Pattern

This check-before-create pattern applies to any workflow that creates PRs:

- Learn workflow creating documentation PRs
- Plan-implement creating feature PRs
- Review workflow creating review PRs

The pattern prevents duplicate PRs that clutter the repository and confuse reviewers.

## Related Topics

- [PR Submit Phases](pr-submit-phases.md) — Full PR submission workflow
- [Learn Workflow](../planning/learn-workflow.md) — Uses this pattern in Step 6.5
