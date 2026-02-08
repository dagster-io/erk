---
title: Optional Field Propagation
read_when:
  - "transforming dataclass instances in pipelines"
  - "debugging null metadata fields"
  - "adding optional fields to dataclasses"
tripwires:
  - action: "hand-constructing frozen dataclass instances with selective field copying"
    warning: "Always use dataclasses.replace() to preserve all fields. Hand-construction with partial field copying silently drops optional fields (learn_status, learn_plan_issue, objective_issue, etc.)."
---

# Optional Field Propagation

**The Problem**: Frozen dataclasses with many optional fields (10+ fields, half optional) flow through multi-stage pipelines (fetch → enrich → filter → transform → display). Optional fields are silently lost when transformations create new instances instead of modifying existing ones.

**Why This Matters**: Unlike mutable objects where you can `.set_field()` incrementally, frozen dataclasses require creating new instances at each transformation. Any transformation that doesn't explicitly preserve all fields will drop optional data—and the type system won't catch it since `field: str | None` accepts `None`.

## The Cross-Cutting Pattern

This pattern appears wherever frozen dataclasses with optional fields flow through multi-stage processing:

- **TUI data pipelines**: `PlanRowData` with 30+ fields (15 optional) flows through filtering/sorting
- **CLI pipelines**: `SubmitState`, `LandState` with 10+ optional fields threaded through validation/execution stages
- **Gateway responses**: API data structures enriched with local metadata

The danger zone: any transformation between stages.

## Why Optional Fields Disappear

### Root Cause: Frozen Dataclass Transformation Pattern

With frozen dataclasses, you can't mutate. You must create new instances:

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, dataclasses.replace() usage -->
```python
# CORRECT: dataclasses.replace() preserves all fields
return dataclasses.replace(state, pr_number=123)
```

But developers familiar with mutable patterns often hand-construct:

```python
# WRONG: Hand-construction drops all unspecified fields
return SubmitState(
    pr_number=123,
    branch_name=state.branch_name,
    # 10+ other optional fields are now None!
)
```

The type system doesn't help: `field: int | None` accepts `None`, so this compiles without warnings.

## Loss Patterns

### Pattern 1: Hand-Construction Instead of replace()

**Anti-pattern**:
```python
# WRONG: Selective field copying
new_plan = Plan(
    issue_number=plan.issue_number,
    title=plan.title,
    # Missing: learn_status, learn_plan_issue, objective_issue, pr_number, ...
)
```

**Why it happens**: Developers new to frozen dataclasses think "I'll just create a new instance with the fields I need." They don't realize optional fields default to `None` when not specified.

**Correct pattern**: See `dataclasses.replace()` usage in `src/erk/cli/commands/land_pipeline.py` (all pipeline steps).

### Pattern 2: Enrich After Filter

**Anti-pattern**:
```python
# WRONG: Filter first, enrich later
plans = fetch_plans()                    # Has 100 plans
filtered = [p for p in plans if p.pr_number is not None]  # Now 20 plans
enriched = add_learn_metadata(filtered)  # Enriches 20, misses 80
```

**Why it happens**: Developers optimize for performance ("why enrich plans we'll filter out?") without realizing later stages might filter differently or that enrichment might affect filtering.

**Correct pattern**: Enrich first (all items), then filter. Enrichment cost is usually negligible compared to API calls.

### Pattern 3: Gateway Returns Partial Data

**Anti-pattern**: Gateway method returns dataclass with only required fields populated, expecting caller to fill optional fields.

**Why it happens**: Gateway author thinks "I'll return the core data, caller can add enrichment if needed." But callers often don't know which fields need enrichment.

**Correct pattern**: Gateways return complete instances. If enrichment is expensive, provide separate `enrich=True` parameter (default `False`).

## Pipeline Stage Ordering

For multi-stage pipelines with optional fields:

```
1. Fetch (gateway returns complete instances)
2. Enrich (add derived/expensive fields to ALL items)
3. Filter (remove items—all fields preserved on remaining items)
4. Transform (dataclasses.replace() for modifications)
5. Display/consume (all optional fields available)
```

**Why this order**: Steps 1-2 populate data. Step 3 removes items but preserves fields. Step 4 only modifies, never constructs from scratch.

## Debugging Null Fields

When optional fields are unexpectedly `None`:

1. **Check gateway output**: Does the gateway method return the field populated?
   - Add logging at gateway boundary: `print(f"Gateway returned: {instance}")`
   - Verify field is non-None immediately after gateway call

2. **Check pipeline transformations**: Did any stage create a new instance?
   - Grep for dataclass constructor calls: `Grep(pattern="ClassName\\(")`
   - Verify all transformations use `dataclasses.replace()`

3. **Check enrichment ordering**: Did filtering happen before enrichment?
   - Trace through pipeline stages—is `enrich()` before or after `filter()`?

4. **Check for partial construction**: Is anyone building instances with subset of fields?
   - Look for constructor calls with fewer parameters than dataclass has fields

## Real-World Example: PlanRowData

<!-- Source: src/erk/tui/data/types.py, PlanRowData -->

`PlanRowData` has 34 fields, 15 optional. It flows through:

1. **Construction** (from `PlanListData`): Gateway returns complete instances
2. **Filtering** (`src/erk/tui/filtering/logic.py`): Returns filtered list, preserves all fields
3. **Sorting** (`src/erk/tui/sorting/logic.py`): Reorders items, never reconstructs
4. **Display**: All 34 fields available

**Key insight**: Filtering/sorting never call `PlanRowData()` constructor—they work with existing instances. This is why fields survive.

## Related Documentation

- [Learn Plan Metadata Fields](../planning/learn-plan-metadata-fields.md) - Specific optional fields for learn plans
- [Land State Threading](land-state-threading.md) - How `LandState` preserves fields through 8+ pipeline stages
- [Linear Pipelines](linear-pipelines.md) - Pipeline architecture using frozen dataclasses
