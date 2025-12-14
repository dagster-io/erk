# REST vs GraphQL Field Mapping Guide

Practical guide for mapping between GitHub REST API and GraphQL API responses when building wrappers or converting between API backends.

## Pull Requests

### State Field

**GraphQL** uses uppercase enum values:
- `OPEN` - PR is open
- `CLOSED` - PR was closed without merging
- `MERGED` - PR was merged

**REST API** uses lowercase + separate `merged_at` field:
- `state: "open"` - PR is open
- `state: "closed"` + `merged_at: null` - PR was closed without merging
- `state: "closed"` + `merged_at: "2024-01-01T..."` - PR was merged

**Mapping logic:**
```python
if data.get("merged_at") is not None:
    state = "MERGED"
elif data["state"] == "closed":
    state = "CLOSED"
else:
    state = "OPEN"
```

### Draft Status

| GraphQL | REST |
|---------|------|
| `isDraft` | `draft` |

### URL Fields

| GraphQL | REST | Notes |
|---------|------|-------|
| `url` | `html_url` | The web URL users see |
| N/A | `url` | REST `url` is the API endpoint, not the web URL |

### Author Information

**GraphQL:**
```graphql
author {
  login
}
```

**REST API:**
```json
{
  "user": {
    "login": "username"
  }
}
```

### Mergeable Status

**GraphQL** uses enum values:
- `MERGEABLE`
- `CONFLICTING`
- `UNKNOWN`

**REST API** uses boolean + state string:
- `mergeable: true` / `false` / `null`
- `mergeable_state: "clean"` / `"dirty"` / `"unknown"` / etc.

**Mapping logic:**
```python
mergeable_raw = data.get("mergeable")
if mergeable_raw is True:
    mergeable = "MERGEABLE"
elif mergeable_raw is False:
    mergeable = "CONFLICTING"
else:
    mergeable = "UNKNOWN"
```

---

## API Feature Differences

### Filtering Limitations

**REST `/repos/{owner}/{repo}/pulls` endpoint:**
- Supports: `state` (open/closed/all), `head`, `base`, `sort`, `direction`
- Does NOT support: `author` filter

**To filter by author with REST:**
1. Get current username via `gh api user --jq '.login'`
2. Fetch all PRs and filter client-side

**GraphQL:**
- Supports author filter directly in query

### State Filter Differences

**REST API state parameter:**
- `open` - Only open PRs
- `closed` - Both closed and merged PRs (must check `merged_at` to distinguish)
- `all` - All PRs

**GraphQL/CLI state parameter:**
- `open` - Only open PRs
- `closed` - Only closed (not merged) PRs
- `merged` - Only merged PRs
- `all` - All PRs

**To get only merged PRs with REST:**
```bash
gh api "/repos/{owner}/{repo}/pulls?state=closed" | \
  jq '[.[] | select(.merged_at != null)]'
```

**To get only closed (not merged) PRs with REST:**
```bash
gh api "/repos/{owner}/{repo}/pulls?state=closed" | \
  jq '[.[] | select(.merged_at == null)]'
```

---

## Common Pitfalls

### 1. Assuming `gh pr list` Uses REST

**Wrong:** The `gh pr list` command uses REST API.

**Correct:** The `gh pr list` command uses **GraphQL** (see `api-backend-audit.md`).

If you need to avoid GraphQL rate limits, use `gh api /repos/{owner}/{repo}/pulls` directly.

### 2. Using REST `url` Field for Web Links

**Wrong:**
```python
url = pr_data["url"]  # Returns API endpoint
```

**Correct:**
```python
url = pr_data["html_url"]  # Returns web URL
```

### 3. Checking `merged` State in REST Response

**Wrong:**
```python
if pr_data["state"] == "merged":  # Never true
```

**Correct:**
```python
if pr_data.get("merged_at") is not None:
```

### 4. Assuming REST Author Filter Exists

**Wrong:**
```bash
gh api "/repos/{owner}/{repo}/pulls?author=username"  # No such parameter
```

**Correct:**
```bash
# Filter client-side after fetching
gh api "/repos/{owner}/{repo}/pulls" | jq '[.[] | select(.user.login == "username")]'
```

---

## Recommended Patterns

### Internal Enum Convention

Use GraphQL-style uppercase enum values as the canonical internal representation:
- `OPEN`, `CLOSED`, `MERGED` for PR state
- `MERGEABLE`, `CONFLICTING`, `UNKNOWN` for merge status

Map to/from lowercase at API boundaries:
```python
# CLI input -> internal
status_internal = cli_status.upper()

# REST response -> internal
if rest_state == "closed" and merged_at:
    internal_state = "MERGED"
elif rest_state == "closed":
    internal_state = "CLOSED"
else:
    internal_state = "OPEN"
```

### Prefer REST for Simple Listing

When you need simple PR listing without complex filtering:
- REST is predictable (1 request = 1 API call)
- GraphQL query cost varies with complexity
- REST has higher rate limit (5000/hour vs point-based)

### Use GraphQL for Complex Queries

When you need:
- Nested data (PR with reviews, checks, comments) in one call
- Complex filtering (by author, labels, etc.)
- Specific field selection to reduce payload

---

## See Also

- `api-backend-audit.md` - Which gh commands use REST vs GraphQL
- `gh.md` - Command reference and workflows
- `graphql.md` - GraphQL API patterns
- [GitHub REST API - Pull Requests](https://docs.github.com/en/rest/pulls/pulls)
- [GitHub GraphQL API - PullRequest](https://docs.github.com/en/graphql/reference/objects#pullrequest)
