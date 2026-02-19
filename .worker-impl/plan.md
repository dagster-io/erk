# Plan: Address PR #7503 Review Comments

## Context

PR #7503 migrates the learn workflow system to PlanBackend abstraction. A reviewer
requested that three inline imports inside the `find_sessions_for_plan` method be
moved to top-level module imports. This is a style fix with no behavioral change.

## Review Thread

- **Thread**: `PRRT_kwDOPxC3hc5vh0kX`
- **File**: `packages/erk-shared/src/erk_shared/plan_store/backend.py:203`
- **Request**: Move inline imports to top-level

## Circular Import Analysis

No circular import risk:
- `plan_header.py` does NOT import from `plan_store`
- `impl_events.py` does NOT import from `plan_store`
- `discovery.py` has inline import of `GitHubPlanStore` (inside a deprecated function,
  not top-level), so promoting `SessionsForPlan` to a top-level import in `backend.py`
  is safe

## Changes Required

**File**: `packages/erk-shared/src/erk_shared/plan_store/backend.py`

### 1. Remove `SessionsForPlan` from `TYPE_CHECKING` block (lines 30-31)
The `TYPE_CHECKING` import was a placeholder; it's needed at runtime for instantiation.
Replace with a direct top-level import.

### 2. Add top-level imports (after existing imports, before the class definition)
Move these three import blocks from inline (lines 188-203) to top-level:

```python
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_created_from_session,
    extract_plan_header_last_learn_session,
    extract_plan_header_last_session_id,
    extract_plan_header_last_session_source,
    extract_plan_header_local_impl_session,
    extract_plan_header_remote_impl_at,
    extract_plan_header_remote_impl_run_id,
    extract_plan_header_remote_impl_session_id,
    extract_plan_header_session_gist_url,
)
from erk_shared.learn.impl_events import (
    extract_implementation_sessions,
    extract_learn_sessions,
)
from erk_shared.sessions.discovery import SessionsForPlan
```

### 3. Remove the inline import block from `find_sessions_for_plan`
Delete lines 188-203 (the three `from ... import` blocks inside the method body).

### 4. Update the return statement
Replace `_SessionsForPlan(...)` with `SessionsForPlan(...)` at line 241
(no longer needs the `_` alias).

## Commit

```
git add packages/erk-shared/src/erk_shared/plan_store/backend.py
git commit -m "Move inline imports to top-level in backend.py

Address PR review request: move find_sessions_for_plan inline imports
to module-level."
```

## CI Checks

Run `make fast-ci` to verify no regressions.

## Thread Resolution

After CI passes and commit is created:

```bash
echo '[{"thread_id": "PRRT_kwDOPxC3hc5vh0kX", "comment": "Moved all three inline imports to top-level in commit <sha>"}]' | erk exec resolve-review-threads
```

## Update PR Description

```bash
erk exec update-pr-description --session-id "${CLAUDE_SESSION_ID}"
```

## Submit

```bash
gt submit --no-interactive
```

## Verification

1. `make fast-ci` passes (lint, type-check, unit tests)
2. Review thread resolved in PR #7503
3. PR description updated