# Plan: Migrate upload_session.py and update_plan_remote_session.py to PlanBackend

**Part of Objective #6864, Step 3.2**

## Context

Objective #6864 consolidates direct GitHub issue operations behind the `PlanBackend` abstraction. Steps 1.1-2.5 established the PlanBackend interface and PlanRef types. Step 3.1 (PR #7005) migrated `impl_signal.py` as the first exec script, establishing the pattern. This plan migrates the next two exec scripts: `upload_session.py` and `update_plan_remote_session.py`.

Both scripts currently bypass PlanBackend by directly calling `require_issues(ctx)` to get/update issues and using low-level `plan_header.py` functions to manipulate metadata. The migration replaces these with `require_plan_backend(ctx)` and `backend.update_metadata()`.

## Files to Modify

1. `src/erk/cli/commands/exec/scripts/upload_session.py` — migrate plan header update to PlanBackend
2. `src/erk/cli/commands/exec/scripts/update_plan_remote_session.py` — migrate plan header update to PlanBackend
3. `tests/unit/cli/commands/exec/scripts/test_update_plan_remote_session.py` — update assertions for PlanBackend pattern
4. `tests/unit/cli/commands/exec/scripts/test_upload_session.py` — **new file**: create tests (none exist today)

## Reference Files (read-only)

- `src/erk/cli/commands/exec/scripts/impl_signal.py` — migration pattern exemplar (PR #7005)
- `packages/erk-shared/src/erk_shared/plan_store/backend.py` — PlanBackend ABC interface
- `packages/erk-shared/src/erk_shared/context/helpers.py:397` — `require_plan_backend()` helper
- `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` — test pattern exemplar

## Implementation

### 1. Migrate `update_plan_remote_session.py`

**Current bypass pattern (lines 111-136):**
```python
github_issues = require_issues(ctx)
issue = github_issues.get_issue(repo_root, issue_number)
updated_body = update_plan_header_remote_impl_event(issue_body=issue.body, ...)
github_issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
```

**Replace with:**
```python
backend = require_plan_backend(ctx)
plan_id = str(issue_number)
metadata: dict[str, object] = {
    "last_remote_impl_at": timestamp,
    "last_remote_impl_run_id": run_id,
    "last_remote_impl_session_id": session_id,
}
backend.update_metadata(repo_root, plan_id, metadata)
```

**Import changes:**
- Remove: `require_issues` from context helpers import, `IssueNotFound`, `update_plan_header_remote_impl_event`, `BodyText`
- Add: `require_plan_backend` to context helpers import

**Error handling changes:**
- `IssueNotFound` check (line 115) → `RuntimeError` catch (PlanBackend raises RuntimeError for not-found)
- `ValueError` for missing plan-header (line 130) → absorbed by PlanBackend's `update_metadata` (it handles the header manipulation internally)
- `RuntimeError` for API failure (line 137) → same, caught as RuntimeError
- All three error paths collapse into a single `RuntimeError` catch with appropriate error_type mapping

### 2. Migrate `upload_session.py`

The gist creation part (lines 86-118) remains unchanged — it uses `require_github(ctx)` for `github.create_gist()`, which is unrelated to PlanBackend.

**Current bypass pattern (lines 121-153):**
```python
issues = require_issues(ctx)
issue_info = issues.get_issue(repo_root, issue_number)
updated_body = update_plan_header_session_gist(issue_body=issue_info.body, ...)
issues.update_issue_body(repo_root, issue_number, BodyText(content=updated_body))
```

**Replace with:**
```python
backend = require_plan_backend(ctx)
plan_id = str(issue_number)
metadata: dict[str, object] = {
    "last_session_gist_url": gist_result.gist_url,
    "last_session_gist_id": gist_result.gist_id,
    "last_session_id": session_id,
    "last_session_at": timestamp,
    "last_session_source": source,
}
backend.update_metadata(repo_root, plan_id, metadata)
```

**Import changes:**
- Remove: `require_issues` from context helpers import, `IssueNotFound`, `BodyText`
- Remove: inline import of `update_plan_header_session_gist` (line 125)
- Add: `require_plan_backend` to context helpers import

**Error handling:** The partial success pattern (gist created but issue update failed) is preserved — catch `RuntimeError` from `backend.update_metadata()` and set `issue_updated = False`.

### 3. Update `test_update_plan_remote_session.py`

The existing tests already use `ErkContext.for_test(github_issues=fake_gh, cwd=tmp_path)`, which auto-wires the GitHubPlanStore backend with the fake. Assertions currently verify `fake_gh.updated_bodies` and parse the plan-header block — this still works because the real GitHubPlanStore flows through FakeGitHubIssues.

**Changes needed:**
- `test_missing_plan_header` error path may change since PlanBackend handles header manipulation differently — verify the error behavior and adjust expected `error_type` if needed
- The `issue-not-found` error type may need adjustment since PlanBackend raises RuntimeError instead of returning IssueNotFound

### 4. Create `test_upload_session.py`

No tests exist for `upload_session.py`. Create tests following the pattern in `test_update_plan_remote_session.py` and `test_impl_signal.py`:

- `test_upload_session_gist_only` — no `--issue-number`, verify gist creation succeeds
- `test_upload_session_with_issue_update` — with `--issue-number`, verify gist + metadata update
- `test_upload_session_issue_not_found` — issue doesn't exist, verify partial success (gist created, issue update failed)
- `test_upload_session_gist_failure` — gist creation fails, verify error output

Tests use `ErkContext.for_test(github_issues=fake_gh, github=fake_github, cwd=tmp_path)` and write a temporary session file. Need to check if `FakeGitHub` supports `create_gist()`.

## Verification

1. Run targeted tests: `uv run pytest tests/unit/cli/commands/exec/scripts/test_update_plan_remote_session.py tests/unit/cli/commands/exec/scripts/test_upload_session.py -v`
2. Run full exec script tests: `uv run pytest tests/unit/cli/commands/exec/scripts/ -v`
3. Run type checker: `uv run ty check src/erk/cli/commands/exec/scripts/upload_session.py src/erk/cli/commands/exec/scripts/update_plan_remote_session.py`
4. Run lint: `uv run ruff check src/erk/cli/commands/exec/scripts/upload_session.py src/erk/cli/commands/exec/scripts/update_plan_remote_session.py`