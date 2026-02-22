---
title: Resolve Review Threads JSON Format
read_when:
  - "calling erk exec resolve-review-threads"
  - "automating PR review thread resolution"
  - "getting 'Item at index 0 is not an object' errors"
tripwires:
  - action: "passing a flat list of thread IDs to resolve-review-threads"
    warning: 'The input must be a list of objects with thread_id and comment fields, not a flat list of strings. Wrong: ["PRRT_..."] → ''Item at index 0 is not an object''. Correct: [{"thread_id": "PRRT_...", "comment": "..."}]'
---

# Resolve Review Threads JSON Format

The `erk exec resolve-review-threads` script expects a specific JSON input format via stdin. Using the wrong format produces an unhelpful "Item at index 0 is not an object" error.

## Correct Format

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py, ThreadResolutionItem -->

Input is a JSON array of objects matching the `ThreadResolutionItem` TypedDict:

```json
[
  { "thread_id": "PRRT_abc123", "comment": "Fixed in latest commit" },
  { "thread_id": "PRRT_def456", "comment": null }
]
```

| Field       | Type          | Description                               |
| ----------- | ------------- | ----------------------------------------- |
| `thread_id` | `str`         | PR review thread ID (starts with `PRRT_`) |
| `comment`   | `str \| null` | Optional reply comment before resolving   |

## Common Mistake

```json
["PRRT_abc123", "PRRT_def456"]
```

This flat array of strings produces: `Item at index 0 is not an object`. Always use the object format.

## Verifying the Schema

Run `erk exec resolve-review-threads -h` to see the expected format and usage.

## Code Location

<!-- Source: src/erk/cli/commands/exec/scripts/resolve_review_threads.py -->

`src/erk/cli/commands/exec/scripts/resolve_review_threads.py` — `ThreadResolutionItem` TypedDict at lines 43-47.
