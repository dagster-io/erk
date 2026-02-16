# Plan: Migrate plan_update_issue.py and plan_update_from_feedback.py to PlanBackend

Part of Objective #7161, Step 3.5

## Context

Objective #7161 consolidates plan operations behind the `PlanBackend` abstraction. Steps 3.1-3.4 migrated other exec scripts. Step 3.5 migrates the two remaining "plan content update" scripts from direct `GitHubIssues` gateway calls to `PlanBackend`.

Both scripts currently use `require_github_issues(ctx)` to get a `GitHubIssues` gateway and manually handle comment lookups and updates. `PlanBackend.update_plan_content()` encapsulates all of this logic (finding the plan comment via `plan_comment_id` metadata or first-comment fallback, formatting, and updating).

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_update_issue.py` | Migrate to PlanBackend |
| `src/erk/cli/commands/exec/scripts/plan_update_from_feedback.py` | Migrate to PlanBackend |
| `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py` | Update assertions for simplified output |
| `tests/unit/cli/commands/exec/scripts/test_plan_update_from_feedback.py` | Update assertions for simplified output |

## Phase 1: Migrate plan_update_from_feedback.py

This is the simpler migration — the entire script becomes `get_plan()` + label check + `update_plan_content()`.

### Changes

**Imports:**
- Remove: `require_issues as require_github_issues`, `GitHubIssues`, `IssueNotFound`, `extract_plan_header_comment_id`, `format_plan_content_comment`
- Add: `require_plan_backend`
- Add: `PlanNotFound` from `erk_shared.plan_store.types`

**`_update_plan_from_feedback_impl()`:**
- Change parameter from `github_issues: GitHubIssues` to `backend: PlanBackend`
- Replace `issue_exists()` + `get_issue()` with `backend.get_plan()` + `isinstance(result, PlanNotFound)` check
- Replace label check: use `plan.labels` instead of `issue.labels`
- Replace manual plan_comment_id extraction + comment lookup + update with `backend.update_plan_content()`
- Remove `comment_id` and `comment_url` from `PlanUpdateFromFeedbackSuccess` — these are internal details that `update_plan_content()` handles internally
- Error codes that change:
  - `no_plan_comment_id` and `comment_not_found` merge into `update_failed` (RuntimeError from `update_plan_content()`)
  - `issue_not_found` stays the same (via `PlanNotFound` check)
  - `missing_erk_plan_label` stays the same (via `plan.labels` check)

**CLI handler:**
- Replace `require_github_issues(ctx)` with `require_plan_backend(ctx)`
- Pass `backend` to `_update_plan_from_feedback_impl()`

**Test updates:**
- Remove assertions on `comment_id` and `comment_url` from success responses
- Remove `test_error_no_plan_comment_id` and `test_error_comment_not_found` — these error codes no longer exist (PlanBackend handles internally)
- Keep `test_error_issue_not_found`, `test_error_missing_erk_plan_label`, input validation tests

## Phase 2: Migrate plan_update_issue.py

This script does two things: (1) update plan content, (2) update issue title. Only (1) can migrate to PlanBackend — title update stays on `GitHubIssues`.

### Changes

**Imports:**
- Keep: `require_issues as require_github_issues` (still needed for title update)
- Add: `require_plan_backend`
- Add: `PlanNotFound` from `erk_shared.plan_store.types`
- Remove: `IssueInfo`, `IssueNotFound` (no longer needed directly)
- Remove: `format_plan_content_comment` (handled by `update_plan_content()`)

**Script body:**
- Add `backend = require_plan_backend(ctx)` alongside existing `github = require_github_issues(ctx)`
- Replace LBYL check: `backend.get_plan()` + `isinstance(result, PlanNotFound)` instead of `github.get_issue()` + `isinstance(issue, IssueNotFound)`
- Replace comment lookup + update (steps 3-4) with `backend.update_plan_content(repo_root, str(issue_number), plan_content.strip())`
- Title update stays: `github.update_issue_title()` (PlanBackend has no title update method)
- Get labels from `plan.labels` and URL from `plan.url` instead of `IssueInfo`
- Remove `comment_id` and `comment_url` from success output (no longer available)
- Remove the "no comments" error case — `update_plan_content()` handles the comment lookup internally and raises RuntimeError if no comment found

**Test updates:**
- Remove assertions on `comment_id` and `comment_url`
- Remove `test_plan_update_issue_no_comments` — this error is now internal to PlanBackend
- Remove `test_plan_update_issue_updates_first_comment_only` — comment selection is PlanBackend's responsibility
- Keep all title-related tests (these still exercise `github.update_issue_title()`)
- Keep plan-not-found and no-plan-found tests

## Design Decisions

1. **Dual dependency for plan_update_issue.py**: Uses both `require_plan_backend` and `require_github_issues`. Title update has no PlanBackend equivalent. This is an acknowledged gap for future consolidation (could add `update_title()` to PlanBackend in a later step).

2. **Removed output fields**: `comment_id` and `comment_url` are dropped from both scripts' outputs. These are internal implementation details of how GitHub stores plan content. No callers depend on them — `one-shot-plan.md` only checks `success` and `issue_number`.

3. **Merged error codes in plan_update_from_feedback**: `no_plan_comment_id` and `comment_not_found` merge into `update_failed`. These granular error codes reflected GitHub-specific implementation details (plan_comment_id metadata field). PlanBackend abstracts this away.

## Verification

1. Run unit tests for both migrated scripts:
   ```
   pytest tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py
   pytest tests/unit/cli/commands/exec/scripts/test_plan_update_from_feedback.py
   ```
2. Run ty type checking
3. Run ruff linting