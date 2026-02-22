---
title: PlanBackend Migration Guide
read_when:
  - "migrating exec scripts from direct GitHubIssues to PlanBackend"
  - "implementing LBYL pattern for plan existence checks"
  - "handling PlanNotFound vs PlanHeaderNotFoundError"
tripwires:
  - action: "calling update_metadata() on PlanBackend"
    warning: "Always check isinstance(result, PlanNotFound) before calling update_metadata()"
  - action: "catching PlanHeaderNotFoundError"
    warning: "PlanHeaderNotFoundError is an exception; PlanNotFound is a result type - use LBYL for the latter"
last_audited: "2026-02-16 14:30 PT"
audit_result: clean
---

# PlanBackend Migration Guide

When exec scripts need to read or update plan issues, use `PlanBackend` instead of direct `GitHubIssues` calls. PlanBackend provides typed abstractions with discriminated union error handling.

## Migration Pattern

**Before (direct GitHubIssues):**

```python
gh = require_issues(ctx)
issue = gh.get_issue(repo_root, issue_number)
# No type safety on failure case
```

**After (PlanBackend):**

```python
backend = require_plan_backend(ctx)
plan_result = backend.get_plan(repo_root, plan_id)
if isinstance(plan_result, PlanNotFound):
    # Handle missing plan explicitly
    return
# plan_result is now typed as Plan
```

## LBYL Pattern for Plan Existence

Always check plan existence **before** calling mutation methods:

```python
backend = require_plan_backend(ctx)
plan_id = str(issue_number)

# LBYL: Check plan exists before updating
plan_result = backend.get_plan(repo_root, plan_id)
if isinstance(plan_result, PlanNotFound):
    output_error("issue-not-found", f"Issue #{issue_number} not found")
    return

# Safe to update
backend.update_metadata(repo_root, plan_id, metadata)
```

## Error Type Distinction

Two different error types serve different purposes:

| Type                      | Kind                     | Use                                                   |
| ------------------------- | ------------------------ | ----------------------------------------------------- |
| `PlanNotFound`            | Result type (dataclass)  | Returned by `get_plan()` when issue doesn't exist     |
| `PlanHeaderNotFoundError` | Exception (RuntimeError) | Raised when plan exists but metadata block is missing |

**PlanNotFound** is checked with `isinstance()` (LBYL pattern). **PlanHeaderNotFoundError** is caught with try/except because it indicates a corrupted plan state that cannot be predicted.

```python
plan_result = backend.get_plan(repo_root, plan_id)
if isinstance(plan_result, PlanNotFound):
    # Plan doesn't exist at all
    return

try:
    backend.update_metadata(repo_root, plan_id, metadata)
except PlanHeaderNotFoundError:
    # Plan exists but has no plan-header metadata block
    output_error("no-plan-header-block", str(e))
except RuntimeError:
    # GitHub API failure
    output_error("github-api-failed", str(e))
```

## Partial Success Handling

Some exec scripts create artifacts (like gists) before updating plan metadata. When the first operation succeeds but the plan update fails, report partial success:

```python
# Gist already created successfully
plan_result = backend.get_plan(repo_root, plan_id)
if isinstance(plan_result, PlanNotFound):
    result["issue_updated"] = False
    result["issue_update_error"] = f"Issue #{issue_number} not found"
else:
    try:
        backend.update_metadata(repo_root, plan_id, metadata)
        result["issue_updated"] = True
    except RuntimeError as e:
        result["issue_updated"] = False
        result["issue_update_error"] = str(e)
```

This pattern ensures the gist URL is still reported even if the plan issue update fails.

## Time Abstraction

Use `require_time(ctx)` instead of `datetime.now()` for deterministic tests:

```python
time = require_time(ctx)
metadata = {"updated_at": time.now().isoformat()}
```

In tests, `ErkContext.for_test()` provides a fake Time that returns predictable values.

## Testing Pattern

```python
def test_my_exec_script(tmp_path: Path) -> None:
    fake_gh = FakeGitHubIssues()
    fake_gh.add_issue(...)

    ctx = ErkContext.for_test(
        cwd=tmp_path,
        github_issues=fake_gh,  # auto-wires PlanBackend
    )
```

`ErkContext.for_test(github_issues=fake_gh)` automatically creates a `GitHubPlanStore` backed by the fake, so `require_plan_backend(ctx)` returns a working implementation.

## Known Inconsistencies

Some scripts have not been fully migrated to the LBYL pattern:

- `mark_impl_started.py` and `mark_impl_ended.py` lack LBYL checks before `update_metadata()`

These represent opportunities for future migration.

## PlanBackend Methods

Key methods on `PlanBackend` ABC (`packages/erk-shared/src/erk_shared/plan_store/backend.py`):

| Method                                             | Returns                  | Description                                 |
| -------------------------------------------------- | ------------------------ | ------------------------------------------- |
| `get_plan(repo_root, plan_id)`                     | `Plan \| PlanNotFound`   | Fetch full plan by ID                       |
| `get_metadata_field(repo_root, plan_id, field)`    | `object \| PlanNotFound` | Get a single metadata field value           |
| `update_metadata(repo_root, plan_id, metadata)`    | `None \| PlanNotFound`   | Update metadata fields in plan header block |
| `add_label(repo_root, plan_id, label)`             | `None` (raises on fail)  | Add a label to a plan (line 398-414)        |
| `post_event(repo_root, plan_id, event_type, data)` | `None`                   | Post a lifecycle event to the plan          |

`add_label()` raises `RuntimeError` if the provider fails or the plan is not found (unlike `get_plan`/`update_metadata` which use the `PlanNotFound` result type).

## Source Code References

| File                                                       | Key Components                             |
| ---------------------------------------------------------- | ------------------------------------------ |
| `packages/erk-shared/src/erk_shared/plan_store/backend.py` | `PlanBackend` ABC                          |
| `packages/erk-shared/src/erk_shared/plan_store/github.py`  | `GitHubPlanStore` implementation           |
| `packages/erk-shared/src/erk_shared/plan_store/types.py`   | `PlanNotFound`, `PlanHeaderNotFoundError`  |
| `packages/erk-shared/src/erk_shared/context/helpers.py`    | `require_plan_backend()`, `require_time()` |
| `src/erk/cli/commands/exec/scripts/upload_session.py`      | LBYL pattern with partial success          |

## get_metadata_field Returns object | PlanNotFound

`PlanBackend.get_metadata_field()` returns `object | PlanNotFound`. The `object` return type requires type narrowing at the call site — use LBYL to check for `PlanNotFound` first, then cast or assert the expected type.

## Error Handling Asymmetry: get vs update

`get_metadata_field()` returns `PlanNotFound` when the plan issue doesn't exist. `update_metadata()` also returns `PlanNotFound`. However, the semantics differ:

- **get**: caller typically wants to branch on the result (display vs skip)
- **update**: caller typically wants to report failure and continue

This means get callers use LBYL branching, while update callers use LBYL with best-effort continuation.

## Plan.header_fields over extract for loaded Plans

When you already have a loaded `Plan` object, access header fields via `plan.header_fields` instead of re-extracting from the raw body. The `header_fields` property returns a parsed dict that avoids re-parsing the metadata block.

## Related Topics

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) -- the broader error handling pattern
- [Exec Script Testing](../testing/exec-script-testing.md) -- testing exec scripts with ErkContext.for_test()
- [Exec Script Environment Requirements](../ci/exec-script-environment-requirements.md) -- environment variables needed in workflows
