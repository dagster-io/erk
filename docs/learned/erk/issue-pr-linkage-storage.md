---
title: Issue-PR Linkage Storage Model
read_when:
  - "understanding how plans link to PRs"
  - "debugging why a PR isn't linked to its issue"
  - "working with .impl/plan-ref.json or .impl/issue.json"
  - "creating PRs that close issues"
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Issue-PR Linkage Storage Model

This document describes how erk creates and stores the relationship between GitHub issues (plans) and pull requests.

## Overview

When a plan becomes a PR, erk establishes a linkage that allows:

- `erk pr list` to show which plans have associated PRs
- PRs to automatically close their source issue when merged
- The 🔗 indicator to appear for auto-closing PRs

## How Linkages Are Created

### Via `erk pr submit`

The primary path for creating issue-PR linkages:

1. Creates branch from plan issue (e.g., `P123-feature-12-11-0948`)
2. Creates `.erk/impl-context/` folder with `ref.json` containing plan reference
3. Creates draft PR with `Closes #N` in **initial** body
4. GitHub registers the `CrossReferencedEvent` with `willCloseTarget: true`

**Key implementation**: `src/erk/cli/commands/pr/dispatch_cmd.py`

### Via `/erk:pr-submit` or `/erk:git-pr-push`

Slash commands that create PRs read the issue reference from local storage:

1. Check for `.impl/plan-ref.json` or `.erk/impl-context/ref.json` (with legacy fallback to `issue.json`)
2. If found, append `Closes #N` to PR body
3. Uses `erk exec get-closing-text` to read the reference

**Key implementation**: `src/erk/cli/commands/exec/scripts/get_closing_text.py`

## Storage Locations

### Local Worktree: `.impl/plan-ref.json` (primary) / `.impl/issue.json` (legacy)

The primary format (`.impl/plan-ref.json`):

```json
{
  "provider": "github-draft-pr",
  "plan_id": "123",
  "url": "https://github.com/owner/repo/pull/123",
  "created_at": "2025-01-15T10:30:00+00:00",
  "synced_at": "2025-01-15T10:30:00+00:00"
}
```

The legacy format (`.impl/issue.json`, still supported via `read_plan_ref()` fallback):

```json
{
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123",
  "created_at": "2025-01-15T10:30:00+00:00",
  "synced_at": "2025-01-15T10:30:00+00:00"
}
```

This file maps the current worktree to its source GitHub issue.

- Created by `erk pr submit` (as `.erk/impl-context/`)
- Created by `erk wt create --from-plan` (as `.impl/`)
- Read by slash commands when creating PRs

### PR Body: `Closes #N`

The "Closes" keyword (or equivalent: "Fixes", "Resolves") in the PR body triggers GitHub's issue auto-close behavior. See [GitHub's documentation on linking keywords](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests).

**Critical**: Must be in the **initial** PR body at creation time. See [willCloseTarget timing detail](#willclosetarget-timing).

### GitHub Timeline Events

GitHub stores cross-reference events on the issue timeline. These are what erk queries to display linkages in `erk pr list`.

See [GitHub Issue-PR Linkage API Patterns](../architecture/github-pr-linkage-api.md) for query details.

## How Linkages Are Queried

### `erk pr list`

Uses GraphQL to query `CrossReferencedEvent` timeline items on each plan issue:

1. Fetches all issues with `erk-plan` label
2. For each issue, queries timeline for cross-references
3. Extracts PR info including `willCloseTarget` field
4. Displays 🔗 indicator for PRs that will close the issue

**Display format**: `#123 🔗` indicates PR #123 will close the issue when merged.

### `erk dash`

Uses batch queries via `get_prs_linked_to_issues()` for efficient dashboard display.

## willCloseTarget Timing

**Important behavior**: GitHub's `willCloseTarget` field is set at PR creation time only. This field is part of the [`CrossReferencedEvent` GraphQL type](https://docs.github.com/en/graphql/reference/objects#crossreferencedevent).

| Action                                       | Result                              |
| -------------------------------------------- | ----------------------------------- |
| Create PR with `Closes #N` in body           | `willCloseTarget: true`             |
| Create PR, then edit body to add `Closes #N` | `willCloseTarget: false`            |
| Create PR with `Closes #N`, then remove it   | `willCloseTarget: true` (unchanged) |

This timing behavior is documented in [GitHub community discussion #24706](https://github.com/orgs/community/discussions/24706). This is why `erk pr submit` passes the "Closes" text to `create_pr()` rather than adding it via `update_pr_body()`.

## Debugging Linkage Issues

### PR Not Showing in `erk pr list`

1. **No cross-reference exists**: PR body/commits don't mention the issue number
2. **Wrong issue number**: Check `.impl/plan-ref.json` (or legacy `.impl/issue.json`) contains correct plan ID
3. **API propagation delay**: Wait a moment and refresh

### 🔗 Not Appearing (willCloseTarget is False)

The PR was created without `Closes #N` in the initial body:

- PR was created manually without the keyword
- PR was created via a tool that adds the keyword after creation
- The `.impl/plan-ref.json` was missing when the PR was created

**Resolution**: Close the PR and create a new one with the closing keyword in the initial body.

### Verifying Linkage Status

```bash
# Check local plan reference
cat .impl/plan-ref.json  # or legacy: cat .impl/issue.json

# Check PR body for closing keywords
gh pr view --json body -q '.body'

# Check GitHub's timeline (shows willCloseTarget)
# See debugging section in github-pr-linkage-api.md
```

## Key Files

| Purpose                  | Location                                                     |
| ------------------------ | ------------------------------------------------------------ |
| Issue reference reading  | `packages/erk-shared/src/erk_shared/impl_folder.py`          |
| PR creation with Closes  | `src/erk/cli/commands/pr/`                                   |
| Get closing text command | `src/erk/cli/commands/exec/scripts/get_closing_text.py`      |
| Timeline event parsing   | `packages/erk-shared/src/erk_shared/gateway/github/real.py`  |
| PullRequestInfo type     | `packages/erk-shared/src/erk_shared/gateway/github/types.py` |

## Related Topics

- [GitHub Issue-PR Linkage API Patterns](../architecture/github-pr-linkage-api.md) - API patterns for querying linkages
- [Plan Lifecycle](../planning/lifecycle.md) - Full plan lifecycle from creation to landing
