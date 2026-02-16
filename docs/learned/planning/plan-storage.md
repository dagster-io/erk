---
title: Plan Storage Architecture
read_when:
  - "debugging plan issues"
  - "implementing plan tooling"
  - "plan content appears missing"
tripwires:
  - action: "assuming plan content is in the issue body"
    warning: "Plan content lives in an issue COMMENT, not the issue body. The body contains only metadata blocks. Use plan_comment_id from plan-header to find the content."
---

# Plan Storage Architecture

## Storage Locations

| Content            | Location          | Identifier                        |
| ------------------ | ----------------- | --------------------------------- |
| Plan metadata      | Issue body        | `plan-header` metadata block      |
| Objective metadata | Issue body        | `objective-header` metadata block |
| Full plan content  | Issue **comment** | `plan_comment_id` in plan-header  |

## Key Insight

The issue body does NOT contain the full plan. Full content lives in a comment.

## Markers

Full plan content is wrapped in:

```
<!-- erk:metadata-block:plan-body -->
[plan content here]
<!-- /erk:metadata-block:plan-body -->
```

## Implementation Reference

See `PlanHeader` dataclass and `plan_comment_id` field in `erk_shared.gateway.github.metadata`.

## Related Documentation

- [Plan File Recovery](plan-recovery.md) — Recovering truncated plan files
- [Plan Lifecycle](lifecycle.md) — Full plan lifecycle
- [Metadata Block Fallback](metadata-block-fallback.md) — Extraction logic
