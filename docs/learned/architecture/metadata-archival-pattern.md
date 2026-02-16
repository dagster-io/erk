---
title: Archive-on-Clear Metadata Pattern
read_when:
  - clearing a metadata field that should be auditable
  - adding companion fields for historical tracking
  - extending plan-header schema with lifecycle transitions
tripwires:
  - action: "archiving value to 'last_' variant BEFORE clearing"
    warning: "Order matters — clear-then-archive loses the value silently"
    score: 6
last_audited: "2026-02-16 14:05 PT"
audit_result: clean
---

# Archive-on-Clear Metadata Pattern

When clearing a metadata field that tracks active workflow state, archive its value to a `last_` companion field first. This pattern preserves audit trails for completed workflows while maintaining clean active state.

## Why This Pattern Exists

Metadata fields in plan-header blocks track **active** workflow state (e.g., `review_pr` for an ongoing review). When workflows complete, these fields must be cleared to signal completion. But clearing loses historical context — which review PR was this? When did it complete?

The archive-on-clear pattern solves this by:

1. **Preserving evidence** of completed workflows for debugging and audit
2. **Signaling completion** via `None` in the active field
3. **Maintaining single source of truth** — one field for active state, one for history

## The Critical Ordering Rule

**Archive BEFORE clear.** This is the most common failure mode.

**Why order matters**: The archive step reads the current value. If you clear first, the current value is gone and cannot be archived.

**Anti-pattern (WRONG — silently loses value):**

```python
# Clear first
data[ACTIVE_FIELD] = None

# Try to archive (too late!)
current = data.get(ACTIVE_FIELD)  # Always None now
if current is not None:
    data[LAST_FIELD] = current  # Never executes
```

**Correct pattern:**

```python
# Archive current value (if present)
current = data.get(ACTIVE_FIELD)
if current is not None:
    data[LAST_FIELD] = current

# Then clear
data[ACTIVE_FIELD] = None
```

The None check prevents overwriting existing archived values with None.

## Pattern in Context

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py, clear_plan_header_review_pr -->

See `clear_plan_header_review_pr()` in plan_header.py for the canonical implementation. This function archives `review_pr` → `last_review_pr` when plan review completes.

Currently, the only field using the full archive-on-clear pattern is:

- **Plan review completion**: `review_pr` → `last_review_pr` (review PR closed)

Note: Other `last_` prefixed fields (e.g., `last_session_id`, `last_local_impl_at`) use direct overwrite, not archive-on-clear. They track "most recent value" without a separate active/archived pair. The archive-on-clear pattern applies specifically when a field must be **cleared to signal completion** while preserving its previous value.

## Naming Convention

Use the `last_` prefix for archived fields:

- `review_pr` → `last_review_pr`
- `session_id` → `last_session_id`
- `dispatched_run_id` → `last_dispatched_run_id`

This naming signals "most recent historical value" vs "current active value."

## Decision Table: When to Archive

| Scenario                                        | Archive? | Why                                                             |
| ----------------------------------------------- | -------- | --------------------------------------------------------------- |
| Field represents active workflow that completes | ✓        | History matters for debugging (which review PR? which session?) |
| Field is state machine transition               | ✓        | Understanding previous state is valuable                        |
| Field is ephemeral/always overwritten           | ✗        | History would be noise (high-churn fields)                      |
| Field is permanent metadata                     | ✗        | No concept of "clearing" (e.g., `created_at`)                   |

**Example requiring archival**: `review_pr` — when review completes, we clear the active field but need to know which PR was reviewed.

**Example not requiring archival**: `last_modified_at` — always overwritten with new value, history isn't meaningful.

## Schema Implications

Both active and archived fields need **identical type constraints**. If the active field is `int | None`, the archived field must be too. This ensures validation works correctly across the lifecycle.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py, PlanHeaderSchema.validate -->

See `PlanHeaderSchema.validate()` in `schemas.py` for the canonical validation of both `REVIEW_PR` and `LAST_REVIEW_PR` with identical constraints.

## Testing the Pattern

<!-- Source: tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py, test_plan_review_complete_sets_last_review_pr -->

See `test_plan_review_complete_sets_last_review_pr()` for test pattern. The test verifies:

1. Active field contains value before operation
2. Operation completes successfully
3. Archived field (`last_review_pr`) contains the old value
4. Active field (`review_pr`) is now None

## Common Mistakes

### Forgetting the None Check

```python
# WRONG: Always archives, even if None
data[LAST_FIELD] = data[ACTIVE_FIELD]

# CORRECT: Only archive if there's a value
current = data.get(ACTIVE_FIELD)
if current is not None:
    data[LAST_FIELD] = current
```

Without the None check, you'll overwrite a valid archived value with None when the active field is already None (e.g., during repeated operations).

### Not Validating Both Fields

Validation schemas must include **both** active and archived fields with identical constraints. If you add an archived field, update the schema validation to ensure it accepts the same types as the active field.

## Related Documentation

- [Plan Review Lifecycle](../planning/lifecycle.md) — How `review_pr`/`last_review_pr` fit into the full plan lifecycle (see Phase 2b: Plan Review)
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — Related pattern for state transitions with error handling
