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
last_audited: "2026-02-16 08:00 PT"
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
- `update_dispatch_info.py` exits 1 on failure vs 0 in other scripts

These represent opportunities for future migration.

## Source Code References

| File                                                              | Key Components                             |
| ----------------------------------------------------------------- | ------------------------------------------ |
| `packages/erk-shared/src/erk_shared/plan_store/backend.py`        | `PlanBackend` ABC                          |
| `packages/erk-shared/src/erk_shared/plan_store/github.py`         | `GitHubPlanStore` implementation           |
| `packages/erk-shared/src/erk_shared/plan_store/types.py`          | `PlanNotFound`, `PlanHeaderNotFoundError`  |
| `packages/erk-shared/src/erk_shared/context/helpers.py`           | `require_plan_backend()`, `require_time()` |
| `src/erk/cli/commands/exec/scripts/upload_session.py`             | LBYL pattern with partial success          |
| `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` | LBYL pattern with error output             |

## Related Topics

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) -- the broader error handling pattern
- [Exec Script Testing](../testing/exec-script-testing.md) -- testing exec scripts with ErkContext.for_test()
- [Exec Script Environment Requirements](../ci/exec-script-environment-requirements.md) -- environment variables needed in workflows
