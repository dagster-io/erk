---
title: Consolidation Labels
read_when:
  - "consolidating multiple learn plans"
  - "working with erk-consolidated label"
  - "preventing re-consolidation of issues"
  - "running /local:replan-learn-plans"
tripwires:
  - action: "consolidating issues that already have erk-consolidated label"
    warning: "Filter out erk-consolidated issues before consolidation. These are outputs of previous consolidation and should not be re-consolidated."
---

# Consolidation Labels

The `erk-consolidated` label is a state machine marker that prevents circular re-consolidation of learn plans.

## Problem Statement

The `/local:replan-learn-plans` command consolidates multiple open `erk-learn` plans into a single new plan. Without protection, the consolidated output would itself be picked up by future consolidation runs, creating an infinite loop.

## Solution: The `erk-consolidated` Label

When `/erk:replan` runs in consolidation mode (multiple source plans), it adds the `erk-consolidated` label to the newly created issue:

```bash
gh issue edit <new_issue_number> --add-label "erk-consolidated"
```

This label marks the issue as "already consolidated" and prevents it from being re-consolidated.

## Workflow Integration

### `/local:replan-learn-plans`

1. Lists all open issues with `erk-learn` label
2. **Filters out** any issues that also have `erk-consolidated`
3. Consolidates the remaining (un-consolidated) issues
4. Creates new issue with `erk-consolidated` label

### `/erk:replan` (Consolidation Mode)

When called with multiple issue numbers:

1. Analyzes all source issues
2. Creates consolidated plan
3. Adds `erk-consolidated` label to new issue
4. Closes original issues with reference to new one

## Label State Machine

```
┌─────────────┐
│  erk-learn  │  (documentation plan from /erk:learn)
└──────┬──────┘
       │
       │ /local:replan-learn-plans or /erk:replan (consolidation)
       ▼
┌─────────────────────┐
│ erk-learn +         │  (consolidated plan, protected from re-consolidation)
│ erk-consolidated    │
└─────────────────────┘
```

## Edge Cases

### All Issues Already Consolidated

If `/local:replan-learn-plans` finds open `erk-learn` issues but all have `erk-consolidated`:

```
All N open erk-learn plans are already consolidated. Nothing new to consolidate.
```

### Single Issue Consolidation

When `/erk:replan` is called with a single issue (not consolidation mode), the `erk-consolidated` label is **not** added. This is intentional - single-issue replans are updates, not consolidations.

## Commands That Use This Label

| Command                     | Behavior                                     |
| --------------------------- | -------------------------------------------- |
| `/local:replan-learn-plans` | Filters out `erk-consolidated` from input    |
| `/erk:replan`               | Adds label when consolidating multiple plans |

## Implementation Notes

The label check happens early in the workflow to avoid unnecessary API calls:

```bash
# Step 1b: Filter Out Already-Consolidated Plans
# From the results, filter out any issues that have the erk-consolidated label.
```

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Overall plan state management
- [Learn Workflow](learn-workflow.md) - How learn plans are created
- [Glossary: erk-consolidated](../glossary.md#erk-consolidated) - Label definition
