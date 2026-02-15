# Plan: Migrate update_dispatch_info.py, mark_impl_started/ended.py to PlanBackend

**Part of Objective #6864, Step 3.3**

## Context

This plan migrates three exec scripts to use the `PlanBackend` abstraction instead of directly calling `GitHubIssues` gateway and `plan_header` functions. This continues the work from step 3.1 (which migrated `impl_signal.py`) and step 3.2 (which migrated session-related scripts).

The scripts being migrated:

1. **`update_dispatch_info.py`** - Updates dispatch metadata (run_id, node_id, dispatched_at) in plan-header block. Currently uses `GitHubIssues.get_issue()` + `update_plan_header_dispatch()` + `GitHubIssues.update_issue_body()`.

2. **`mark_impl_started.py`** - Updates implementation started event metadata and writes local state. Currently uses `GitHubIssues.get_issue()` + `update_plan_header_local_impl_event()` or `update_plan_header_remote_impl()` + `GitHubIssues.update_issue_body()`.

3. **`mark_impl_ended.py`** - Updates implementation ended event metadata and writes local state. Currently uses `GitHubIssues.get_issue()` + `update_plan_header_local_impl_event()` or `update_plan_header_remote_impl()` + `GitHubIssues.update_issue_body()`.

All three scripts follow the same pattern:
- Fetch issue from GitHub
- Call a `plan_header` function to generate updated body text
- Post updated body back to GitHub

The `PlanBackend.update_metadata()` method replaces this entire sequence with a single high-level call that handles metadata block parsing, validation, and rendering internally.

## Migration Pattern (from step 3.1)

The migration pattern established in PR #7005 (`impl_signal.py`):

**Before:**
```python
from erk_shared.context.helpers import require_issues as require_github_issues
from erk_shared.gateway.github.metadata.plan_header import update_plan_header_*
from erk_shared.gateway.github.types import BodyText

github_issues = require_github_issues(ctx)
issue = github_issues.get_issue(repo_root, issue_number)
if isinstance(issue, IssueNotFound):
    # handle error

updated_body = update_plan_header_*(issue_body=issue.body, ...)
github_issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
```

**After:**
```python
from erk_shared.context.helpers import require_plan_backend

backend = require_plan_backend(ctx)
backend.update_metadata(
    repo_root,
    plan_ref.plan_id,
    metadata={
        "field_name": field_value,
        # ... all fields to update
    }
)
```

Key differences:
- Replace `require_github_issues()` → `require_plan_backend()`
- Remove manual `get_issue()` call (backend handles it)
- Remove `update_plan_header_*()` call (backend handles it)
- Remove `update_issue_body()` call (backend handles it)
- Remove `IssueNotFound` checks (backend raises `RuntimeError` on failure)
- Build a metadata dict with field names and values
- Use `plan_ref.plan_id` instead of `issue_number` (supports future PR-based plans)

## Changes

### 1. Migrate `update_dispatch_info.py` to use PlanBackend

**File:** `src/erk/cli/commands/exec/scripts/update_dispatch_info.py`

**Current implementation:**
- Takes `issue_number` as Click argument
- Calls `require_github_issues(ctx)` to get GitHub gateway
- Calls `github_issues.get_issue(repo_root, issue_number)`
- Checks for `IssueNotFound` sentinel
- Calls `update_plan_header_dispatch(issue_body, run_id, node_id, dispatched_at)`
- Handles `ValueError` if plan-header block not found
- Calls `github_issues.update_issue_body()`
- Handles `RuntimeError` on GitHub API failure

**Migration steps:**

1. **Change imports:**
   - Remove: `require_issues as require_github_issues`
   - Remove: `IssueNotFound`
   - Remove: `update_plan_header_dispatch`
   - Remove: `BodyText`
   - Add: `require_plan_backend` from `erk_shared.context.helpers`

2. **Replace gateway call with backend call:**
   ```python
   # Get dependencies from context
   backend = require_plan_backend(ctx)
   repo_root = require_repo_root(ctx)

   # Update dispatch info via PlanBackend
   try:
       backend.update_metadata(
           repo_root,
           str(issue_number),
           metadata={
               "last_dispatched_run_id": run_id,
               "last_dispatched_node_id": node_id,
               "last_dispatched_at": dispatched_at,
           }
       )
   except RuntimeError as e:
       result = UpdateError(
           success=False,
           error="update-failed",
           message=f"Failed to update dispatch info: {e}",
       )
       click.echo(json.dumps(asdict(result)), err=True)
       raise SystemExit(1) from None
   ```

3. **Remove issue fetch logic:**
   - Remove `issue = github_issues.get_issue(repo_root, issue_number)` call
   - Remove `if isinstance(issue, IssueNotFound):` check
   - Remove `updated_body = update_plan_header_dispatch(...)` call
   - Remove separate `github_issues.update_issue_body()` call

4. **Error handling changes:**
   - `IssueNotFound` check → remove (backend raises `RuntimeError` if plan not found)
   - `ValueError` for missing plan-header → remove (backend raises `RuntimeError` if metadata block invalid)
   - Single `RuntimeError` catch handles all backend failures (includes issue not found, no plan-header, GitHub API failure)
   - Consolidate error codes: use `"update-failed"` instead of separate `"issue-not-found"`, `"no-plan-header-block"`, `"github-api-failed"`

5. **Keep existing:**
   - Click command signature (`issue_number` argument stays)
   - Result dataclasses (`UpdateSuccess`, `UpdateError`)
   - JSON output format
   - Exit code 1 on error

**Note:** Unlike `mark_impl_started/ended`, this script takes `issue_number` as a Click argument rather than reading from `.impl/plan-ref.json`. This is correct - the script is called from CI workflows that dispatch to specific issue numbers.

### 2. Migrate `mark_impl_started.py` to use PlanBackend

**File:** `src/erk/cli/commands/exec/scripts/mark_impl_started.py`

**Current implementation:**
- Reads plan reference from `.impl/plan-ref.json`
- Writes local state to `.impl/local-run-state.json` (keep this)
- Calls `require_github_issues(ctx)` to get GitHub gateway
- Calls `github_issues.get_issue(repo_root, int(plan_ref.plan_id))`
- Checks for `IssueNotFound` sentinel
- Calls `update_plan_header_local_impl_event()` or `update_plan_header_remote_impl()` based on environment
- Handles `ValueError` if plan-header block not found
- Calls `github_issues.update_issue_body()`
- Handles `RuntimeError` on GitHub API failure

**Migration steps:**

1. **Change imports:**
   - Remove: `require_issues as require_github_issues`
   - Remove: `IssueNotFound`
   - Remove: `update_plan_header_local_impl_event`
   - Remove: `update_plan_header_remote_impl`
   - Remove: `BodyText`
   - Add: `require_plan_backend` from `erk_shared.context.helpers`

2. **Replace gateway call with backend call:**
   ```python
   # Get PlanBackend from context
   try:
       backend = require_plan_backend(ctx)
   except SystemExit:
       result = MarkImplError(
           success=False,
           error_type="context-not-initialized",
           message="Context not initialized",
       )
       click.echo(json.dumps(asdict(result), indent=2))
       raise SystemExit(0) from None

   # Build metadata dict based on environment
   metadata: dict[str, object] = {}
   if in_github_actions():
       metadata["last_remote_impl_at"] = timestamp
   else:
       metadata["last_local_impl_at"] = timestamp
       metadata["last_local_impl_event"] = "started"
       metadata["last_local_impl_session"] = session_id
       metadata["last_local_impl_user"] = user

   # Update impl event via PlanBackend
   try:
       backend.update_metadata(repo_root, plan_ref.plan_id, metadata)
   except RuntimeError as e:
       result = MarkImplError(
           success=False,
           error_type="update-failed",
           message=f"Failed to update metadata: {e}",
       )
       click.echo(json.dumps(asdict(result), indent=2))
       raise SystemExit(0) from None
   ```

3. **Remove issue fetch logic:**
   - Remove `issue = github_issues.get_issue(repo_root, int(plan_ref.plan_id))` call
   - Remove `if isinstance(issue, IssueNotFound):` check
   - Remove `updated_body = update_plan_header_local_impl_event(...)` or `update_plan_header_remote_impl(...)` call
   - Remove separate `github_issues.update_issue_body()` call

4. **Error handling changes:**
   - `issue-not-found` error → remove (merged into `update-failed`)
   - `no-plan-header-block` error → remove (merged into `update-failed`)
   - `github-api-failed` error → rename to `update-failed`
   - Single `RuntimeError` catch handles all backend failures

5. **Keep existing:**
   - Local state write (`write_local_run_state()` - happens before GitHub update)
   - Plan reference read (`read_plan_ref()`)
   - Session ID parameter
   - Environment detection (`in_github_actions()`)
   - Metadata capture (timestamp, user, session_id)
   - Result dataclasses (`MarkImplSuccess`, `MarkImplError`)
   - JSON output format
   - Exit code 0 always (graceful degradation)

### 3. Migrate `mark_impl_ended.py` to use PlanBackend

**File:** `src/erk/cli/commands/exec/scripts/mark_impl_ended.py`

**Current implementation:**
- Nearly identical to `mark_impl_started.py` but with `event="ended"` instead of `event="started"`
- Same gateway bypass pattern

**Migration steps:**

Identical to `mark_impl_started.py` migration, but with:
- `event="ended"` in metadata
- No session_id validation required (session_id can be None for ended)

### 4. Update tests for `update_dispatch_info.py`

**File:** `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py`

**Current test structure:**
- Already uses `ErkContext.for_test()` with `FakeGitHubIssues` (good!)
- Tests use `find_metadata_block()` to verify updated fields
- Tests cover success cases, error cases, JSON output structure

**Migration steps:**

1. **Update fake setup:**
   - Current tests inject `github_issues=fake_gh` into `ErkContext.for_test()`
   - After migration: inject `plan_backend=GitHubPlanBackend(fake_gh)`
   - Need to import `GitHubPlanBackend` from `erk_shared.plan_store.github`

2. **Update error case tests:**
   - `test_update_dispatch_info_issue_not_found`: Backend raises `RuntimeError` instead of returning `IssueNotFound`
   - Test should verify exit code 1 and `error="update-failed"` (not `"issue-not-found"`)
   - `test_update_dispatch_info_no_plan_header_block`: Backend raises `RuntimeError` for invalid metadata block
   - Test should verify `error="update-failed"` (not `"no-plan-header-block"`)
   - `test_update_dispatch_info_github_api_failure`: Still uses subclass override of `update_issue_body()`, but now we need to override `update_metadata()` on `GitHubPlanBackend`

3. **Update test helper to create proper plan backend:**
   ```python
   from erk_shared.plan_store.github import GitHubPlanBackend

   def _make_context_with_fake_issues(fake_gh: FakeGitHubIssues) -> ErkContext:
       backend = GitHubPlanBackend(fake_gh)
       return ErkContext.for_test(plan_backend=backend)
   ```

4. **Verify success cases still pass:**
   - `test_update_dispatch_info_success`: Should work unchanged (backend updates metadata)
   - `test_update_dispatch_info_overwrites_existing`: Should work unchanged
   - `test_update_dispatch_info_preserves_other_content`: Should work unchanged

### 5. Add tests for `mark_impl_started.py`

**File:** `tests/unit/cli/commands/exec/scripts/test_mark_impl_started.py`

**Current state:** Tests exist but may not follow the fake-driven pattern from step 3.1.

**Required tests:**

1. **Success cases:**
   - `test_mark_impl_started_local_environment`: Verify local metadata fields set
   - `test_mark_impl_started_github_actions`: Verify remote metadata field set
   - `test_mark_impl_started_writes_local_state`: Verify `.impl/local-run-state.json` created
   - `test_mark_impl_started_with_worker_impl_dir`: Verify works with `.worker-impl/`

2. **Error cases:**
   - `test_mark_impl_started_no_plan_ref`: Exit code 0, `error_type="no-issue-reference"`
   - `test_mark_impl_started_update_failed`: Backend raises `RuntimeError`, exit code 0, `error_type="update-failed"`
   - `test_mark_impl_started_local_state_write_failed`: Exit code 0, `error_type="local-state-write-failed"`

3. **Context injection:**
   - Use `ErkContext.for_test(cwd=tmp_path, plan_backend=backend)`
   - Create fake plan backend: `GitHubPlanBackend(FakeGitHubIssues(...))`
   - Set up `.impl/plan-ref.json` in `tmp_path`

4. **Assertions:**
   - Verify `FakeGitHubIssues.issues[N].body` contains updated metadata
   - Use `find_metadata_block()` to extract plan-header and check fields
   - Verify local state file contents match expected format

### 6. Add tests for `mark_impl_ended.py`

**File:** `tests/unit/cli/commands/exec/scripts/test_mark_impl_ended.py`

**Current state:** Tests exist but may not follow the fake-driven pattern.

**Required tests:**

Nearly identical to `mark_impl_started.py` tests, but:
- `event="ended"` instead of `"started"`
- Session ID can be None (no validation error)
- Verify `last_local_impl_event` or `last_remote_impl_at` updated correctly

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/update_dispatch_info.py` | Replace `GitHubIssues` calls with `PlanBackend.update_metadata()` |
| `src/erk/cli/commands/exec/scripts/mark_impl_started.py` | Replace `GitHubIssues` calls with `PlanBackend.update_metadata()` |
| `src/erk/cli/commands/exec/scripts/mark_impl_ended.py` | Replace `GitHubIssues` calls with `PlanBackend.update_metadata()` |
| `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py` | Update to use `GitHubPlanBackend` with `FakeGitHubIssues` |
| `tests/unit/cli/commands/exec/scripts/test_mark_impl_started.py` | Rewrite or update to use fake-driven pattern |
| `tests/unit/cli/commands/exec/scripts/test_mark_impl_ended.py` | Rewrite or update to use fake-driven pattern |

## What Stays the Same

**`update_dispatch_info.py`:**
- Click command signature (issue_number argument)
- Result dataclasses
- JSON output format
- Exit code 1 on error

**`mark_impl_started.py` and `mark_impl_ended.py`:**
- Plan reference read from `.impl/plan-ref.json`
- Local state write to `.impl/local-run-state.json`
- Environment detection (`in_github_actions()`)
- Metadata capture (timestamp, user, session_id)
- Result dataclasses
- JSON output format
- Exit code 0 always (graceful degradation)
- Session ID parameter

## Files NOT Changing

- `src/erk/cli/commands/exec/scripts/impl_signal.py` - Already migrated in step 3.1
- `src/erk/cli/commands/exec/scripts/upload_session.py` - Migrated in step 3.2
- `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` - Migrated in step 3.2
- `packages/erk-shared/src/erk_shared/plan_store/backend.py` - ABC already has `update_metadata()` method
- `packages/erk-shared/src/erk_shared/plan_store/github.py` - Implementation already exists
- `packages/erk-shared/src/erk_shared/gateway/github/metadata/plan_header.py` - Still used by `GitHubPlanBackend` internally

## Verification

1. **Run unit tests:**
   ```bash
   pytest tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py -v
   pytest tests/unit/cli/commands/exec/scripts/test_mark_impl_started.py -v
   pytest tests/unit/cli/commands/exec/scripts/test_mark_impl_ended.py -v
   ```

2. **Run type checker on changed files:**
   ```bash
   mypy src/erk/cli/commands/exec/scripts/update_dispatch_info.py
   mypy src/erk/cli/commands/exec/scripts/mark_impl_started.py
   mypy src/erk/cli/commands/exec/scripts/mark_impl_ended.py
   ```

3. **Run linter on changed files:**
   ```bash
   ruff check src/erk/cli/commands/exec/scripts/
   ```

4. **Verify no remaining `plan_header` imports in exec scripts:**
   ```bash
   grep -r "from erk_shared.gateway.github.metadata.plan_header import" src/erk/cli/commands/exec/scripts/
   # Should only show imports in scripts NOT yet migrated (steps 3.4+)
   ```

5. **Integration smoke test:**
   - Test `update_dispatch_info` manually with a real issue
   - Test `mark_impl_started` and `mark_impl_ended` in a real `.impl/` directory

## Implementation Order

1. Migrate `update_dispatch_info.py` (simplest - takes issue_number as argument)
2. Update tests for `update_dispatch_info.py`
3. Migrate `mark_impl_started.py` (reads plan-ref, writes local state)
4. Update/rewrite tests for `mark_impl_started.py`
5. Migrate `mark_impl_ended.py` (nearly identical to started)
6. Update/rewrite tests for `mark_impl_ended.py`
7. Run verification steps

## Success Criteria

- All three scripts use `PlanBackend.update_metadata()` instead of direct `GitHubIssues` calls
- No imports from `erk_shared.gateway.github.metadata.plan_header` in the three migrated scripts
- All tests pass with fake-driven pattern (no `monkeypatch` or `unittest.mock`)
- Type checker passes
- Linter passes
- Existing slash commands and workflows that call these scripts continue to work