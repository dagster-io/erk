---
title: Branch Reuse in Plan Submit
read_when:
  - "implementing erk plan submit"
  - "handling duplicate branches"
  - "resubmitting a plan issue"
---

# Branch Reuse in Plan Submit

When resubmitting a plan issue, `erk plan submit` detects existing local branches and prompts the user to reuse or replace them.

## Problem Statement

Without branch detection, each `erk plan submit` creates a new timestamped branch (e.g., `P123-feature-01-15-1430`). Resubmitting the same issue creates duplicate branches that clutter the repository.

## User Workflow

When existing branches are detected, users see three decision paths:

1. **Use existing branch** (default): Continue working on the most recent branch
2. **Delete and create new**: Remove existing branches and start fresh
3. **Abort**: Cancel the submission

### Example Interaction

```
Found existing local branch(es) for this issue:
  • P123-feature-01-10-0900
  • P123-feature-01-12-1430

New branch would be: P123-feature-01-15-1600

Use existing branch 'P123-feature-01-12-1430'? [Y/n]
```

## Detection Logic

The `_find_existing_branches_for_issue()` function searches local branches matching the `P{issue_number}-*` pattern.

**Key behaviors:**

- Returns all matching branches sorted alphabetically (newest timestamp last)
- When reusing, selects the most recent branch (last in sorted list)
- When deleting, removes all matching branches before creating new

## Graphite Integration

When reusing an existing branch, the submit command ensures Graphite tracking is properly configured:

**LBYL Pattern (Look Before You Leap):**

1. Check if branch is already tracked: `graphite.is_branch_tracked(branch_name)`
2. If not tracked: `graphite.track_branch(branch_name, parent)`

This prevents errors from attempting to re-track an already tracked branch.

## Why Detection Happens First

Branch detection occurs **before** computing the new branch name because:

1. Allows early exit if user chooses existing branch
2. Avoids computing timestamps that won't be used
3. Shows users the comparison (existing vs. new) for informed decisions

## Implementation Reference

See `src/erk/cli/commands/submit.py`:

- `_find_existing_branches_for_issue()` - Detection logic
- `_prompt_existing_branch_action()` - User prompt handling

## Related Topics

- [Plan Lifecycle](lifecycle.md) - Full plan submission workflow
- [Graphite Branch Setup](../erk/graphite-branch-setup.md) - Branch tracking patterns
