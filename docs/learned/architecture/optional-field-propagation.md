---
title: Optional Field Propagation
read_when:
  - "transforming dataclass instances in pipelines"
  - "debugging null metadata fields"
  - "adding optional fields to dataclasses"
tripwires:
  - action: "hand-constructing Plan or PlanRowData with only required fields"
    warning: "Always pass through gateway methods or use dataclasses.replace(). Hand-construction drops optional fields (learn_status, learn_plan_issue, etc.)."
---

# Optional Field Propagation

This document describes patterns for preserving optional fields when transforming frozen dataclasses through pipelines.

## The Problem

Frozen dataclasses with optional fields are commonly transformed through pipelines:

```
GitHub API → Plan dataclass → Filter → Transform → TUI display
```

Optional fields can be lost at any stage:

- Hand-constructing instances with only required fields
- Filtering before enrichment adds metadata
- Using `dataclasses.replace()` incorrectly

## Common Loss Patterns

### Hand-Construction

```python
# WRONG: Drops optional fields
new_plan = Plan(
    issue_number=plan.issue_number,
    title=plan.title,
    # Missing: learn_status, learn_plan_issue, etc.
)
```

### Filter Before Enrich

```python
# WRONG: Enrichment after filtering misses filtered-out plans
plans = fetch_plans()
filtered = [p for p in plans if matches_filter(p)]
enriched = enrich_with_metadata(filtered)  # Too late!
```

## Correct Patterns

### Pattern 1: Gateway Passthrough

Use gateway methods that return complete dataclass instances:

```python
# Gateway handles complete field population
plan = github.issues.get_plan(issue_number)
# All fields populated by gateway
```

### Pattern 2: dataclasses.replace()

When transforming, use `replace()` to preserve all fields:

```python
from dataclasses import replace

# Preserves all fields, only modifies specified ones
updated = replace(plan, title=f"[erk-learn] {plan.title}")
```

### Pattern 3: Enrich Before Filter

```python
# RIGHT: Enrich first, then filter
plans = fetch_plans()
enriched = enrich_with_metadata(plans)  # All plans enriched
filtered = [p for p in enriched if matches_filter(p)]
```

## Pipeline Order

For pipelines with multiple stages:

```
1. Fetch (gateway returns complete instances)
2. Enrich (add derived fields to all items)
3. Filter (remove items - fields preserved)
4. Transform (dataclasses.replace() for changes)
5. Display (all optional fields available)
```

## Debugging Null Fields

When optional fields are unexpectedly null:

1. **Check source**: Does the GitHub API response contain the field?
2. **Check gateway**: Does the gateway populate the field?
3. **Check pipeline**: Is there hand-construction that drops fields?
4. **Check ordering**: Is enrichment happening after filtering?

## Affected Fields

Common optional fields that are lost:

| Field                           | Type           | Source                   |
| ------------------------------- | -------------- | ------------------------ |
| `learn_status`                  | `str \| None`  | Metadata block           |
| `learn_plan_issue`              | `int \| None`  | Metadata block           |
| `pr_number`                     | `int \| None`  | PR linking               |
| `worktree_path`                 | `Path \| None` | Local worktree discovery |
| `created_from_workflow_run_url` | `str \| None`  | CI workflow backlink     |

## Related Documentation

- [Learn Plan Metadata Fields](../planning/learn-plan-metadata-fields.md) - Specific field preservation for learn metadata
- [Pipeline Transformation Patterns](pipeline-transformation-patterns.md) - General pipeline patterns
- [TUI Architecture](../tui/architecture.md) - How PlanRowData uses optional fields
