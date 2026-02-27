---
title: Branch Plan Resolution
read_when:
  - "resolving which plan a branch belongs to"
  - "working with branch naming conventions for plans"
  - "understanding how get_plan_for_branch works"
tripwires:
  - action: "assuming branch names always follow the P-prefix format"
    warning: "Branch resolution supports multiple formats (P-prefix, objective). Use resolve_plan_id_for_branch() rather than manual parsing. See branch-plan-resolution.md."
  - action: "extracting plan ID from branch name instead of using plan-ref.json"
    warning: "plan-ref.json is sole source of truth. validate_plan_linkage() only reads plan-ref.json. get_branch_issue() and resolve_plan_id_for_branch() always return None."
---

# Branch Plan Resolution

Given a branch name, resolve which plan it belongs to.

## Methods

These methods live on `PlannedPRBackend` in `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`, accessed via the `PlanBackend` interface.

### `resolve_plan_id_for_branch()`

Queries GitHub for a draft PR on the branch. Returns the PR number as a string if found, `None` otherwise.

- Delegates to `GitHub.get_pr_for_branch()` — requires an API call
- Returns plan ID as string if a draft PR exists, `None` otherwise
- Does NOT fetch full plan content

### `get_plan_for_branch()`

Full resolution — resolves branch name to plan via draft PR lookup, then converts to Plan.

- Calls `GitHub.get_pr_for_branch()` internally
- Returns `Plan | PlanNotFound` discriminated union (not an exception)
- Returns `PlanNotFound(plan_id=branch_name)` if no draft PR exists for the branch

## Supported Branch Formats

- **P-prefix**: `P{number}-{slug}` — legacy plan branches (current format is `plnd/`)
- **Objective format**: `P{number}-O{objective}-{slug}` — plans linked to objectives
- **Legacy formats**: No longer resolved from branch names; use `plan-ref.json`

## Error Types

Defined in `packages/erk-shared/src/erk_shared/plan_store/types.py`:

- **`PlanNotFound`**: Frozen dataclass with `plan_id: str`. Returned when a plan can't be found — used as a return type, not an exception (per erk convention).
- **`PlanHeaderNotFoundError`**: Exception inheriting from `RuntimeError`. Raised when a plan exists but has no plan-header metadata block. Distinct from "plan not found."

## Related Topics

- [Draft PR Plan Backend](draft-pr-plan-backend.md) - Backend that also supports branch resolution
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Pattern for PlanNotFound return type
