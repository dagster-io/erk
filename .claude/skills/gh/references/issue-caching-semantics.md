# GitHub Issue Timestamp Semantics for Caching

## Overview

When implementing caching strategies for GitHub issues, the `updatedAt` timestamp
is a reliable signal for cache invalidation. This document describes what operations
update `updatedAt` and what does not.

## `updatedAt` Timestamp Behavior

### Operations That UPDATE `updatedAt`

These operations cause the issue's `updatedAt` timestamp to change:

| Operation            | API/CLI                                          | Notes                                               |
| -------------------- | ------------------------------------------------ | --------------------------------------------------- |
| Add comment          | `gh issue comment`                               | ~2s delay between comment creation and issue update |
| Edit issue body      | `gh issue edit --body`                           | Immediate                                           |
| Edit issue title     | `gh issue edit --title`                          | Immediate                                           |
| Add/remove labels    | `gh issue edit --add-label/--remove-label`       | Immediate                                           |
| Close/reopen issue   | `gh issue close/reopen`                          | Immediate                                           |
| Add/remove assignees | `gh issue edit --add-assignee/--remove-assignee` | Immediate                                           |
| Add/remove milestone | `gh issue edit --milestone`                      | Immediate                                           |
| Lock/unlock issue    | API only                                         | Immediate                                           |

### Operations That DO NOT Update `updatedAt`

These operations do NOT change the issue's `updatedAt`:

| Operation             | Notes                                         |
| --------------------- | --------------------------------------------- |
| Add reactions (emoji) | Confirmed: reactions don't update `updatedAt` |
| View issue            | Read-only operations never update             |
| Subscribe/unsubscribe | User preference, not issue state              |

## Empirical Verification

Verified on GitHub issue (2025-12-01):

```
Issue created:    22:37:49Z
Comment 1 added:  22:37:50Z
Comment 2 added:  22:39:10Z
Issue updatedAt:  22:39:12Z  (2 seconds after last comment)
```

The ~2 second delay between comment creation and `updatedAt` change is normal
GitHub processing time.

## Caching Strategy Implications

1. **Comments reliably update `updatedAt`** - Safe to use for cache invalidation
2. **All write mutations update `updatedAt`** - Any state change triggers update
3. **Reactions are invisible** - Don't rely on `updatedAt` for reaction changes
4. **Small timing delay** - Allow ~2-3 seconds for `updatedAt` to propagate

## Lightweight Timestamp Queries

Fetch only timestamps for cache validation:

```bash
# Single issue
gh issue view 123 --json updatedAt

# Multiple issues (with filters)
gh issue list --json number,updatedAt --label my-label --state open
```

Payload size: ~50 bytes/issue vs ~2KB/issue for full data.

## Implementing a Caching Wrapper

### Cache Strategy for `get_issue()`

1. Fetch lightweight timestamp via `gh issue view --json updatedAt`
2. Compare with cached entry (if exists)
3. Return cached if timestamps match, fetch full otherwise

### Cache Strategy for `list_issues()`

1. Always fetch lightweight timestamps via `gh issue list --json number,updatedAt`
2. Compare each issue's `updated_at` against cache
3. Batch-fetch only changed/missing issues via GraphQL
4. Return combined results from cache + fresh fetch

### Cache Invalidation

All write operations (add comment, update body, add/remove labels, close)
should invalidate the cache entry for that issue.

### API Call Efficiency

| Scenario                  | Before      | After (cold)                | After (warm)                |
| ------------------------- | ----------- | --------------------------- | --------------------------- |
| `list_issues` (50 issues) | 1 full call | 1 lightweight + 1 batch     | 1 lightweight only          |
| `list_issues` (5 changed) | 1 full call | 1 lightweight + 1 batch (5) | 1 lightweight + 1 batch (5) |
| `get_issue`               | 1 full call | 1 lightweight + 1 full      | 1 lightweight only          |

Payload reduction: ~50 bytes/issue for timestamps vs ~2KB/issue for full data.

## Known Limitations

1. **Reactions not tracked** - If your application cares about reactions,
   you cannot use `updatedAt` for caching
2. **External edits** - Edits made outside your application still update
   `updatedAt`, which is correct behavior for cache invalidation
3. **Timing precision** - Don't compare timestamps with sub-second precision

## References

- [GitHub Community Discussion #79024](https://github.com/orgs/community/discussions/79024) -
  Confirms reactions don't update `updatedAt`
