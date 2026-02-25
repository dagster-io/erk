# Plan: Delete GitHubPlanStore and PlanStore ABC (Objective #7911, Node 3.1)

## Context

Objective #7911 ("Delete Issue-Based Plan Backend") has completed Phases 1-2: removing production code paths and migrating test infrastructure. Node 3.1 is the first node in Phase 3 (deletion phase). The goal is to collapse the two-level `PlanStore → PlanBackend` ABC hierarchy into a single `PlanBackend` ABC, delete the issue-based `GitHubPlanStore` implementation, and migrate all test files to use `PlannedPRBackend`.

**Current class hierarchy:**
```
PlanStore (ABC, store.py)           ← DELETE
  └── PlanBackend (ABC, backend.py) ← becomes standalone ABC
        ├── GitHubPlanStore (github.py) ← DELETE
        └── PlannedPRBackend (planned_pr.py) ← KEEP (sole implementation)
```

## Phase 1: Inline PlanStore into PlanBackend

Make `PlanBackend` a standalone ABC by inlining PlanStore's only non-redeclared method.

**File: `packages/erk-shared/src/erk_shared/plan_store/backend.py`**
1. Add `ABC` to imports: `from abc import ABC, abstractmethod`
2. Change `class PlanBackend(PlanStore):` → `class PlanBackend(ABC):`
3. Remove `from erk_shared.plan_store.store import PlanStore`
4. Replace the comment `# close_plan is inherited from PlanStore` (line 354) with the actual `close_plan` abstract method (copied from store.py lines 62-73)
5. Update docstrings to remove PlanStore references

**Verification:** ty check on backend.py, planned_pr.py

## Phase 2: Update Type Annotations (PlanStore → PlanBackend)

**File: `packages/erk-shared/src/erk_shared/context/context.py`**
- Remove `from erk_shared.plan_store.store import PlanStore` (line 53)
- Change field `plan_store: PlanStore` (line 86) → `plan_store: PlanBackend`
- Change param `plan_store: PlanStore | None` (line 212) → `plan_store: PlanBackend | None`
- Simplify `plan_backend` property (lines 159-173): remove isinstance check, just `return self.plan_store`

**File: `packages/erk-shared/src/erk_shared/context/testing.py`**
- Remove `from erk_shared.plan_store.store import PlanStore` (line 38)
- Change param `plan_store: PlanStore | None` (line 53) → `plan_store: PlanBackend | None`
- Add `from erk_shared.plan_store.backend import PlanBackend` import
- Change `resolved_plan_store: PlanStore` (line 176) → `resolved_plan_store: PlanBackend`

**File: `src/erk/core/context.py`**
- Remove `from erk_shared.plan_store.store import PlanStore` (line 82)
- Add `from erk_shared.plan_store.backend import PlanBackend` if not present
- Change param `plan_store: PlanStore | None` → `plan_store: PlanBackend | None`
- Remove the `issues_explicitly_passed` auto-GitHubPlanStore branch (lines 299-309): always default to `PlannedPRBackend`

**Verification:** ty check on all modified files

## Phase 3: Migrate Test Files from GitHubPlanStore to PlannedPRBackend

~32 test files import `GitHubPlanStore`. Each constructs `GitHubPlanStore(issues)` or `GitHubPlanStore(issues, time)` and passes it as `plan_store=`. Migration pattern for each:

**Pattern:** Replace `plan_store=GitHubPlanStore(fake_issues, FakeTime())` with `plan_store=PlannedPRBackend(fake_github, fake_issues, time=FakeTime())`. This requires ensuring each test has a `FakeGitHub` instance available. Where tests seed issue bodies with plan-header metadata, move that content to `PRDetails` bodies seeded in `FakeGitHub(pr_details={...})`.

**Key behavioral differences to handle:**
- `GitHubPlanStore.get_plan()` reads from issues → `PlannedPRBackend.get_plan()` reads from PRs
- `GitHubPlanStore.close_plan()` calls `issues.close_issue()` → `PlannedPRBackend.close_plan()` calls `github.close_pr()`
- `GitHubPlanStore.add_comment()` calls `issues.add_comment()` → `PlannedPRBackend.add_comment()` calls `github.create_pr_comment()`
- Plan body in issues was in comment (Schema V2) or issue body → in PRs it's after `PLAN_CONTENT_SEPARATOR` in PR body

**Test files to migrate (~32):**

Production code (2 files):
- `packages/erk-shared/src/erk_shared/context/factories.py` — change `GitHubPlanStore(github_issues, fake_time)` → `PlannedPRBackend(github, github_issues, time=fake_time)`
- `packages/erk-shared/src/erk_shared/sessions/discovery.py` — delete the `find_sessions_for_plan` function (zero callers, duplicated by `PlanBackend.find_sessions_for_plan`)

Test files — exec script tests (Group 1, ~20 files):
- `tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`
- `tests/unit/cli/commands/exec/scripts/test_plan_update_from_feedback.py`
- `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py`
- `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py`
- `tests/unit/cli/commands/exec/scripts/test_track_learn_evaluation.py`
- `tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`
- `tests/unit/cli/commands/exec/scripts/test_get_plan_metadata.py`
- `tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py`
- `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`
- `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`
- `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
- `tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py`
- `tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py`
- `tests/unit/cli/commands/exec/scripts/test_create_impl_context_from_plan.py`
- `tests/unit/cli/commands/exec/scripts/test_upload_session.py`
- `tests/unit/cli/commands/exec/scripts/test_register_one_shot_plan.py`
- `tests/unit/cli/commands/exec/scripts/test_update_pr_description.py`
- `tests/unit/cli/commands/exec/scripts/test_get_pr_context.py`
- `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py`

Test files — other tests (Group 2, ~8 files):
- `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py`
- `tests/unit/cli/commands/test_implement_shared.py`
- `tests/commands/pr/test_log.py`
- `tests/commands/pr/test_close.py`
- `tests/core/test_plan_context_provider.py`
- `tests/integration/test_plan_repo_root.py`
- `tests/unit/plan_store/test_plan_backend_interface.py`

erk-shared test files (Group 3, 2 files):
- `packages/erk-shared/tests/unit/plan_store/test_update_plan_content.py`
- `packages/erk-shared/tests/unit/learn/test_tracking.py`

## Phase 4: Delete Files and Clean Up

1. Delete `packages/erk-shared/src/erk_shared/plan_store/store.py`
2. Delete `packages/erk-shared/src/erk_shared/plan_store/github.py`
3. Delete `tests/integration/plan_store/test_github_plan_store.py` (tests the deleted class directly; overlaps Node 3.4 but safe to do here)
4. Update `packages/erk-shared/src/erk_shared/plan_store/__init__.py` — remove references to `store` and `github` modules

## Verification

1. `make fast-ci` — all unit tests pass
2. `ty` — no type errors in modified files
3. `ruff check` — no lint errors
4. Grep for any remaining `GitHubPlanStore` or `from erk_shared.plan_store.store` imports — should be zero
5. Grep for any remaining `PlanStore` references (excluding `PlanBackend` lines) — should only appear in docs/comments describing history
