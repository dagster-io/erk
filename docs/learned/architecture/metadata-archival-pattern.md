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
---

# Archive-on-Clear Metadata Pattern

A pattern for preserving historical values when clearing metadata fields that represent workflow state transitions. When clearing a metadata field, archive its value to a `last_` companion field first.

## The Pattern

When clearing a metadata field that tracks active workflow state:

1. **Archive BEFORE clear**: Copy the current value to a `last_` companion field
2. **Then clear**: Set the active field to `None`
3. **Validate**: Ensure both fields conform to schema rules

## Why Archive?

Workflow state fields often need historical tracking:

- **Audit trail**: Preserve evidence of completed workflows
- **Debugging**: Understand what happened in previous iterations
- **State transitions**: Track movement through workflow stages
- **User visibility**: Show users the history of their plans

Archiving allows the active field to reflect current state while preserving past values.

## Implementation Example: clear_plan_header_review_pr

The `clear_plan_header_review_pr()` function demonstrates the pattern:

```python
def clear_plan_header_review_pr(issue_body: str) -> str:
    """Clear review_pr and archive its value to last_review_pr.

    Archives the current review_pr value to last_review_pr (if not None),
    then sets review_pr to None. This is called when a review PR is
    completed to clear the active review while preserving history.
    """
    block = find_metadata_block(issue_body, "plan-header")
    if block is None:
        raise ValueError("plan-header block not found in issue body")

    updated_data = dict(block.data)

    # Archive current review_pr to last_review_pr (if not None)
    current_review_pr = updated_data.get(REVIEW_PR)
    if current_review_pr is not None:
        updated_data[LAST_REVIEW_PR] = current_review_pr

    # Clear review_pr
    updated_data[REVIEW_PR] = None

    # Validate updated data
    schema = PlanHeaderSchema()
    schema.validate(updated_data)

    # Create new block and render
    new_block = MetadataBlock(key="plan-header", data=updated_data)
    new_block_content = render_metadata_block(new_block)

    # Replace block in full body
    return replace_metadata_block_in_body(issue_body, "plan-header", new_block_content)
```

**Source:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py:1398-1437`

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

If you clear first, the value is lost and cannot be archived. The archive step becomes a no-op.

## When to Use This Pattern

Use archive-on-clear when:

- **Workflow state transitions**: Field represents an active workflow that completes (e.g., review_pr)
- **Historical tracking matters**: Users or systems need to see previous values
- **Audit requirements**: Need evidence of what happened in past iterations
- **State machine transitions**: Moving from one state to another, preserving the old state

## When NOT to Use This Pattern

Skip archiving when:

- **Ephemeral fields**: Temporary values that don't need history
- **Overwritten fields**: Fields that are always replaced, never cleared
- **Internal details**: Implementation details users don't care about
- **High-churn fields**: Values that change frequently and history is noise

## Schema Implications

Both the active and archived fields need validation rules:

```python
# Validate optional review_pr field
if REVIEW_PR in data and data[REVIEW_PR] is not None:
    if not isinstance(data[REVIEW_PR], int):
        raise ValueError("review_pr must be an integer or null")
    if data[REVIEW_PR] <= 0:
        raise ValueError("review_pr must be positive when provided")

# Validate optional last_review_pr field
if LAST_REVIEW_PR in data and data[LAST_REVIEW_PR] is not None:
    if not isinstance(data[LAST_REVIEW_PR], int):
        raise ValueError("last_review_pr must be an integer or null")
    if data[LAST_REVIEW_PR] <= 0:
        raise ValueError("last_review_pr must be positive when provided")
```

**Source:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py:734-745`

Both fields have:

- **Same type constraints** (integer or null)
- **Same value constraints** (positive when provided)
- **Same optional semantics** (both can be None)

## Testing the Pattern

Tests should verify the archived value matches the pre-clear value:

```python
def test_plan_review_complete_sets_last_review_pr(tmp_path: Path) -> None:
    """Test that the old review_pr is archived to last_review_pr."""
    issue_number = 7777
    review_pr_number = 111

    # Create issue with review_pr set
    body = make_plan_header_body(review_pr=review_pr_number)
    issue = make_issue_info(issue_number, body, ...)

    # Execute the clear operation
    runner.invoke(plan_review_complete, [str(issue_number)], ...)

    # Verify last_review_pr is set to the old review PR number
    assert f"last_review_pr: {review_pr_number}" in updated_body
```

**Source:** `tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py:279-313`

The test verifies:

1. **Before**: `review_pr` has a value
2. **After**: `last_review_pr` has the old value
3. **After**: `review_pr` is cleared

## Naming Convention

Use the `last_` prefix for archived fields:

- `review_pr` → `last_review_pr`
- `active_session` → `last_active_session`
- `current_branch` → `last_current_branch`

This convention makes the relationship clear: the `last_` variant holds the most recent archived value.

## Common Pitfalls

### Pitfall: Forgetting the None Check

**WRONG:**

```python
# Always archive, even if None
data[LAST_FIELD] = data[ACTIVE_FIELD]
```

This pollutes the archived field with None values when there was nothing to archive.

**CORRECT:**

```python
# Only archive if there's a value
current = data.get(ACTIVE_FIELD)
if current is not None:
    data[LAST_FIELD] = current
```

### Pitfall: Archiving After Clear

As shown earlier, clearing first loses the value. Always archive before clearing.

### Pitfall: Not Validating Both Fields

Both fields need the same validation rules. Don't forget to add schema constraints for the `last_` variant.

## Related Patterns

- **Metadata Blocks**: Archive-on-clear operates within metadata blocks (plan-header, etc.)
- **State Machines**: This pattern supports state machine transitions with history
- **Audit Trails**: Part of a broader audit trail strategy for workflow tracking

## Related Documentation

- [Plan Header Metadata](../planning/plan-header-metadata.md) - Plan-header schema and fields
- [Plan Review Lifecycle](../planning/lifecycle.md) - How review_pr/last_review_pr fit into plan lifecycle
- [Metadata Block Patterns](metadata-block-patterns.md) - General metadata block operations

## Attribution

Pattern implemented in plan review PR completion workflow (PR #6241 implementation).
