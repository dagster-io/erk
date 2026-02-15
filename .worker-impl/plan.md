# Plan: Migrate update_dispatch_info.py, mark_impl_started.py, mark_impl_ended.py to PlanBackend

**Part of Objective #6864, Step 3.3**

## Context

This plan migrates three exec scripts that currently bypass `PlanBackend` by calling `GitHubIssues` gateway and `plan_header` functions directly:

1. **`update_dispatch_info.py`** - Updates dispatch info (run_id, node_id, dispatched_at) in plan-header metadata
2. **`mark_impl_started.py`** - Signals implementation started by updating local/remote impl event metadata
3. **`mark_impl_ended.py`** - Signals implementation ended by updating local/remote impl event metadata

All three scripts follow the same bypass pattern:
- Fetch issue via `GitHubIssues.get_issue()`
- Call `plan_header` functions to update metadata (e.g., `update_plan_header_dispatch()`, `update_plan_header_local_impl_event()`)
- Update issue body via `GitHubIssues.update_issue_body()`

The `PlanBackend.update_metadata()` method already exists and handles exactly this pattern: structured metadata field updates without fetching/parsing the entire issue body. This migration consolidates these three scripts behind the abstraction.

This follows the same pattern as step 3.1 (PR #7005), which migrated `impl_signal.py` from `GitHubIssues` + `plan_header` to `PlanBackend`.

## Changes

### 1. Migrate `update_dispatch_info.py`

**File:** `src/erk/cli/commands/exec/scripts/update_dispatch_info.py`

**Current pattern:**
```python
# Fetch issue
issue = github_issues.get_issue(repo_root, issue_number)
# Update metadata block
updated_body = update_plan_header_dispatch(issue.body, run_id, node_id, dispatched_at)
# Write back
github_issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
```

**New pattern:**
```python
# Update metadata directly
backend.update_metadata(
    repo_root,
    str(issue_number),
    metadata={
        "last_dispatched_run_id": run_id,
        "last_dispatched_node_id": node_id,
        "last_dispatched_at": dispatched_at,
    },
)
```

**Changes:**
- Replace `require_issues(ctx)` with `require_plan_backend(ctx)`
- Remove `github_issues.get_issue()` call (not needed - PlanBackend handles fetch internally)
- Replace `update_plan_header_dispatch()` + `update_issue_body()` with single `backend.update_metadata()` call
- Remove try/except around `update_plan_header_dispatch()` (PlanBackend raises RuntimeError on failure)
- Keep RuntimeError handling around `update_metadata()` call
- Remove imports: `update_plan_header_dispatch`, `IssueNotFound`, `BodyText`, `require_issues`
- Add import: `require_plan_backend` from `erk_shared.context.helpers`

**Error handling:**
- `IssueNotFound` check becomes unnecessary (PlanBackend raises RuntimeError if plan doesn't exist)
- `ValueError` from `update_plan_header_dispatch()` becomes unnecessary (PlanBackend validates internally)
- Keep `RuntimeError` handling for GitHub API failures

### 2. Migrate `mark_impl_started.py`

**File:** `src/erk/cli/commands/exec/scripts/mark_impl_started.py`

**Current pattern:**
```python
# Fetch issue
issue = github_issues.get_issue(repo_root, int(plan_ref.plan_id))
# Update metadata based on environment
if in_github_actions():
    updated_body = update_plan_header_remote_impl(issue.body, timestamp)
else:
    updated_body = update_plan_header_local_impl_event(issue.body, timestamp, "started", session_id, user)
# Write back
github_issues.update_issue_body(repo_root, int(plan_ref.plan_id), BodyText(content=updated_body))
```

**New pattern:**
```python
# Build metadata dict based on environment
metadata: dict[str, object] = {}
if in_github_actions():
    metadata["last_remote_impl_at"] = timestamp
else:
    metadata["last_local_impl_at"] = timestamp
    metadata["last_local_impl_event"] = "started"
    metadata["last_local_impl_session"] = session_id
    metadata["last_local_impl_user"] = user

# Update metadata directly
backend.update_metadata(repo_root, plan_ref.plan_id, metadata=metadata)
```

**Changes:**
- Replace `require_github_issues(ctx)` with `require_plan_backend(ctx)`
- Remove `github_issues.get_issue()` call
- Build metadata dict with conditional environment-specific fields
- Replace `update_plan_header_remote_impl()` / `update_plan_header_local_impl_event()` + `update_issue_body()` with single `backend.update_metadata()` call
- Remove imports: `update_plan_header_local_impl_event`, `update_plan_header_remote_impl`, `IssueNotFound`, `BodyText`, `require_issues`
- Add import: `require_plan_backend` from `erk_shared.context.helpers`
- Keep `write_local_run_state()` call (local file operation, unchanged)

**Error handling:**
- `IssueNotFound` check becomes unnecessary (PlanBackend raises RuntimeError)
- `ValueError` from plan_header functions becomes unnecessary (PlanBackend validates)
- Keep `RuntimeError` handling for GitHub API failures
- Preserve graceful degradation (exit code 0 on all errors)

### 3. Migrate `mark_impl_ended.py`

**File:** `src/erk/cli/commands/exec/scripts/mark_impl_ended.py`

**Same changes as `mark_impl_started.py`**, except:
- Metadata dict uses `event="ended"` instead of `event="started"`
- Otherwise identical pattern

### 4. Add Integration Tests

**New file:** `tests/integration/cli/commands/exec/scripts/test_update_dispatch_info_integration.py`

Test `update_dispatch_info` with real `GitHubPlanStore` + `FakeGitHubIssues`:

```python
def test_update_dispatch_info_updates_metadata(tmp_path: Path) -> None:
    """update-dispatch-info updates plan-header metadata via PlanBackend."""
    # Setup: create fake issue with plan-header metadata
    fake_issues = FakeGitHubIssues(issues={42: IssueInfo(...)})
    backend = GitHubPlanStore(fake_issues)
    ctx = ErkContext.for_test(cwd=tmp_path, plan_backend=backend)

    # Execute
    result = runner.invoke(
        update_dispatch_info,
        ["42", "run-123", "node-456", "2026-02-15T10:00:00Z"],
        obj=ctx,
    )

    # Verify
    assert result.exit_code == 0
    # Assert fake_issues.updated_issues[42] contains new metadata values
```

**New file:** `tests/integration/cli/commands/exec/scripts/test_mark_impl_integration.py`

Test `mark_impl_started` and `mark_impl_ended` with real backend + fake gateway:

```python
def test_mark_impl_started_local_updates_metadata(tmp_path: Path) -> None:
    """mark-impl-started updates local impl metadata via PlanBackend."""
    # Setup .impl/plan-ref.json
    # Setup fake issue with plan-header
    # Execute with session_id
    # Verify metadata updated
    # Verify .impl/local-run-state.json written

def test_mark_impl_started_remote_updates_metadata(tmp_path: Path, monkeypatch) -> None:
    """mark-impl-started in GitHub Actions updates remote impl metadata."""
    # monkeypatch GITHUB_ACTIONS env var
    # Execute
    # Verify last_remote_impl_at updated (not local fields)
```

### 5. Update Existing Unit Tests (Optional)

**Files:** `tests/unit/cli/commands/exec/scripts/test_update_dispatch_info.py`, `test_mark_impl_started.py`, `test_mark_impl_ended.py`

These files don't exist yet. If they do exist, update them to use `ErkContext.for_test(plan_backend=fake_backend)` instead of mocking `GitHubIssues`.

If they don't exist, the integration tests above provide sufficient coverage.

## Files to Create

| File | Purpose |
|------|---------|
| `tests/integration/cli/commands/exec/scripts/test_update_dispatch_info_integration.py` | Integration test with real backend + fake gateway |
| `tests/integration/cli/commands/exec/scripts/test_mark_impl_integration.py` | Integration tests for started/ended with real backend |

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/update_dispatch_info.py` | Replace `GitHubIssues` + `plan_header` with `PlanBackend.update_metadata()` |
| `src/erk/cli/commands/exec/scripts/mark_impl_started.py` | Replace `GitHubIssues` + `plan_header` with `PlanBackend.update_metadata()` |
| `src/erk/cli/commands/exec/scripts/mark_impl_ended.py` | Replace `GitHubIssues` + `plan_header` with `PlanBackend.update_metadata()` |

## Files NOT Changing

- `.impl/` folder structure (plan-ref.json, local-run-state.json)
- `erk_shared.impl_folder` module (read_plan_ref, write_local_run_state)
- `erk_shared.env.in_github_actions()` detection
- Click command interfaces (arguments, options)
- JSON output format (success/error dataclasses)
- Graceful degradation behavior (exit code 0 on errors for mark_impl scripts)
- Exit code 1 on errors for update_dispatch_info

## Implementation Details

### PlanBackend Context Helper

The `require_plan_backend(ctx)` helper (from `erk_shared.context.helpers`) retrieves the `PlanBackend` from Click context. It's analogous to `require_github_issues(ctx)`.

### Metadata Field Naming

The metadata field names passed to `PlanBackend.update_metadata()` match the YAML keys in the plan-header metadata block:

- `last_dispatched_run_id`, `last_dispatched_node_id`, `last_dispatched_at`
- `last_local_impl_at`, `last_local_impl_event`, `last_local_impl_session`, `last_local_impl_user`
- `last_remote_impl_at`

These are defined in `erk_shared.gateway.github.metadata.schemas.PlanHeaderSchema`.

### Error Handling Pattern

All three scripts catch `RuntimeError` from PlanBackend methods and convert to error response JSON. The scripts differ in exit codes:

- `update_dispatch_info`: exits 1 on error (normal failure)
- `mark_impl_started`, `mark_impl_ended`: exit 0 on error (graceful degradation for `|| true` pattern)

### Integration Test Pattern

The integration tests use the **real backend + fake gateway** pattern (per backend testing conventions):

```python
# Correct: real backend with fake gateway
fake_issues = FakeGitHubIssues(issues={...})
backend = GitHubPlanStore(fake_issues)
ctx = ErkContext.for_test(cwd=tmp_path, plan_backend=backend)
```

Do NOT use `FakeLinearPlanBackend` for testing exec scripts. Fake backends exist only to validate the ABC contract across multiple providers, not for testing callers.

### Type Conversion

`update_dispatch_info` receives `issue_number: int` as argument, but `PlanBackend.update_metadata()` expects `plan_id: str`. Convert with `str(issue_number)`.

`mark_impl_started` and `mark_impl_ended` read `plan_id` from `PlanRef`, which is already a string. Use `plan_ref.plan_id` directly.

## Verification Steps

1. **Type check:** `ty src/erk/cli/commands/exec/scripts/update_dispatch_info.py`
2. **Type check:** `ty src/erk/cli/commands/exec/scripts/mark_impl_started.py`
3. **Type check:** `ty src/erk/cli/commands/exec/scripts/mark_impl_ended.py`
4. **Lint:** `ruff check src/erk/cli/commands/exec/scripts/{update_dispatch_info,mark_impl_started,mark_impl_ended}.py`
5. **Integration tests:** `pytest tests/integration/cli/commands/exec/scripts/test_update_dispatch_info_integration.py`
6. **Integration tests:** `pytest tests/integration/cli/commands/exec/scripts/test_mark_impl_integration.py`
7. **Grep verification:** `grep -r "update_plan_header_dispatch\|update_plan_header_local_impl_event\|update_plan_header_remote_impl" src/` should show zero matches after migration

## Success Criteria

- [ ] All three scripts use `PlanBackend.update_metadata()` instead of direct `plan_header` functions
- [ ] No imports of `update_plan_header_dispatch`, `update_plan_header_local_impl_event`, `update_plan_header_remote_impl` in the three scripts
- [ ] Integration tests pass with real `GitHubPlanStore` + fake `GitHubIssues`
- [ ] Type checker passes on all three scripts
- [ ] Linter passes on all three scripts
- [ ] Manual test: run `update_dispatch_info` in real repo (creates actual GitHub API call)
- [ ] Manual test: run `mark_impl_started` in `.impl/` folder with real plan
- [ ] Manual test: run `mark_impl_ended` in `.impl/` folder with real plan

## Related Work

- **Step 3.1 (PR #7005):** Migrated `impl_signal.py` using the same pattern (replaced `GitHubIssues` + `plan_header` with `PlanBackend`)
- **Step 3.2 (Issue #7033):** Migrates session-related scripts (`upload_session.py`, `update_plan_remote_session.py`)
- **Phase 1 (PR #6871):** Added `update_metadata()` method to `PlanBackend` ABC
- **Phase 2 (PR #6984):** Introduced `PlanRef` dataclass to replace raw `int issue_number`