---
title: GitHub API Field Mapping
read_when:
  - "parsing API responses"
  - "switching between GraphQL and REST"
  - "normalizing GitHub API data"
tripwires:
  - action: "switching GitHub API from GraphQL to REST or vice versa"
    warning: "Field names differ between APIs. Incorrect mapping causes runtime errors."
---

# GitHub API Field Mapping

## GraphQL vs REST Field Differences

When switching between GraphQL (`gh issue view --json`) and REST (`gh api`), field names differ:

| Field             | GraphQL               | REST                  |
| ----------------- | --------------------- | --------------------- |
| Issue URL         | `url`                 | `html_url`            |
| State             | `"OPEN"` / `"CLOSED"` | `"open"` / `"closed"` |
| Created timestamp | `createdAt`           | `created_at`          |
| Updated timestamp | `updatedAt`           | `updated_at`          |
| Body              | Always string         | Can be `null`         |

## Normalization Pattern

When parsing REST responses, normalize to match GraphQL conventions:

```python
return IssueInfo(
    number=data["number"],
    title=data["title"],
    body=data["body"] or "",           # REST can return null
    state=data["state"].upper(),       # "open" -> "OPEN"
    url=data["html_url"],              # Different field name
    created_at=datetime.fromisoformat(
        data["created_at"].replace("Z", "+00:00")
    ),
    updated_at=datetime.fromisoformat(
        data["updated_at"].replace("Z", "+00:00")
    ),
)
```

## Timestamp Parsing

Both APIs return ISO 8601 timestamps with "Z" suffix:

```python
# "2024-01-15T10:30:00Z" -> datetime with UTC timezone
datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
```
