---
title: PR Feedback Classifier Schema
read_when:
  - "working with PR feedback classification output"
  - "debugging classifier-to-dash alignment issues"
  - "understanding informational_count vs actionable_threads"
tripwires:
  - action: "treating informational_count as including review threads"
    warning: "informational_count covers ONLY discussion comments, not review threads. All unresolved review threads must appear individually in actionable_threads."
  - action: "checking thread count without comparing to dash count"
    warning: "Thread count in classifier output must equal erk dash count. Missing threads are silently dropped."
  - action: "editing .claude/ markdown without running prettier"
    warning: "Run `prettier --write <file>` immediately after editing .claude/ markdown. `make fast-ci` fails otherwise."
---

# PR Feedback Classifier Schema

Authoritative reference for the PR feedback classifier's JSON output format.

## Output Schema

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md:92-152 -->

```json
{
  "success": true,
  "pr_number": 5944,
  "pr_title": "Feature: Add new API endpoint",
  "pr_url": "https://github.com/owner/repo/pull/5944",
  "actionable_threads": [
    {
      "thread_id": "PRRT_kwDOPxC3hc5q73Ne",
      "type": "review",
      "path": "src/api.py",
      "line": 42,
      "is_outdated": false,
      "classification": "actionable",
      "action_summary": "Add integration tests for new endpoint",
      "complexity": "local",
      "original_comment": "This needs integration tests"
    }
  ],
  "discussion_actions": [
    {
      "comment_id": 12345678,
      "action_summary": "Update API documentation",
      "complexity": "cross_cutting",
      "original_comment": "Please update the docs to reflect..."
    }
  ],
  "informational_count": 2,
  "batches": [
    {
      "name": "Local Fixes",
      "complexity": "local",
      "auto_proceed": true,
      "item_indices": [0]
    }
  ],
  "error": null
}
```

## Top-Level Fields

| Field                 | Type                   | Description                                                                                                             |
| --------------------- | ---------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `success`             | bool                   | Whether the classification operation succeeded                                                                          |
| `pr_number`           | int                    | PR number being classified                                                                                              |
| `pr_title`            | string                 | PR title                                                                                                                |
| `pr_url`              | string                 | PR URL                                                                                                                  |
| `actionable_threads`  | list[ActionableThread] | All unresolved review threads (both actionable and informational)                                                       |
| `discussion_actions`  | list[DiscussionAction] | Top-level PR discussion comments requiring action                                                                       |
| `informational_count` | int                    | Count of informational **discussion** comments only (CI status, Graphite stack). Review threads are listed individually |
| `batches`             | list[Batch]            | Execution order with `item_indices` referencing the arrays above                                                        |
| `error`               | string \| null         | Error message if `success` is false                                                                                     |

## ActionableThread Fields

| Field              | Type        | Description                                                              |
| ------------------ | ----------- | ------------------------------------------------------------------------ |
| `thread_id`        | string      | GitHub thread ID for `erk exec resolve-review-thread`                    |
| `type`             | string      | Always `"review"` for review threads                                     |
| `path`             | string      | File path the comment applies to                                         |
| `line`             | int \| null | Line number (null for outdated threads)                                  |
| `is_outdated`      | bool        | Whether the thread's code context has changed since posting              |
| `classification`   | string      | `"actionable"` (code changes needed) or `"informational"` (user decides) |
| `action_summary`   | string      | One-line summary of the required action                                  |
| `complexity`       | string      | `"local"`, `"single_file"`, `"cross_cutting"`, or `"complex"`            |
| `original_comment` | string      | First 200 characters of the comment text                                 |

## DiscussionAction Fields

| Field              | Type   | Description                                           |
| ------------------ | ------ | ----------------------------------------------------- |
| `comment_id`       | int    | Comment ID for `erk exec reply-to-discussion-comment` |
| `action_summary`   | string | One-line summary of the required action               |
| `complexity`       | string | Complexity level for batch ordering                   |
| `original_comment` | string | First 200 characters of the comment text              |

## Batch Fields

| Field          | Type      | Description                                                      |
| -------------- | --------- | ---------------------------------------------------------------- |
| `name`         | string    | Human-readable batch name                                        |
| `complexity`   | string    | Batch complexity level                                           |
| `auto_proceed` | bool      | Whether this batch can proceed without user confirmation         |
| `item_indices` | list[int] | Indices into `actionable_threads` or `discussion_actions` arrays |

## Classifier-to-Dash Alignment Invariant

The number of threads in `actionable_threads` must equal the unresolved comments count shown in the TUI dashboard. If they differ, the classifier is silently dropping threads.

**Verification**: Compare `len(actionable_threads)` with the `comments` column in `erk dash` output.

## Bot Thread Inflation

Bot-generated review threads (automated linting, CI notifications) inflate `informational_count`. This is expected behavior — the classifier categorizes bot discussion comments as informational rather than actionable.

## Related Documentation

- [PR Address Workflows](pr-address-workflows.md) — How classified feedback is addressed
- [PR Operations](../pr-operations/) — Broader PR workflow context
