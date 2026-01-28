---
title: Branch Creation Patterns
read_when:
  - "creating branches from dynamic data"
  - "working with branch naming conventions"
  - "implementing commands that create git branches"
---

# Branch Creation Patterns

## Branch Naming from Dynamic Data

When creating branches from dynamic user input (e.g., issue numbers, plan titles), use prefixes to namespace them:

**Pattern:** `<prefix>/<dynamic-value>`

**Example:** `plan-review/1234` from issue #1234

**Why this matters:**

- Avoids collisions with user-created branches
- Groups related branches for easy identification (`git branch --list 'plan-review/*'`)
- Makes cleanup straightforward (`git branch -D plan-review/*`)

**Implemented in:**

- `plan-create-review-branch` uses `plan-review/<issue>` prefix

## Related Topics

- [Graphite Branch Setup](graphite-branch-setup.md) - Branch creation with Graphite
- [Branch Cleanup](branch-cleanup.md) - Cleaning up stale branches
