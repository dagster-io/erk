---
title: GitHub Issue-PR Linkage API Patterns
read_when:
  - "querying PRs linked to an issue"
  - "understanding how GitHub tracks issue-PR relationships"
  - "debugging why a PR doesn't show as linked to an issue"
  - "working with CrossReferencedEvent or closingIssuesReferences"
---

# GitHub Issue-PR Linkage API Patterns

This document describes how to query the relationship between GitHub issues and pull requests using the GitHub GraphQL API.

## Two API Approaches

GitHub provides two different ways to find PRs related to an issue:

| Approach                  | Returns             | Direction   | Use Case                          |
| ------------------------- | ------------------- | ----------- | --------------------------------- |
| `closingIssuesReferences` | Only closing PRs    | PR → Issues | Finding issues a PR closes        |
| `CrossReferencedEvent`    | ALL referencing PRs | Issue → PRs | Finding PRs that mention an issue |

### The Common Pitfall

**Wrong approach**: Using `closingIssuesReferences` to find PRs for an issue.

```graphql
# ❌ WRONG: This queries FROM a PR, not TO a PR
query {
  repository(owner: "owner", name: "repo") {
    pullRequest(number: 123) {
      closingIssuesReferences(first: 10) {
        nodes {
          number
        } # Returns ISSUES this PR closes
      }
    }
  }
}
```

This returns issues that the PR will close, not PRs that reference the issue.

**Correct approach**: Use timeline events on the issue to find referencing PRs:

```graphql
# ✅ CORRECT: Query timeline events FROM the issue
query {
  repository(owner: "owner", name: "repo") {
    issue(number: 100) {
      timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20) {
        nodes {
          ... on CrossReferencedEvent {
            willCloseTarget
            source {
              ... on PullRequest {
                number
                state
                url
              }
            }
          }
        }
      }
    }
  }
}
```

## The willCloseTarget Field

[`CrossReferencedEvent.willCloseTarget`](https://docs.github.com/en/graphql/reference/objects#crossreferencedevent) indicates whether the referencing PR will automatically close the issue when merged.

| willCloseTarget | Meaning                                               |
| --------------- | ----------------------------------------------------- |
| `true`          | PR body contains "Closes #N" (or equivalent keyword)  |
| `false`         | PR merely mentions the issue without closing keywords |

**Critical timing detail**: `willCloseTarget` is determined at PR creation time. Editing the PR body afterward to add "Closes #N" does NOT update this field. This behavior is documented in [GitHub community discussion #24706](https://github.com/orgs/community/discussions/24706).

### Implications for Erk

The `erk submit` command must include "Closes #N" in the **initial** PR body passed to `create_pr()`, not added via a subsequent body update. See `src/erk/cli/commands/submit.py` for the implementation.

## When to Use Each Approach

### Use CrossReferencedEvent (Issue → PRs) When:

- Finding all PRs that reference an issue
- Building a dashboard showing issue-to-PR mappings
- Need to know which PRs will close vs merely mention an issue
- Query efficiency matters (O(issues) instead of O(all PRs))

### Use closingIssuesReferences (PR → Issues) When:

- Finding which issues a specific PR will close
- Verifying a PR's closing references are correct

## Erk Implementation

Erk uses `CrossReferencedEvent` to query issue-PR linkages:

- **Query location**: `packages/erk-shared/src/erk_shared/github/real.py`
- **Method**: `get_prs_linked_to_issues()` for batch queries (dash)
- **Method**: `get_prs_referencing_issue()` for single-issue queries (plan list)
- **Field mapping**: GraphQL `willCloseTarget` → `PullRequestInfo.will_close_target`

## Debugging PR Linkages

If a PR doesn't appear linked to an issue:

1. **PR not showing at all**: The PR may not reference the issue in its body or commits
2. **willCloseTarget is false**: The PR was created without "Closes #N" in the initial body
3. **Stale data**: GitHub's timeline events may have a short propagation delay

To verify linkage status via CLI:

```bash
# Check issue timeline for cross-references
gh api graphql -f query='
  query {
    repository(owner: "OWNER", name: "REPO") {
      issue(number: ISSUE_NUMBER) {
        timelineItems(itemTypes: [CROSS_REFERENCED_EVENT], first: 20) {
          nodes {
            ... on CrossReferencedEvent {
              willCloseTarget
              source {
                ... on PullRequest { number url }
              }
            }
          }
        }
      }
    }
  }
'
```

## Related Topics

- [GitHub GraphQL API Patterns](github-graphql.md) - Variable passing and query organization
- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Handling PR lookup failures
- [Issue-PR Linkage Storage](../erk/issue-pr-linkage-storage.md) - How erk creates and stores linkages
