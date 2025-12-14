---
title: GitHub REST API Patterns
read_when:
  - "using gh api for REST endpoints"
  - "converting from gh issue/pr commands to REST"
  - "handling GitHub API response fields"
tripwires:
  - action: "expecting author.login in REST API response"
    warning: "REST uses user.login, not author.login. GraphQL uses author.login."
  - action: "expecting camelCase datetime fields from REST API"
    warning: "REST uses snake_case (created_at), GraphQL uses camelCase (createdAt)."
---

# GitHub REST API Patterns

This document covers patterns for using GitHub's REST API via `gh api`.

## Field Mapping: REST vs GraphQL

When converting from `gh issue list --json` (GraphQL) to `gh api repos/.../issues` (REST), these field differences apply:

| Field   | GraphQL (`gh ... --json`)   | REST (`gh api`)             |
| ------- | --------------------------- | --------------------------- |
| Author  | `author.login`              | `user.login`                |
| URL     | `url`                       | `html_url`                  |
| Created | `createdAt` (camelCase)     | `created_at` (snake_case)   |
| Updated | `updatedAt` (camelCase)     | `updated_at` (snake_case)   |
| State   | `OPEN`/`CLOSED` (uppercase) | `open`/`closed` (lowercase) |
| Body    | Always string               | Can be `null`               |

## Normalization Pattern

```python
def _normalize_issue(self, data: dict[str, Any]) -> IssueInfo:
    return IssueInfo(
        number=data["number"],
        title=data["title"],
        body=data.get("body") or "",  # Handle null body
        state=data["state"].upper(),  # Normalize to uppercase
        url=data["html_url"],  # Map html_url to url
        labels=[label["name"] for label in data.get("labels", [])],
        author=data.get("user", {}).get("login", ""),  # user.login not author.login
        created_at=data.get("created_at", ""),  # snake_case
        updated_at=data.get("updated_at", ""),  # snake_case
    )
```

## Query Parameter Syntax

REST API uses query parameters instead of GraphQL arguments:

| Filter | GraphQL Flag               | REST Query Param                     |
| ------ | -------------------------- | ------------------------------------ |
| State  | `--state open`             | `?state=open`                        |
| Labels | `--label bug --label feat` | `?labels=bug,feat` (comma-separated) |
| Limit  | `--limit 10`               | `?per_page=10`                       |

## Example Conversion

**Before (GraphQL-backed):**

```python
cmd = ["gh", "issue", "list", "--json", "number,title,state", "--state", "open"]
```

**After (REST):**

```python
cmd = ["gh", "api", "repos/{owner}/{repo}/issues?state=open"]
```

## Related Topics

- [GitHub GraphQL API Patterns](github-graphql.md) - When GraphQL is required
