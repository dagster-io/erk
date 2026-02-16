---
description: Resolving multiple PR review threads in a single API call
read_when:
  - resolving multiple review threads at once
  - batch resolving PR comments
  - using erk exec resolve-review-threads
last_audited: "2026-02-16 00:00 PT"
audit_result: new
---

# Batch Thread Resolution

Resolve multiple review threads in a single API call using `erk exec resolve-review-threads`.

## JSON Stdin Format

```json
[
  {
    "thread_id": "<thread-id>",
    "body": "Explanation for resolution"
  },
  {
    "thread_id": "<thread-id-2>",
    "body": "Second explanation"
  }
]
```

## Usage

```bash
echo '[{"thread_id": "123", "body": "Fixed"}]' | erk exec resolve-review-threads --pr 7134
```

## When to Use

- Multiple threads can be resolved together (same batch)
- More efficient than individual `resolve-review-thread` calls
- Especially useful after batch code fixes
