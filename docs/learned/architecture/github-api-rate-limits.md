---
title: GitHub API Rate Limits
read_when:
  - "using gh CLI commands programmatically"
  - "encountering GraphQL rate limit errors"
  - "choosing between REST and GraphQL API"
  - "implementing GitHub API calls in gateways"
tripwires:
  - action: "using gh issue create in production code"
    warning: "Use REST API via `gh api repos/{owner}/{repo}/issues -X POST` instead. `gh issue create` uses GraphQL which has separate (often exhausted) rate limits."
  - action: "using gh pr create in production code"
    warning: "Use REST API via `gh api repos/{owner}/{repo}/pulls -X POST` instead. `gh pr create` uses GraphQL which has separate (often exhausted) rate limits."
  - action: "using gh issue view in command documentation"
    warning: "Use `erk exec get-issue-body` instead. `gh issue view` uses GraphQL which has separate (often exhausted) rate limits."
  - action: "using gh issue edit in command documentation"
    warning: "Use `erk exec update-issue-body` instead. `gh issue edit` uses GraphQL which has separate (often exhausted) rate limits."
  - action: "using gh pr view --json merged"
    warning: "The `merged` field doesn't exist. Use `mergedAt` instead. Run `gh pr view --help` or check error output for valid field names."
  - action: "using gh api or gh api graphql to fetch or resolve PR review threads"
    warning: "Load `pr-operations` skill first. Use `erk exec get-pr-review-comments` and `erk exec resolve-review-thread` instead. Raw gh api calls miss thread resolution functionality."
---

# GitHub API Rate Limits

GitHub has **separate rate limits** for REST API and GraphQL API. This document explains the distinction and why erk uses REST API for all programmatic GitHub operations.

## Rate Limit Quotas

| API Type    | Limit               | Scope                  |
| ----------- | ------------------- | ---------------------- |
| REST API    | 5,000 requests/hour | Per authenticated user |
| GraphQL API | 5,000 points/hour   | Per authenticated user |

**Key insight**: These are **separate quotas**. Exhausting GraphQL quota does not affect REST quota, and vice versa.

## The Problem with `gh` Porcelain Commands

Many `gh` CLI "porcelain" commands (the user-friendly ones) use **GraphQL internally**:

| Command           | Uses GraphQL? | REST Alternative                                   |
| ----------------- | ------------- | -------------------------------------------------- |
| `gh issue create` | Yes           | `gh api repos/{owner}/{repo}/issues -X POST`       |
| `gh pr create`    | Yes           | `gh api repos/{owner}/{repo}/pulls -X POST`        |
| `gh issue view`   | Yes           | `erk exec get-issue-body <number>`                 |
| `gh issue edit`   | Yes           | `erk exec update-issue-body <number> --body "..."` |
| `gh pr view`      | Yes           | `gh api repos/{owner}/{repo}/pulls/{number}`       |
| `gh api <path>`   | **No**        | Direct REST API access                             |

When you hit the error:

```
GraphQL: API rate limit already exceeded for user ID ...
```

The `gh` porcelain commands stop working, but `gh api` REST calls continue to work.

## The Pattern: Always Use `gh api` for Programmatic Access

In erk's GitHub gateways, we always use `gh api` with REST endpoints:

```python
# BANNED: Uses GraphQL, hits rate limits
base_cmd = ["gh", "issue", "create", "--title", title, "--body", body]

# CORRECT: Uses REST API, separate quota
base_cmd = [
    "gh", "api", "repos/{owner}/{repo}/issues",
    "-X", "POST",
    "-f", f"title={title}",
    "-f", f"body={body}",
]
```

## REST API Reference

### Creating Issues

```bash
gh api repos/{owner}/{repo}/issues \
  -X POST \
  -f title="Issue title" \
  -f body="Issue body" \
  -f "labels[]=bug" \
  -f "labels[]=priority-high"
```

### Creating Pull Requests

```bash
gh api repos/{owner}/{repo}/pulls \
  -X POST \
  -f title="PR title" \
  -f body="PR body" \
  -f head="feature-branch" \
  -f base="main"
```

### Updating Issues/PRs

```bash
gh api repos/{owner}/{repo}/issues/{number} \
  -X PATCH \
  -f body="Updated body"
```

### Handling Large Bodies

Large body content (3,500+ characters) can fail with shell argument length limits or trigger GitHub's abuse detection. Use the `-F body=@{filepath}` syntax to read content from a file:

```bash
# Write content to temp file, then pass via -F with @ prefix
gh api repos/{owner}/{repo}/pulls/{number} \
  -X PATCH \
  -f title="PR title" \
  -F body=@/tmp/pr-body.md
```

**Gateway API Pattern**: The gateway methods accept `body: str | Path`:

```python
# Pass string for small bodies
github.update_pr_title_and_body(repo_root=root, pr_number=123, title="Title", body="Small body")

# Pass Path for large bodies (reads from file using -F body=@path)
github.update_pr_title_and_body(repo_root=root, pr_number=123, title="Title", body=body_file)
```

The gateway uses `isinstance(body, Path)` to determine which `gh api` syntax to use.

### Adding Comments

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments \
  -X POST \
  -f body="Comment text"
```

## Extracting Data from Responses

Use `--jq` to extract fields from JSON responses:

```bash
# Get issue number and URL
gh api repos/{owner}/{repo}/issues -X POST \
  -f title="Test" \
  -f body="Test" \
  --jq '"\(.number) \(.html_url)"'

# Get just the ID
gh api repos/{owner}/{repo}/issues/{number}/comments \
  -X POST \
  -f body="Comment" \
  --jq ".id"
```

## Rate Limits vs Transient Errors

Erk has a [retry mechanism](github-api-retry-mechanism.md) for transient network errors, but **rate limits are NOT retried**.

| Error Type       | Retried? | Why                                       |
| ---------------- | -------- | ----------------------------------------- |
| Network timeout  | Yes      | Transient, likely succeeds on retry       |
| Connection reset | Yes      | Transient, likely succeeds on retry       |
| Rate limit       | No       | Persistent until quota resets (up to 1hr) |
| Auth failure     | No       | Configuration issue, won't fix on retry   |

**Rationale**: Rate limit errors indicate quota exhaustion. Retrying immediately wastes time and may trigger abuse detection. The correct response is to either wait for quota reset or switch to REST API (separate quota).

## Implementation Reference

See `packages/erk-shared/src/erk_shared/github/issues/real.py` for examples of REST API usage in erk's GitHub gateway.
