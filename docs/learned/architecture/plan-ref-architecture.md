---
title: PlanRef Architecture
read_when:
  - "working with plan-ref.json"
  - "working with PlanRef dataclass"
  - "migrating from IssueReference to PlanRef"
  - "understanding provider-agnostic plan references"
tripwires:
  - action: "accessing plan_ref.plan_id as int without checking"
    warning: "plan_id is a string. Use LBYL: `plan_ref.plan_id.isdigit()` before `int(plan_ref.plan_id)`. Supports future non-numeric providers like 'PROJ-123'."
  - action: "calling save_plan_ref with positional arguments"
    warning: "All parameters after `impl_dir` are keyword-only. Positional calls will fail at runtime."
---

# PlanRef Architecture

PlanRef is the provider-agnostic plan reference abstraction stored in `.impl/plan-ref.json`. It replaced the GitHub-specific `IssueReference` to support future plan providers.

## Why PlanRef Replaced IssueReference

The original `IssueReference` was tightly coupled to GitHub:

- Fields: `issue_number` (int), `issue_url` (str)
- File: `.impl/issue.json`
- Only supported GitHub issues as plan storage

PlanRef generalizes this:

- Fields: `provider`, `plan_id` (str), `url`, `labels`, `objective_id`
- File: `.impl/plan-ref.json`
- Designed for any plan provider (GitHub, Jira, Linear, etc.)

## PlanRef Dataclass

Defined in `packages/erk-shared/src/erk_shared/impl_folder.py`:

See the `PlanRef` dataclass in
[`packages/erk-shared/src/erk_shared/impl_folder.py`](../../../packages/erk-shared/src/erk_shared/impl_folder.py).

Key fields: `provider` (`PlanProviderType`), `plan_id` (str), `url`, `created_at`, `synced_at`, `labels` (tuple), `objective_id` (int | None).

### String `plan_id` Rationale

`plan_id` is deliberately a `str`, not `int`, to support future providers where plan identifiers are non-numeric (e.g., Jira's `PROJ-123`). GitHub issue numbers are stored as strings and converted at callsites when needed.

## API Functions

### `save_plan_ref(impl_dir, *, provider, plan_id, url, labels, objective_id)`

Saves a plan reference to `plan-ref.json`. All parameters after `impl_dir` are keyword-only. Raises `FileNotFoundError` if `impl_dir` doesn't exist.

### `read_plan_ref(impl_dir) -> PlanRef | None`

Reads plan reference with backward compatibility:

1. Tries `plan-ref.json` first (new format)
2. Falls back to `issue.json` (legacy format)
3. Returns `None` if neither exists or is valid

The legacy fallback maps old fields to new PlanRef structure:

- `issue_number` -> `plan_id` (converted to string)
- `issue_url` -> `url`
- Defaults: `provider="github"`, `labels=()`, `objective_id=None`

### `has_plan_ref(impl_dir) -> bool`

Returns `True` if either `plan-ref.json` or legacy `issue.json` exists.

### `validate_plan_linkage(impl_dir, branch_name) -> str | None`

Validates that branch name and plan reference agree:

- Extracts issue number from branch name (pattern: `P{issue}-{slug}`)
- Reads plan reference from impl directory
- Raises `ValueError` if both sources disagree
- Returns `plan_id` as string if discoverable, `None` otherwise

## The `plan_id` String-to-Int Conversion Pattern

Since `plan_id` is a string but GitHub APIs require integers, callsites must convert carefully:

```python
# Correct: LBYL before conversion
if plan_ref.plan_id.isdigit():
    issue_number = int(plan_ref.plan_id)
else:
    # Handle non-numeric plan_id
    ...
```

This pattern appears at several callsites across the codebase.

## erk-statusline's Duplicate Reader

The `erk-statusline` package has its own plan-ref reading logic via `_load_impl_data()`, `get_issue_number()`, and `get_objective_issue()` because it cannot import from `erk_shared` (separate package with no dependency). This duplication is intentional and must be kept in sync manually.

## Related Documentation

- [Issue Reference Flow](issue-reference-flow.md) - How plan references flow to PR bodies
- [Plan Lifecycle](../planning/lifecycle.md) - Complete plan lifecycle documentation
