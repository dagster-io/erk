---
title: PlanBackend Migration Pattern
read_when:
  - "migrating exec scripts to use PlanBackend"
  - "working with require_plan_backend"
  - "understanding post_event vs update_metadata"
  - "Phase 3 PlanBackend consolidation"
tripwires:
  - action: "calling gh api directly in an exec script for plan metadata updates"
    warning: "Use `require_plan_backend(ctx)` + backend methods instead. Direct gh calls bypass the abstraction and testability layers."
  - action: "choosing between post_event and update_metadata"
    warning: "post_event = metadata update + optional comment. update_metadata = metadata only. Use post_event when the operation should be visible to users in the issue timeline."
---

# PlanBackend Migration Pattern

Pattern for migrating exec scripts from direct GitHub CLI calls to the `PlanBackend` abstraction. Part of Objective #6864 "Consolidate Plan Operations Behind PlanBackend".

## Context

Exec scripts historically used direct `gh` CLI calls to update plan issue metadata and post comments. The PlanBackend abstraction (a Backend ABC, not a Gateway) provides a testable, provider-agnostic interface for these operations.

## Migration Pattern

### Before: Direct `gh` Calls

```python
# Old pattern: direct subprocess calls
subprocess.run(["gh", "api", f"repos/{owner}/{repo}/issues/{issue_number}", ...])
subprocess.run(["gh", "issue", "comment", str(issue_number), "--body", comment])
```

### After: PlanBackend

See `impl_signal.py` for a complete example:
[`src/erk/cli/commands/exec/scripts/impl_signal.py`](../../../src/erk/cli/commands/exec/scripts/impl_signal.py).

Key steps:

1. `from erk_shared.context.helpers import require_plan_backend`
2. `backend = require_plan_backend(ctx)`
3. Build metadata dict and comment via `render_erk_issue_event()`
4. `backend.post_event(repo_root, plan_ref.plan_id, metadata=metadata, comment=comment_body)`

## Method Selection

| Method              | What It Does                                | When to Use                                     |
| ------------------- | ------------------------------------------- | ----------------------------------------------- |
| `post_event()`      | Updates metadata AND posts optional comment | Operation should be visible in issue timeline   |
| `update_metadata()` | Updates metadata only                       | Silent state tracking (no user-visible comment) |
| `add_comment()`     | Posts comment only                          | Informational messages without state changes    |

## Example: impl_signal.py Migration (PR #7005)

`src/erk/cli/commands/exec/scripts/impl_signal.py` was migrated from direct `gh` calls to PlanBackend:

1. **Extract backend:** `backend = require_plan_backend(ctx)` with `SystemExit` catch
2. **Build metadata:** Context-aware fields (different for local vs GitHub Actions)
3. **Build comment:** Using `render_erk_issue_event()` for consistent formatting
4. **Post event:** Single `backend.post_event()` call

## Testing Pattern

See [Backend Testing Composition](../testing/backend-testing-composition.md) for the testing approach. The key pattern: inject `FakeGitHubIssues` into real `GitHubPlanStore`, then assert on fake mutation tracking properties.

## Remaining Phase 3 Work

Some exec scripts still use direct GitHub CLI calls and are candidates for migration. These can be identified by grepping for `gh api` or `gh issue` patterns in `src/erk/cli/commands/exec/scripts/`.

## Related Documentation

- [Gateway vs Backend](gateway-vs-backend.md) - Backend ABC (3-place) vs Gateway ABC (5-place)
- [Backend Testing Composition](../testing/backend-testing-composition.md) - Testing pattern
- [PlanBackend ABC Methods](plan-backend-methods.md) - Complete method reference
