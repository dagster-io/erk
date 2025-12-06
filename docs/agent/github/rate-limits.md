---
title: GitHub API Rate Limits
read_when:
  - "hitting API rate limits"
  - "choosing between GraphQL and REST"
  - "seeing rate limit exceeded errors"
---

# GitHub API Rate Limits

## Key Insight: Separate Rate Limits

GitHub maintains **separate rate limits** for GraphQL and REST APIs:

- **GraphQL**: 5,000 points/hour (queries cost variable points)
- **REST**: 5,000 requests/hour (simple count)

**Critical**: Hitting the GraphQL rate limit does NOT affect REST API access. If you see:

```
GraphQL: API rate limit already exceeded
```

You can switch to the equivalent REST API endpoint and continue working.

## When to Use REST vs GraphQL

| Use REST When...                              | Use GraphQL When...                      |
| --------------------------------------------- | ---------------------------------------- |
| High-volume operations (batch issue fetching) | Need nested/related data in single query |
| GraphQL rate limit is exhausted               | Need specific field selection            |
| Simple CRUD operations                        | Complex filtering                        |

## Erk Pattern: Prefer REST for Simple Operations

In `erk_shared/github/issues/real.py`, we prefer REST API for simple operations:

```python
# REST API - counts against REST rate limit
cmd = ["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}"]

# GraphQL (via gh issue view) - counts against GraphQL rate limit
cmd = ["gh", "issue", "view", str(number), "--json", "..."]
```

## Checking Rate Limits

```bash
# Check REST rate limit
gh api rate_limit

# Check GraphQL rate limit (in the response)
gh api graphql -f query='{ rateLimit { remaining resetAt } }'
```
