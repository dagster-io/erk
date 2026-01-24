---
title: Pipeline Transformation Patterns
read_when:
  - "designing data transformation pipelines"
  - "deciding when to enrich vs filter data"
  - "troubleshooting lost metadata in pipelines"
---

# Pipeline Transformation Patterns

When data flows through multiple transformation stages, the ordering of operations matters. This document covers patterns for maintaining data integrity.

## The ENRICH → FILTER → DISPLAY Principle

Data pipelines should follow this order:

```
Raw Data → ENRICH (add metadata) → FILTER (reduce set) → DISPLAY (format for output)
```

### Why This Order

**ENRICH before FILTER**: Enrichment adds metadata needed for filtering decisions. If you filter first, you can't enrich filtered-out items, and re-adding them later loses metadata.

**FILTER before DISPLAY**: Display formatting is expensive. Only format items that will be shown.

### Anti-Pattern: Filter Before Enrich

```python
# WRONG: Filtering before enrichment
plans = fetch_plans_from_github()
filtered = [p for p in plans if p.state == "open"]
enriched = add_learn_prefixes(filtered)  # Lost plans never get prefixes!
```

If the filter is later changed to include more plans, they won't have the enrichment applied.

### Correct Pattern

```python
# CORRECT: Enrich first, then filter
plans = fetch_plans_from_github()
enriched = add_learn_prefixes(plans)  # All plans get prefixes
filtered = [p for p in enriched if p.state == "open"]
displayed = format_for_table(filtered)
```

## Metadata Preservation Through Transformations

When transforming data structures (e.g., `Plan` → `PlanRowData`), ensure all fields transfer:

### Anti-Pattern: Partial Object Construction

```python
# WRONG: Hand-constructing with missing fields
row_data = PlanRowData(
    issue_number=plan.issue_number,
    title=plan.title,
    # Missing: learn_status, learn_plan_issue, etc.
)
```

### Correct Pattern: Complete Field Transfer

Ensure transformation functions explicitly handle all fields, or use patterns that naturally preserve data (like dataclass `replace()`).

## Immutability in Pipelines

Use frozen dataclasses throughout pipelines:

- Prevents accidental mutation during filtering
- Makes threading safer
- Clarifies that transformations create new objects

```python
@dataclass(frozen=True)
class Plan:
    issue_number: int
    title: str
    learn_status: str | None
```

## Common Pipeline Issues

| Symptom                         | Likely Cause                 | Fix                                        |
| ------------------------------- | ---------------------------- | ------------------------------------------ |
| Metadata null after filtering   | Filter before enrich         | Reorder: ENRICH → FILTER                   |
| Prefix missing on some items    | Items added after enrichment | Enrich all items, including late additions |
| Data inconsistent after refresh | Mutable objects modified     | Use frozen dataclasses                     |

## Related Topics

- [Learn Plan Metadata Preservation](../planning/learn-plan-metadata-fields.md) - Specific metadata fields to preserve
- [TUI Plan Title Rendering Pipeline](../tui/plan-title-rendering-pipeline.md) - Concrete pipeline example
