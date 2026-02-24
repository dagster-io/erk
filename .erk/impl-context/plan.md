# Fix: Remote session discovery broken for draft-PR plans

## Context

When a remote implementation runs in GitHub Actions for a draft-PR-backed plan, the learn workflow fails to discover the remote session. The `trigger-async-learn` pipeline only finds the local (empty/warmup) session and misses the remote implementation session entirely. This means learn can't analyze the implementation that actually happened.

**Root cause:** `PlanBackend.find_sessions_for_plan()` extracts session metadata by calling `extract_plan_header_*()` functions on `plan.body`. For issue-based plans, `plan.body` includes the metadata block. For draft-PR plans, `plan.body` is the **stripped plan content** (metadata removed by `extract_plan_content()` in `_convert_to_plan()`). All `extract_plan_header_*()` calls return `None`, so `SessionsForPlan` has empty session fields, and `_discover_sessions()` never adds a `RemoteSessionSource`.

**Fix:** Use `plan.header_fields` (already correctly parsed for both backends) instead of re-parsing `plan.body`.

## Changes

### 1. `packages/erk-shared/src/erk_shared/plan_store/backend.py`

**Replace imports** (lines 26-36): Remove `extract_plan_header_*` imports. Add:
```python
from erk_shared.gateway.github.metadata.schemas import (
    CREATED_FROM_SESSION,
    LAST_LEARN_SESSION,
    LAST_LOCAL_IMPL_SESSION,
    LAST_REMOTE_IMPL_AT,
    LAST_REMOTE_IMPL_RUN_ID,
    LAST_REMOTE_IMPL_SESSION_ID,
    LAST_SESSION_BRANCH,
    LAST_SESSION_ID,
    LAST_SESSION_SOURCE,
)
from erk_shared.plan_store.conversion import header_str
```

**Refactor `find_sessions_for_plan()`** (lines 200-246): Replace body-parsing with `header_fields` reads:

```python
plan = self.get_plan(repo_root, plan_id)
if isinstance(plan, PlanNotFound):
    msg = f"Plan {plan_id} not found"
    raise RuntimeError(msg)

hf = plan.header_fields
planning_session_id = header_str(hf, CREATED_FROM_SESSION)
metadata_impl_session = header_str(hf, LAST_LOCAL_IMPL_SESSION)
metadata_learn_session = header_str(hf, LAST_LEARN_SESSION)

# ... comment extraction (unchanged) ...

return SessionsForPlan(
    planning_session_id=planning_session_id,
    implementation_session_ids=implementation_session_ids,
    learn_session_ids=learn_session_ids,
    last_remote_impl_at=header_str(hf, LAST_REMOTE_IMPL_AT),
    last_remote_impl_run_id=header_str(hf, LAST_REMOTE_IMPL_RUN_ID),
    last_remote_impl_session_id=header_str(hf, LAST_REMOTE_IMPL_SESSION_ID),
    last_session_branch=header_str(hf, LAST_SESSION_BRANCH),
    last_session_id=header_str(hf, LAST_SESSION_ID),
    last_session_source=header_str(hf, LAST_SESSION_SOURCE),
)
```

Remove the `body = plan.body` line (no longer needed). The `comments = self.get_comments(repo_root, plan_id)` line and everything after it remain unchanged.

### 2. `src/erk/cli/commands/wt/delete_cmd.py` (line 71)

Same pattern - uses `extract_plan_header_worktree_name(plan.body)`. Fix:

```python
# Before
from erk_shared.gateway.github.metadata.plan_header import extract_plan_header_worktree_name
plan_worktree_name = extract_plan_header_worktree_name(plan.body)

# After
from erk_shared.gateway.github.metadata.schemas import WORKTREE_NAME
from erk_shared.plan_store.conversion import header_str
plan_worktree_name = header_str(plan.header_fields, WORKTREE_NAME)
```

### 3. `tests/unit/plan_store/test_plan_backend_interface.py`

Add a parameterized test that runs against both backends:
- Create a plan, update its metadata with session fields (`last_session_branch`, `last_session_id`, `created_from_session`, etc.)
- Call `find_sessions_for_plan()`
- Assert all session fields are populated (not None)

This test would have caught the bug since it would fail for the draft-PR backend before the fix.

## Key utilities being reused

- `header_str()` from `packages/erk-shared/src/erk_shared/plan_store/conversion.py:115` - handles `object -> str | None` coercion (str passthrough, datetime `.isoformat()`, other types `str()`)
- Schema constants from `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py` (all exist, verified)
- `plan.header_fields` already populated correctly for both backends in `pr_details_to_plan()` and `issue_info_to_plan()`

## Verification

1. Run existing tests: `pytest tests/unit/plan_store/test_plan_backend_interface.py`
2. Run new regression test to confirm session fields are populated for draft-PR backend
3. Run `pytest tests/unit/cli/commands/` for any wt/delete related tests
4. Run full fast CI to catch any import/type issues
