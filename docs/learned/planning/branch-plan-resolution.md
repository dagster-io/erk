---
title: Branch Plan Resolution
read_when:
  - "resolving which plan a branch belongs to"
  - "working with branch naming conventions for plans"
  - "understanding how get_plan_for_branch works"
tripwires:
  - action: "assuming branch names always follow the P-prefix format"
    warning: "Branch resolution supports multiple formats (P-prefix, objective). Use resolve_plan_id_for_branch() rather than manual parsing. See branch-plan-resolution.md."
---

# Branch Plan Resolution

Given a branch name, resolve which plan it belongs to.

## Methods

Both methods are in `packages/erk-shared/src/erk_shared/plan_store/github.py` on the GitHubPlanStore class.

### `resolve_plan_id_for_branch()`

Zero-cost operation (lines 94-110) — regex-based, no API calls. Parses the branch naming convention to extract a plan ID.

- Uses `extract_leading_issue_number()` from `erk_shared.naming`
- Returns plan ID as string if branch matches a known pattern, `None` otherwise
- Does NOT verify the plan exists in GitHub

### `get_plan_for_branch()`

Full resolution (lines 112-127) — resolves branch name to plan ID, then fetches the plan.

- Calls `resolve_plan_id_for_branch()` first
- Returns `Plan | PlanNotFound` discriminated union (not an exception)
- Returns `PlanNotFound(plan_id=branch_name)` if branch doesn't match any pattern

## Supported Branch Formats

- **P-prefix**: `P{number}-{slug}` — standard plan branches
- **Objective format**: `P{number}-O{objective}-{slug}` — plans linked to objectives
- **Legacy formats**: Handled via `extract_leading_issue_number()`

## Error Types

Defined in `packages/erk-shared/src/erk_shared/plan_store/types.py`:

- **`PlanNotFound`** (lines 84-87): Frozen dataclass with `plan_id: str`. Returned when a plan can't be found — used as a return type, not an exception (per erk convention).
- **`PlanHeaderNotFoundError`** (lines 79-80): Exception inheriting from `RuntimeError`. Raised when a plan exists but has no plan-header metadata block. Distinct from "plan not found."

## Related Topics

- [Draft PR Plan Backend](draft-pr-plan-backend.md) - Backend that also supports branch resolution
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Pattern for PlanNotFound return type
