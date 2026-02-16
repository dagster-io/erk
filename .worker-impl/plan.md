# Migrate Steps 3.6 and 3.7 to PlanBackend

Part of Objective #7161, Steps 3.6 and 3.7

## Context

Objective #7161 consolidates plan operations behind the `PlanBackend` abstraction. Steps 3.1-3.5 are complete. Steps 3.6 and 3.7 migrate the remaining Phase 3 exec scripts that still bypass `PlanBackend` to read/write plan-header metadata directly via `GitHubIssues` and `plan_header.py` helpers.

## Scope

Four files to migrate:

| File | Step | Migration Scope |
|------|------|----------------|
| `plan_create_review_pr.py` | 3.6 | Replace `issue_exists` + `get_issue` + `update_plan_header_review_pr` + `update_issue_body` with `backend.get_plan()` LBYL + `backend.update_metadata({"review_pr": pr_number})` |
| `plan_review_complete.py` | 3.6 | Replace `issue_exists` + `get_issue` + `extract_plan_header_review_pr` + `clear_plan_header_review_pr` + `update_issue_body` with `backend.get_metadata_field()` + `backend.update_metadata({"review_pr": None, "last_review_pr": old_value})` |
| `handle_no_changes.py` | 3.7 | Replace `github.issues.add_comment()` with `backend.add_comment()` (minimal - only 1 plan-issue operation; PR operations stay on `GitHub` gateway) |
| `get_plan_metadata.py` | 3.7 | Replace `get_issue` + `find_metadata_block` + `block.data.get()` with `backend.get_metadata_field()` |

## Implementation

### Phase 1: Migrate `plan_create_review_pr.py`

**File:** `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py`

Changes:
1. Replace import of `GitHubIssues`, `IssueNotFound`, `find_metadata_block`, `update_plan_header_review_pr`, `BodyText` with `require_plan_backend`, `PlanBackend`, `PlanNotFound`, `PlanHeaderNotFoundError`
2. Keep `GitHub` import (needed for PR creation, label, branch check)
3. In `_create_review_pr_impl`: replace `github_issues` param with `backend: PlanBackend`
   - Replace `issue_exists` + `get_issue` LBYL with `backend.get_plan(repo_root, str(issue_number))` + `isinstance(result, PlanNotFound)` check
   - Remove `find_metadata_block` validation — `backend.update_metadata` raises `PlanHeaderNotFoundError` if missing
   - Replace `update_plan_header_review_pr(issue.body, pr_number)` + `update_issue_body` with `backend.update_metadata(repo_root, str(issue_number), {"review_pr": pr_number})`
   - Catch `PlanHeaderNotFoundError` and convert to `CreateReviewPRException(error="invalid_issue")`
4. In click command: replace `github.issues` with `require_plan_backend(ctx)`
5. Update tests to pass `github_issues=fake_gh_issues` into `ErkContext.for_test()` (the real `GitHubPlanStore` wraps the fake — "real backend + fake gateway" pattern)

**Test file:** `tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py`
- Update `ErkContext.for_test()` calls to include `github_issues=fake_gh_issues` (so PlanBackend is auto-created)
- Metadata assertion: instead of checking `updated_issue.body` for `"review_pr: 999"`, assert via `fake_gh_issues.updated_bodies` that the body was updated with the correct metadata

### Phase 2: Migrate `plan_review_complete.py`

**File:** `src/erk/cli/commands/exec/scripts/plan_review_complete.py`

Changes:
1. Replace imports: drop `GitHubIssues`, `IssueNotFound`, `find_metadata_block`, `extract_plan_header_review_pr`, `clear_plan_header_review_pr`, `BodyText`; add `require_plan_backend`, `PlanBackend`, `PlanNotFound`, `PlanHeaderNotFoundError`
2. Keep `GitHub` import (needed for PR operations: close_pr, delete_remote_branch, get_pr)
3. In `_plan_review_complete_impl`: replace `github_issues` param with `backend: PlanBackend`
   - Replace `issue_exists` + `get_issue` with `backend.get_plan()` LBYL
   - Replace `find_metadata_block` check — `get_metadata_field` handles missing blocks (returns `None`)
   - Replace `extract_plan_header_review_pr(issue.body)` with `backend.get_metadata_field(repo_root, plan_id, "review_pr")` + `isinstance(result, PlanNotFound)` check
   - Replace `clear_plan_header_review_pr(issue.body)` + `update_issue_body` with `backend.update_metadata(repo_root, plan_id, {"review_pr": None, "last_review_pr": review_pr})`
   - Catch `PlanHeaderNotFoundError` and convert to `PlanReviewCompleteException(error="no_plan_header")`
4. In click command: replace `github.issues` with `require_plan_backend(ctx)`
5. Update tests: add `github_issues=fake_gh_issues` to `ErkContext.for_test()` calls

**Test file:** `tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py`
- Update `ErkContext.for_test()` to include `github_issues=fake_gh_issues`
- `test_plan_review_complete_clears_review_pr_metadata`: adjust assertion to check via `fake_gh_issues.updated_bodies` (metadata block now rendered by `GitHubPlanStore.update_metadata()`)
- `test_plan_review_complete_sets_last_review_pr`: similarly adjust assertion

### Phase 3: Migrate `get_plan_metadata.py`

**File:** `src/erk/cli/commands/exec/scripts/get_plan_metadata.py`

Changes:
1. Replace imports: drop `require_issues`, `IssueNotFound`, `find_metadata_block`; add `require_plan_backend`, `PlanNotFound`
2. Replace entire implementation:
   - `backend = require_plan_backend(ctx)`
   - `result = backend.get_metadata_field(repo_root, str(issue_number), field_name)`
   - `if isinstance(result, PlanNotFound):` → error exit
   - `value = result` (may be `None` for missing field or missing block, which is correct)
3. Output format stays identical (JSON with success, value, issue_number, field)

**Test file:** `tests/unit/cli/commands/exec/scripts/test_get_plan_metadata.py`
- Update `ErkContext.for_test(github_issues=fake_gh)` → stays the same since it already uses `github_issues` param name (this will automatically create a `GitHubPlanStore` backed by the fake)

### Phase 4: Migrate `handle_no_changes.py`

**File:** `src/erk/cli/commands/exec/scripts/handle_no_changes.py`

Minimal change — only the issue comment (line 242) uses `GitHubIssues` directly.

Changes:
1. Add import: `require_plan_backend`
2. In click command: add `backend = require_plan_backend(ctx)`
3. Replace `github.issues.add_comment(repo_root, issue_number, comment)` with `backend.add_comment(repo_root, str(issue_number), comment)`
4. All PR operations (`update_pr_title_and_body`, `ensure_label_exists`, `add_label_to_pr`, `mark_pr_ready`) stay on `GitHub` gateway (these are PR operations, not plan-issue operations)

**Test file:** `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py`
- Update `ErkContext.for_test()` to include `github_issues=...` extracted from `FakeGitHub` (to enable `PlanBackend` auto-creation)
- Update `test_cli_adds_comment_to_issue` assertion: change `github.issues.added_comments` to check via the fake issues gateway directly (pattern unchanged, just routing through backend)

## Key Patterns to Follow

- **LBYL with PlanBackend:** `result = backend.get_plan(...)` then `isinstance(result, PlanNotFound)` — never try/except for control flow
- **Real backend + fake gateway testing:** `ErkContext.for_test(github_issues=fake_gh_issues)` auto-creates `GitHubPlanStore(fake_gh_issues)`
- **Metadata updates via dict:** `backend.update_metadata(repo_root, plan_id, {"review_pr": pr_number})` — the backend handles metadata block parsing/rendering
- **Reference implementation:** `plan_update_issue.py` (PR #7190) shows the exact pattern

## Files Modified

**Source (4):**
- `src/erk/cli/commands/exec/scripts/plan_create_review_pr.py`
- `src/erk/cli/commands/exec/scripts/plan_review_complete.py`
- `src/erk/cli/commands/exec/scripts/get_plan_metadata.py`
- `src/erk/cli/commands/exec/scripts/handle_no_changes.py`

**Tests (4):**
- `tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py`
- `tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py`
- `tests/unit/cli/commands/exec/scripts/test_get_plan_metadata.py`
- `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py`

## Verification

1. Run scoped unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py tests/unit/cli/commands/exec/scripts/test_plan_review_complete.py tests/unit/cli/commands/exec/scripts/test_get_plan_metadata.py tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py`
2. Run type checker: `ty check` on modified files
3. Run linter: `ruff check` on modified files
4. Verify no remaining direct `GitHubIssues` usage in the four migrated scripts (except where `GitHub` gateway is needed for PR operations in `plan_create_review_pr.py`, `plan_review_complete.py`, and `handle_no_changes.py`)