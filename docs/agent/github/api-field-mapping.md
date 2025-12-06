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

## PR-Specific Field Mapping

| Field       | GraphQL                               | REST               | Notes                                                |
| ----------- | ------------------------------------- | ------------------ | ---------------------------------------------------- |
| Base branch | `baseRefName`                         | `base.ref`         | Nested object                                        |
| Head branch | `headRefName`                         | `head.ref`         | Nested object                                        |
| Cross-repo  | `isCrossRepository`                   | Computed           | Compare `head.repo.full_name != base.repo.full_name` |
| State       | `"OPEN"/"CLOSED"/"MERGED"`            | `state` + `merged` | REST: lowercase + separate bool                      |
| Mergeable   | `"MERGEABLE"/"CONFLICTING"/"UNKNOWN"` | `true/false/null`  | Requires mapping                                     |
| Merge state | `mergeStateStatus`                    | `mergeable_state`  | REST: lowercase                                      |
| Title       | `title`                               | `title`            | Same                                                 |
| Body        | `body`                                | `body`             | Both can be null                                     |
| Labels      | `labels[].name`                       | `labels[].name`    | Same structure                                       |

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

## PR State Normalization

REST returns lowercase state with separate `merged` boolean. Normalize to GraphQL format:

```python
# Compute state: REST has "open"/"closed", check merged bool for MERGED
if data.get("merged"):
    state = "MERGED"
else:
    state = data["state"].upper()  # "open" -> "OPEN", "closed" -> "CLOSED"
```

## PR Mergeability Normalization

REST returns `true/false/null` for mergeable. Normalize to GraphQL enums:

```python
# REST --jq returns multiline: mergeable value, then state
lines = result.stdout.strip().split("\n")
mergeable_raw = lines[0] if len(lines) > 0 else "null"
merge_state = lines[1] if len(lines) > 1 else "unknown"

# Map to GraphQL enum format
mergeable = {"true": "MERGEABLE", "false": "CONFLICTING"}.get(mergeable_raw, "UNKNOWN")
merge_state_status = merge_state.upper() if merge_state != "null" else "UNKNOWN"
```

## Cross-Repository Detection

GraphQL provides `isCrossRepository` directly. REST requires computation:

```python
is_cross_repository = data["head"]["repo"]["full_name"] != data["base"]["repo"]["full_name"]
```
