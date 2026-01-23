---
title: Multi-Plan Consolidation Patterns
read_when:
  - "consolidating multiple plans into one"
  - "understanding overlap analysis for plans"
  - "deciding between consolidation vs batch replan"
---

# Multi-Plan Consolidation Patterns

When multiple related plans exist, consolidation merges them into a single unified plan. This document covers when to consolidate, how to analyze overlap, and the output format.

## When to Consolidate vs Alternatives

| Approach                      | Use When                                    |
| ----------------------------- | ------------------------------------------- |
| **Consolidate**               | Plans overlap significantly (30%+ items)    |
| **Batch replan**              | Plans are independent, just need refreshing |
| **Objective coordination**    | Plans are steps in a larger initiative      |
| **Sequential implementation** | Plans must be done in order (dependencies)  |

### Decision Criteria

1. **Overlap > 30%**: Consolidate to avoid duplicate work
2. **Shared context**: Consolidate when plans touch same files/concepts
3. **Independent work**: Batch replan (parallel, no merge)
4. **Dependency chain**: Objective with ordered steps

## Consolidation Workflow

### Step 1: Fetch All Plans (Parallel)

```bash
# Fetch each plan's content in parallel
erk exec get-issue-body 123 &
erk exec get-issue-body 456 &
erk exec get-issue-body 789 &
wait
```

### Step 2: Overlap Analysis

Launch parallel Explore agents (one per plan) to identify:

- Common files mentioned across plans
- Shared concepts or patterns
- Items that appear in multiple plans
- Dependency relationships

**Output format:**

| Item              | Plans      | Resolution                   |
| ----------------- | ---------- | ---------------------------- |
| Add tripwire X    | #123, #456 | Merge - single item          |
| Update doc Y      | #123       | Keep - unique to #123        |
| Refactor module Z | #456, #789 | Merge - combine requirements |

### Step 3: Merge Strategy Determination

For overlapping items:

1. **Identical**: Pick one, attribute to first plan
2. **Compatible**: Combine requirements from both
3. **Conflicting**: Flag for manual resolution, prefer newer plan

### Step 4: Attribution Tracking

When merging items from source plans, include attribution:

```markdown
## Implementation Steps

### Update gateway-abc-implementation.md [from #5696]

Add section documenting sub-gateway extraction pattern.

### Add session source tripwire [from #5683, #5680]

Add tripwire for checking source_type before session download.
```

The `[from #123]` syntax shows which original plan contributed each item.

## Consolidated Plan Format

Consolidated plans use a special header format:

```markdown
# Plan: Consolidated Title

> **Consolidates:** #123, #456, #789

## Source Plans

| #    | Title       | Status       |
| ---- | ----------- | ------------ |
| #123 | First Plan  | To be closed |
| #456 | Second Plan | To be closed |
| #789 | Third Plan  | To be closed |

## Investigation Findings

### What Already Exists (Skip These Items)

[Items discovered to already be implemented]

### Corrections to Original Plans

[Mistakes or outdated assumptions in source plans]

### Overlap Analysis

[Table showing which items came from which plans]

## Remaining Gaps (Items to Implement)

[Actual implementation items after deduplication]
```

Compare to single-plan replan format which uses `> **Replans:** #123`.

## Implementation Reference

The `/erk:replan` command handles consolidation when given multiple issue numbers:

```bash
/erk:replan 123 456 789
```

See `.claude/commands/erk/replan.md` for the full agent instructions.

## Related Documentation

- [Plan Schema Reference](plan-schema.md) - Full plan format specification
- [Plan Lifecycle](lifecycle.md) - How plans are created and closed
- [Cross-Artifact Analysis](cross-artifact-analysis.md) - Detecting relationships between PRs and plans
