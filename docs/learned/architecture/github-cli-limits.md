---
title: GitHub CLI Limits
last_audited: "2026-02-04 05:48 PT"
audit_result: edited
read_when:
  - "using gh pr diff in production code"
  - "working with large pull requests (300+ files)"
  - "encountering HTTP 406 errors from gh CLI"
  - "implementing PR file discovery"
  - "working with GitHub codespaces in code"
  - "implementing codespace operations"
tripwires:
  - action: "using gh pr diff --name-only in production code"
    warning: "For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead."
  - action: "using gh codespace start"
    warning: "gh codespace start does not exist. Use REST API POST /user/codespaces/{name}/start via gh api instead."
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

| Method                             | Pagination         | Size Limit | Failure Mode   |
| ---------------------------------- | ------------------ | ---------- | -------------- |
| `gh pr diff --name-only`           | No                 | ~300 files | HTTP 406 error |
| `gh api repos/.../pulls/.../files` | Yes (`--paginate`) | No limit   | None           |

## Implementation Pattern

See `src/erk/cli/commands/exec/scripts/discover_reviews.py` for the production implementation, which uses `github.get_pr_changed_files()` with automatic pagination.

## Why This Matters

PR #6119 fixed a bug where `erk exec discover-reviews` failed on large PRs. The original implementation used `gh pr diff`, which worked fine on small PRs but broke silently on large ones.

This is a production tripwire: code that works in testing (small PRs) fails in production (large refactors).

## gh codespace start Does Not Exist

The GitHub CLI does not provide a `gh codespace start` command. Attempting to use it fails:

```bash
gh codespace start mycodespace
# Error: unknown command "start" for "gh codespace"
```

### The Solution: REST API

Use the REST API endpoint `/user/codespaces/{name}/start` via `gh api`:

```bash
gh api \
  --method POST \
  "user/codespaces/${CODESPACE_NAME}/start"
```

This returns JSON with the codespace state. The operation is asynchronous - the codespace may still be starting when the API call returns.

### Implementation Pattern

See `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` for the production implementation using `gh api --method POST user/codespaces/{name}/start`.

## GH-API-AUDIT Annotation Convention

To track GitHub CLI commands that should be audited for potential REST/GraphQL API replacements, use the `GH-API-AUDIT` annotation:

```python
# GH-API-AUDIT: [REST/GraphQL] - [operation description]
subprocess.run(["gh", "pr", "view", pr_number])
```

### Format

- **`REST`**: Operation has a known REST API endpoint
- **`GraphQL`**: Operation may be better served by GraphQL
- **Operation description**: Brief explanation of what the command does

### Examples from Codebase

```python
# GH-API-AUDIT: REST - Get PR number from branch
result = subprocess.run(["gh", "pr", "view", "--json", "number"])

# GH-API-AUDIT: GraphQL - Fetch issue comments
result = subprocess.run(["gh", "issue", "view", issue_number, "--json", "comments"])
```

### Purpose

This convention identifies 66+ locations in the gateway code where we're using `gh` CLI commands that could potentially be replaced with direct REST or GraphQL API calls for better performance, error handling, or functionality.

## GitHub Machines Endpoint HTTP 500 Bug

The machines endpoint (`/repos/{owner}/{repo}/codespaces/machines`) returns HTTP 500 for certain repositories. The workaround uses `POST /user/codespaces` with `repository_id` instead.

**Full diagnostic methodology and workaround**: See [GitHub API Diagnostics](github-api-diagnostics.md).
**Implementation**: See `src/erk/cli/commands/codespace/setup_cmd.py`.
**Default machine type**: `premiumLinux`

## Related Documentation

- [GitHub API Diagnostics](github-api-diagnostics.md) - Repository-specific diagnostic methodology
- [Universal Tripwires](../universal-tripwires.md) - Lists the gh pr diff tripwire
- [Gateway ABC Implementation](gateway-abc-implementation.md) - How GitHubGateway abstracts this
- [Codespace Patterns](../cli/codespace-patterns.md) - Codespace setup patterns
