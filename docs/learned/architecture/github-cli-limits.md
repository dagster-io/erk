---
title: GitHub CLI Limits
read_when:
  - "using gh pr diff in production code"
  - "working with large pull requests (300+ files)"
  - "encountering HTTP 406 errors from gh CLI"
  - "implementing PR file discovery"
tripwires:
  - action: "using gh pr diff --name-only in production code"
    warning: "For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead."
---

# GitHub CLI Limits

The GitHub CLI has undocumented size limits that cause failures on large PRs. This document covers the limitations and workarounds.

## The Problem

`gh pr diff --name-only` fails on PRs with 300+ files:

```bash
gh pr diff 123 --name-only
# Error: HTTP 406: Not Acceptable (https://api.github.com/...)
```

This happens because `gh pr diff` requests the entire diff in a single API call without pagination support. GitHub's API rejects requests for diffs that are too large.

## The Solution: REST API with Pagination

Use the GitHub REST API `/repos/{owner}/{repo}/pulls/{pr}/files` endpoint, which supports pagination:

```bash
gh api \
  --paginate \
  --jq '.[].filename' \
  "repos/{owner}/{repo}/pulls/${PR_NUMBER}/files"
```

### Key Differences

| Method | Pagination | Size Limit | Failure Mode |
|--------|------------|------------|--------------|
| `gh pr diff --name-only` | No | ~300 files | HTTP 406 error |
| `gh api repos/.../pulls/.../files` | Yes (`--paginate`) | No limit | None |

## Implementation Pattern

See `src/erk/commands/exec/discover_reviews.py` for the production implementation:

```python
# DON'T: Use gh pr diff (fails on large PRs)
result = subprocess.run(["gh", "pr", "diff", pr_number, "--name-only"])

# DO: Use REST API with pagination
files = github.list_pr_files(pr_number=pr_number)
```

The `GitHubGateway.list_pr_files()` method handles pagination automatically.

## Why This Matters

PR #6119 fixed a bug where `erk exec discover-reviews` failed on large PRs. The original implementation used `gh pr diff`, which worked fine on small PRs but broke silently on large ones.

This is a production tripwire: code that works in testing (small PRs) fails in production (large refactors).

## Related Documentation

- [Universal Tripwires](../universal-tripwires.md) - Lists the gh pr diff tripwire
- [Gateway ABC Implementation](gateway-abc-implementation.md) - How GitHubGateway abstracts this
