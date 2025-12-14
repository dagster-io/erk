# Documentation Extraction Plan

## Objective

Add documentation covering GitHub REST vs GraphQL API patterns discovered during rate limit debugging and API migration work.

## Source Information

- **Planning Session**: From issue #3200 (rate limit discovery and research)
- **Implementation Session**: 5cfed9c8-aabe-46f9-becd-35eef10d1264 (REST API conversion)

## Documentation Items

### Item 1: GitHub REST API Response Field Mapping

**Type**: Category A (Learning Gap)
**Location**: `.erk/docs/agent/architecture/github-rest-api.md` (new file)
**Action**: Create
**Priority**: High

The implementation revealed critical field mapping differences between GitHub's REST and GraphQL APIs that caused test failures and required debugging.

**Draft Content**:

```markdown
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

| Field | GraphQL (`gh ... --json`) | REST (`gh api`) |
|-------|---------------------------|-----------------|
| Author | `author.login` | `user.login` |
| URL | `url` | `html_url` |
| Created | `createdAt` (camelCase) | `created_at` (snake_case) |
| Updated | `updatedAt` (camelCase) | `updated_at` (snake_case) |
| State | `OPEN`/`CLOSED` (uppercase) | `open`/`closed` (lowercase) |
| Body | Always string | Can be `null` |

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

| Filter | GraphQL Flag | REST Query Param |
|--------|-------------|------------------|
| State | `--state open` | `?state=open` |
| Labels | `--label bug --label feat` | `?labels=bug,feat` (comma-separated) |
| Limit | `--limit 10` | `?per_page=10` |

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
```

---

### Item 2: gh CLI Command Rate Limit Guide

**Type**: Category A (Learning Gap)
**Location**: `.erk/docs/agent/architecture/github-graphql.md` (update existing)
**Action**: Update - Add "Rate Limit Considerations" section
**Priority**: High

The session discovered that `gh issue list --json` internally uses GraphQL, which has stricter rate limits than REST. This wasn't obvious from the command syntax.

**Draft Content** (add to existing github-graphql.md):

```markdown
## Rate Limit Considerations

### gh Commands That Use GraphQL Internally

**CRITICAL**: Some `gh` commands appear to use REST but internally delegate to GraphQL, which has stricter rate limits (5,000 points/hour vs 5,000 requests/hour for REST).

Commands that use **GraphQL internally**:
- `gh issue list --json ...` - Uses GraphQL for JSON output
- `gh pr list --json ...` - Uses GraphQL for JSON output
- `gh repo view --json ...` - Uses GraphQL for JSON output

Commands that use **REST**:
- `gh api repos/{owner}/{repo}/issues` - Direct REST endpoint
- `gh api repos/{owner}/{repo}/pulls` - Direct REST endpoint
- `gh issue view <number>` (without --json) - Uses REST

### Rate Limit Error Pattern

When you see this error:
```
GraphQL: API rate limit already exceeded for user ID 12345678
```

The solution is often to convert from `gh <resource> list --json` to `gh api repos/{owner}/{repo}/<resource>`.

### When to Prefer REST

Use REST (`gh api`) when:
- Listing resources with simple filters (state, labels)
- Rate limits are a concern (high-frequency operations)
- You don't need GraphQL-only fields (like `isResolved` on PR threads)

Use GraphQL (`gh api graphql` or `gh ... --json`) when:
- You need fields only available in GraphQL (see table below)
- You need to traverse relationships in a single query
- You need mutations (resolve threads, etc.)
```

---

### Item 3: Glossary Entry for GraphQL Rate Limits

**Type**: Category B (Teaching Gap)
**Location**: `.erk/docs/agent/glossary.md` (update existing)
**Action**: Update - Add glossary entry
**Priority**: Medium

Add a glossary entry to help agents quickly understand the rate limit distinction.

**Draft Content**:

```markdown
### GitHub API Rate Limits

GitHub has two separate rate limit pools:

- **REST API**: 5,000 requests/hour per authenticated user
- **GraphQL API**: 5,000 points/hour (queries cost 1+ points based on complexity)

**Key insight**: `gh issue list --json` uses GraphQL internally, not REST. When hitting GraphQL rate limits, convert to `gh api repos/{owner}/{repo}/issues` which uses REST.

See [GitHub GraphQL API Patterns](architecture/github-graphql.md) for details.
```

---

## Implementation Notes

- Item 1 creates a new companion doc to the existing `github-graphql.md`
- Item 2 enhances the existing GraphQL doc with rate limit awareness
- Item 3 provides quick-reference for agents in the glossary