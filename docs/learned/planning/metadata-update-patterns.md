---
title: Metadata Update Patterns
read_when:
  - "writing plan dispatch metadata updates"
  - "choosing between assertive and best-effort metadata operations"
  - "working with write_dispatch_metadata or maybe_update_plan_dispatch_metadata"
tripwires:
  - action: "using assertive metadata writes in a best-effort context"
    warning: "write_dispatch_metadata() raises on error. maybe_update_plan_dispatch_metadata() uses LBYL guards and silent skip with warning. Choose based on whether failure should block the operation."
---

# Metadata Update Patterns

Two contrasting patterns for plan dispatch metadata updates exist in `src/erk/cli/commands/pr/metadata_helpers.py`.

## Assertive: `write_dispatch_metadata()`

<!-- Source: src/erk/cli/commands/pr/metadata_helpers.py, write_dispatch_metadata -->

Raises `RuntimeError` on any failure. Used when dispatch metadata is a hard requirement.

- Calls `get_workflow_run_node_id()` — raises if None
- Calls `get_plan()` — raises if PlanNotFound
- Calls `update_metadata()` directly

**Use when:** The caller cannot proceed without metadata being written.

## Best-Effort: `maybe_update_plan_dispatch_metadata()`

<!-- Source: src/erk/cli/commands/pr/metadata_helpers.py, maybe_update_plan_dispatch_metadata -->

Uses LBYL guards and returns silently when preconditions aren't met. Prints a warning for partial failures.

- Checks `resolve_plan_id_for_branch()` — returns if None
- Checks `get_workflow_run_node_id()` — returns if None
- Validates ALL required fields with set operations (`required_fields - all_metadata.keys()`)
- Prints dim-styled warning if plan-header is incomplete, then returns

**Use when:** Metadata update is optional and should not block the primary operation.

## Key Insight: Set-Based Field Validation

`maybe_update_plan_dispatch_metadata()` demonstrates proper LBYL for best-effort operations. It validates all required fields (`schema_version`, `created_at`, `created_by`) using set difference rather than checking a single field. This prevents partial updates that corrupt plan-header state.
