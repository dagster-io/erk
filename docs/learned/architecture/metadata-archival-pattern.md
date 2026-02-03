---
title: Archive-on-Clear Metadata Pattern
read_when:
  - clearing a metadata field that should be auditable
  - adding companion fields for historical tracking
  - extending plan-header schema with lifecycle transitions
tripwires:
  - action: "Archive value to 'last_' variant BEFORE clearing"
    warning: "Order matters — clear-then-archive loses the value silently"
    score: 6
last_audited: "2026-02-03"
audit_result: edited
---

# Archive-on-Clear Metadata Pattern

When clearing a metadata field that tracks active workflow state, archive its value to a `last_` companion field first.

## The Pattern

1. **Archive BEFORE clear**: Copy the current value to a `last_` companion field
2. **Then clear**: Set the active field to `None`
3. **Validate**: Ensure both fields conform to schema rules

## Why Archive?

- **Audit trail**: Preserve evidence of completed workflows
- **Debugging**: Understand what happened in previous iterations
- **User visibility**: Show users the history of their plans

## Order Requirement: Archive BEFORE Clear

**CRITICAL:** The archive operation must happen before the clear operation.

**CORRECT:**

```python
# Archive current value (if not None)
current_value = data.get(ACTIVE_FIELD)
if current_value is not None:
    data[LAST_FIELD] = current_value

# Then clear
data[ACTIVE_FIELD] = None
```

**WRONG:**

```python
# Clear first
data[ACTIVE_FIELD] = None

# Try to archive (too late!)
current_value = data.get(ACTIVE_FIELD)  # Always None now
if current_value is not None:
    data[LAST_FIELD] = current_value  # Never executes
```

If you clear first, the value is lost and cannot be archived.

## Reference Implementation

`clear_plan_header_review_pr()` in `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` demonstrates the full pattern. Tests: `tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py`

## Naming Convention

Use the `last_` prefix for archived fields:

- `review_pr` → `last_review_pr`
- `active_session` → `last_active_session`
- `current_branch` → `last_current_branch`

## When to Use

Use archive-on-clear when:

- Field represents an active workflow that completes (e.g., `review_pr`)
- Historical tracking matters for audit or debugging
- State machine transitions need to preserve the old state

Skip archiving when:

- Fields are ephemeral or always overwritten
- History would be noise (high-churn fields)

## Common Pitfalls

### Forgetting the None Check

```python
# WRONG: Always archive, even if None
data[LAST_FIELD] = data[ACTIVE_FIELD]

# CORRECT: Only archive if there's a value
current = data.get(ACTIVE_FIELD)
if current is not None:
    data[LAST_FIELD] = current
```

### Not Validating Both Fields

Both the active and `last_` fields need the same validation rules (type constraints, value constraints).

## Related Documentation

- [Plan Review Lifecycle](../planning/lifecycle.md) - How review_pr/last_review_pr fit into plan lifecycle
