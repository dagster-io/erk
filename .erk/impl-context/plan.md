# Plan: Delete GitHubPlanStore, PlanStore ABC, and Inline into PlanBackend

Part of Objective #7911, Node 2.1

## Context

Erk is migrating from issue-based plan storage (GitHubPlanStore) to draft-PR-based storage (DraftPRPlanBackend). Phase 1 (PR #7912) removes all runtime dispatch between backends. Node 2.1 deletes the now-dead code: the deprecated `PlanStore` ABC, the `GitHubPlanStore` implementation, and inlines PlanStore's abstract methods into `PlanBackend`.

**Dependency:** Phase 1 (PR #7912) should land first. Some removals below may already be done. Check current state before each step.

## Files to Delete

1. `packages/erk-shared/src/erk_shared/plan_store/store.py` — deprecated PlanStore ABC (74 lines)
2. `packages/erk-shared/src/erk_shared/plan_store/github.py` — GitHubPlanStore (~691 lines)
3. `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py` — dead migration script (imports GitHubPlanStore)
4. `tests/unit/cli/commands/exec/scripts/test_plan_migrate_to_draft_pr.py` — its test
5. `tests/integration/plan_store/test_github_plan_store.py` — GitHubPlanStore-only integration tests

## Implementation Steps

### Step 1: Inline PlanStore into PlanBackend

**File:** `packages/erk-shared/src/erk_shared/plan_store/backend.py`

- Change `class PlanBackend(PlanStore)` to `class PlanBackend(ABC)`
- Add `ABC` to the `from abc import` line (currently only imports `abstractmethod`)
- Remove `from erk_shared.plan_store.store import PlanStore` (line 41)
- Add `close_plan` as `@abstractmethod` (currently inherited from PlanStore, not redeclared — line 354 has comment `# close_plan is inherited from PlanStore`). Copy the docstring from store.py.
- Update class docstring: remove "Extends PlanStore" and "inherited from PlanStore" language

### Step 2: Delete store.py, github.py, migration script + tests

Delete the 5 files listed above.

**Also update:** `src/erk/cli/commands/exec/group.py`
- Remove import of `plan_migrate_to_draft_pr` (lines 103-105)
- Remove `exec_group.add_command(plan_migrate_to_draft_pr, ...)` (line 234)

### Step 3: Clean up `__init__.py`

**File:** `packages/erk-shared/src/erk_shared/plan_store/__init__.py`

- Delete `get_plan_backend()` function (if still present after Phase 1)
- Remove unused imports (`os`, `cast`, `PlanBackendType`)
- Update docstring to remove PlanStore/GitHubPlanStore references
- Result: minimal `__init__.py` with just a docstring

### Step 4: Update ErkContext type annotations

**File:** `packages/erk-shared/src/erk_shared/context/context.py`
- Remove `from erk_shared.plan_store.store import PlanStore` (line 53)
- Change field `plan_store: PlanStore` (line 86) to `plan_store: PlanBackend` (already imported at line 52)
- Simplify `plan_backend` property (lines 160-173): remove isinstance check, just `return self.plan_store`

### Step 5: Update context factories

**File:** `packages/erk-shared/src/erk_shared/context/testing.py`
- Remove imports: `get_plan_backend`, `PlanStore`, `GitHubPlanStore`
- Add `from erk_shared.plan_store.backend import PlanBackend`
- Change parameter `plan_store: PlanStore | None` to `plan_store: PlanBackend | None`
- Change `resolved_plan_store: PlanStore` to `resolved_plan_store: PlanBackend`
- Simplify resolution: always default to `DraftPRPlanBackend(resolved_github, resolved_issues, time=FakeTime())`

**File:** `src/erk/core/context.py`
- Remove imports: `get_plan_backend`, `GitHubPlanStore`, `PlanStore`
- Add `from erk_shared.plan_store.backend import PlanBackend` (if not present)
- In `minimal_context()` (~line 165): change `GitHubPlanStore(fake_issues, fake_time)` to `DraftPRPlanBackend(fake_github, fake_issues, time=fake_time)` — will need a `FakeGitHub` instance
- In `context_for_test()` (~line 198): change param type to `PlanBackend | None`, default to `DraftPRPlanBackend(github, issues, time=time)`
- In `create_context()` (~lines 609-617): remove `get_plan_backend()` dispatch, always create `DraftPRPlanBackend` and `DraftPRPlanListService`

**File:** `packages/erk-shared/src/erk_shared/context/factories.py`
- Remove `GitHubPlanStore` import (line 92)
- Change `plan_store=GitHubPlanStore(github_issues, fake_time)` to use `DraftPRPlanBackend`
- Will need `DraftPRPlanBackend` and a `GitHub` instance (compose from existing `github_issues`)

### Step 6: Delete deprecated standalone function in sessions/discovery.py

**File:** `packages/erk-shared/src/erk_shared/sessions/discovery.py`
- Delete `find_sessions_for_plan()` standalone function (lines 75-96) — deprecated wrapper that creates a temporary GitHubPlanStore

### Step 7: Update test helper — plan_helpers.py

**File:** `tests/test_utils/plan_helpers.py`

- Remove `GitHubPlanStore` and `PlanStore` imports
- Add `from erk_shared.plan_store.backend import PlanBackend`
- **Rewrite `create_plan_store_with_plans()`**: delegate to `create_draft_pr_store_with_plans()`, change return type to `tuple[DraftPRPlanBackend, FakeGitHub]`
- Delete `_plan_to_issue_info()` helper (only used by old GitHubPlanStore path)
- **Simplify `create_plan_store()`**: remove `backend` parameter, always delegate to `create_draft_pr_store_with_plans()`, return type `tuple[PlanBackend, FakeGitHub]`

### Step 8: Update test files

**Callers of `create_plan_store_with_plans()`** (~20 call sites) — the return type changes from `(GitHubPlanStore, FakeGitHubIssues)` to `(DraftPRPlanBackend, FakeGitHub)`. Most unpack as `store, _` (no change needed). Those using the second element need `fake_github` instead of `fake_issues`:
- `tests/commands/workspace/test_delete.py` (3 call sites)
- `tests/commands/plan/test_log.py` (1)
- `tests/commands/plan/test_view.py` (2)
- `tests/commands/plan/test_close.py` (4)
- `tests/commands/test_top_level_commands.py` (1)
- `tests/commands/submit/test_multiple_issues.py` (1)
- `tests/commands/submit/test_base_branch.py` (3)
- `tests/commands/submit/test_dispatch_metadata.py` (1)
- `tests/commands/submit/test_workflow_config.py` (1)
- `tests/commands/submit/test_rollback.py` (1)
- `tests/commands/implement/test_issue_mode.py` (2)
- `tests/unit/cli/commands/branch/test_create_cmd.py` (1)

**Callers of `create_plan_store(plans, backend=...)`** — remove `backend` param:
- Same test files that pass `backend=plan_backend_type`

**Dual-backend parametrized fixtures** — remove `"github"` parametrization, simplify `plan_backend_type` fixture or delete it:
- `tests/commands/plan/test_view.py`
- `tests/commands/implement/test_model_flag.py`
- `tests/commands/implement/test_execution_modes.py`
- `tests/commands/implement/test_issue_mode.py`
- `tests/commands/implement/test_flags.py`
- `tests/commands/test_top_level_commands.py`

**GitHubPlanStore-specific test code:**
- `tests/unit/plan_store/test_plan_backend_interface.py` — remove `_make_github_plan_store()`, `_make_github_backend_with_plan()`, change parametrized fixtures to non-parametrized (DraftPR only), delete GitHubPlanStore-specific test functions
- `tests/commands/plan/test_close.py` — update tests that directly create GitHubPlanStore
- `tests/core/test_plan_context_provider.py` — change `GitHubPlanStore(github_issues)` to DraftPRPlanBackend
- `tests/integration/test_plan_repo_root.py` — change to DraftPRPlanBackend
- `packages/erk-shared/tests/unit/learn/test_tracking.py` — change to DraftPRPlanBackend

**Comment-only references** (update docstrings/comments mentioning GitHubPlanStore):
- `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py` (line 4)
- `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py` (line 423)

### Step 9: Update PlanBackendType (if still present)

**File:** `packages/erk-shared/src/erk_shared/context/types.py`
- If `PlanBackendType = Literal["draft_pr", "github"]` still exists, change to `Literal["draft_pr"]`
- If already removed by Phase 1, skip

## What This Node Does NOT Do (deferred)

- **Node 2.2:** Delete `RealPlanListService` (keep alive but unused)
- **Node 2.3:** Delete `plan_save_to_issue.py` exec script
- **Node 2.4:** Delete `issue_info_to_plan` from conversion.py, deeper test factory cleanup
- Documentation updates in `docs/learned/`

## Verification

1. `uv run ty check` — type checking passes
2. `uv run ruff check` — no lint errors
3. `uv run pytest tests/unit/plan_store/` — PlanBackend interface tests pass
4. `uv run pytest tests/commands/plan/` — plan commands work
5. `uv run pytest tests/commands/implement/` — implement commands work
6. `uv run pytest tests/commands/submit/` — submit commands work
7. `uv run pytest tests/core/test_plan_context_provider.py` — context provider works
8. `uv run pytest packages/erk-shared/tests/` — erk-shared tests pass
9. Full test suite as final check
