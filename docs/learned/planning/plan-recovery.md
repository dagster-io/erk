---
title: Plan File Recovery
read_when:
  - "plan.md appears truncated or corrupted"
  - "file ends without newline or mid-content"
  - "implementing plans after setup failure"
tripwires:
  - action: "implementing a plan from .impl/plan.md without verifying file integrity"
    warning: "Check file ends with newline and content is not truncated. If corrupted, recover from GitHub API using plan_comment_id from .impl/plan-ref.json."
---

# Plan File Recovery

Local `.impl/plan.md` files may become truncated during setup (incomplete writes, encoding issues, disk problems).

## Detection

Check for truncation indicators:

- File ends without newline
- Content stops mid-sentence or mid-block
- File size unexpectedly small

## Recovery Pattern

Plans are stored in GitHub issue **comments**, not issue bodies. The body contains only metadata blocks.

1. Find the `plan_comment_id` in `.impl/plan-ref.json`
2. Fetch comment via `gh api repos/{owner}/{repo}/issues/comments/{id}`
3. Extract content between `<!-- erk:metadata-block:plan-body -->` markers
4. Overwrite local `plan.md` with recovered content

See `plan_comment_id` handling in `erk exec setup-impl-from-issue`.

## Related Documentation

- [Plan Storage Architecture](plan-storage.md) — Where plan content lives
- [Plan Lifecycle](lifecycle.md) — Full plan lifecycle
