# Plan: Delete Legacy Issue-Based Plan Infrastructure (Nodes 1.2 + 1.3)

Part of Objective #7775, Nodes 1.2 and 1.3

## Context

Erk has two plan storage backends: the original GitHub Issues backend (`GitHubPlanStore`) and the newer Draft PR backend (`DraftPRPlanBackend`). Node 1.1 (PR #7871, in progress) makes `draft_pr` the default and removes all `if plan_backend == "issues"` conditional branches. Once 1.1 lands, the issue-based backend code becomes dead. This plan deletes that dead code.

**Dependency: This plan must be implemented AFTER PR #7871 (node 1.1) lands.**

## Phase 1: Delete `get_plan_backend()` and `ERK_PLAN_BACKEND` env var

Remove the backend selection mechanism since there will be only one backend.

### Files to modify

- **`packages/erk-shared/src/erk_shared/plan_store/__init__.py`** — Delete `get_plan_backend()` function, remove `os` and `cast` imports, remove `PlanBackendType` import
- **`packages/erk-shared/src/erk_shared/context/types.py`** — Delete `PlanBackendType` type alias
- **All callers of `get_plan_backend()`** — After node 1.1 lands, these should already be simplified to only use the draft_pr path. Remove any remaining imports/references:
  - `src/erk/core/context.py` (line 81, 612)
  - `packages/erk-shared/src/erk_shared/context/testing.py` (line 14, 193)
  - `src/erk/cli/commands/plan/list_cmd.py` (line 44)
  - `src/erk/cli/commands/implement_shared.py` (line 29)
  - `src/erk/cli/commands/branch/create_cmd.py` (line 30)
  - `src/erk/cli/commands/branch/checkout_cmd.py` (line 38)
  - `src/erk/cli/commands/exec/scripts/plan_save.py` (line 52)
  - `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` (line 61)
  - `src/erk/cli/commands/wt/create_cmd.py` (line 39)
  - `packages/erk-statusline/src/erk_statusline/statusline.py` (line 24)
- **Workflow files** — Remove `plan_backend` input and `ERK_PLAN_BACKEND` env var:
  - `.github/workflows/learn.yml` (line 47)
  - `.github/workflows/plan-implement.yml` (lines 101, 152, 435)
  - `.github/workflows/one-shot.yml` (lines 47, 236)
- **Test files** — Delete or update:
  - `tests/unit/plan_store/test_get_plan_backend.py` — DELETE entirely
  - `tests/unit/cli/commands/branch/test_create_cmd.py` — remove `get_plan_backend` references
  - `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` — remove references
  - `tests/commands/branch/test_checkout_cmd.py` — remove references
  - All tests using `monkeypatch.setenv("ERK_PLAN_BACKEND", ...)` or `env_overrides={"ERK_PLAN_BACKEND": ...}`

## Phase 2: Delete `GitHubPlanStore` and `RealPlanListService`

### Delete GitHubPlanStore

- **`packages/erk-shared/src/erk_shared/plan_store/github.py`** — DELETE entire file
- **`packages/erk-shared/src/erk_shared/plan_store/__init__.py`** — Remove import/reference to GitHubPlanStore
- **`tests/integration/plan_store/test_github_plan_store.py`** — DELETE entire file
- **`tests/unit/plan_store/test_plan_backend_interface.py`** — Remove GitHubPlanStore from interface compliance tests
- **`tests/test_utils/plan_helpers.py`** — Remove GitHubPlanStore usage (lines 72-89)
- **`tests/commands/plan/test_log.py`**, **`test_close.py`** — Update to use DraftPRPlanBackend
- **`tests/core/test_plan_context_provider.py`** — Update to use DraftPRPlanBackend
- **`src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py`** — DELETE (migration tool no longer needed)
- **`packages/erk-shared/src/erk_shared/sessions/discovery.py`** — Remove GitHubPlanStore construction (lines 83-95), refactor `get_plan_from_session()` to use DraftPRPlanBackend

### Delete RealPlanListService

- **`src/erk/core/services/plan_list_service.py`** — Delete `RealPlanListService` class (lines 121-204), keep `DraftPRPlanListService` and helpers
- **`src/erk/core/services/objective_list_service.py`** — Refactor `RealObjectiveListService` to call `github.get_issues_with_pr_linkages()` directly instead of wrapping `RealPlanListService`. Inline the conversion logic (`issue_info_to_plan`, workflow run fetching).
- **`src/erk/core/context.py`** — Remove `RealPlanListService` import and construction (line 617)
- **`tests/unit/services/test_plan_list_service.py`** — Delete `RealPlanListService` tests (keep `DraftPRPlanListService` tests)
- **`tests/integration/test_plan_repo_root.py`** — Remove `RealPlanListService` import/usage

## Phase 3: Delete `extract_leading_issue_number` and callers

With draft-PR as the only backend, all branches use `plnd/` or `planned/` prefix. `extract_leading_issue_number` always returns None for these branches, making it dead code.

### Delete the function

- **`packages/erk-shared/src/erk_shared/naming.py`** (lines 556-587) — Delete function

### Delete `get_branch_issue()` from GitBranchOps ABC

The `get_branch_issue()` method wraps `extract_leading_issue_number`. With only draft-PR branches, it always returns None — dead code. Delete from the ABC and all 5 implementations:

- **`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py`** (line 237) — Remove abstract method
- **`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py`** (lines 355-362) — Delete method
- **`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/fake.py`** (line 328) — Delete method
- **`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py`** (lines 107-109) — Delete method
- **`packages/erk-shared/src/erk_shared/gateway/git/branch_ops/printing.py`** (lines 100-102) — Delete method
- **`packages/erk-shared/src/erk_shared/gateway/git/fake.py`** — Remove any `get_branch_issue` reference
- **`src/erk/cli/commands/wt/list_cmd.py`** (line 108) — Only external caller. Remove call, rely on `.impl/plan-ref.json` for plan association.
- **`tests/unit/fakes/test_fake_git.py`** — Remove `get_branch_issue` test cases

### Update other callers

- **`packages/erk-shared/src/erk_shared/impl_folder.py`** (line 268) — `discover_plan_id_from_branch_or_impl()`: Remove the `branch_issue` path, rely solely on `.impl/plan-ref.json`. Simplify function.
- **`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`** (lines 495-507) — Remove the `extract_leading_issue_number` call, keep only the draft-PR branch fallback path (`.impl/plan-ref.json`)
- **`src/erk/cli/commands/plan/checkout_cmd.py`** (line 47) — Remove `extract_leading_issue_number` import and usage
- **`src/erk/cli/commands/pr/shared.py`** (line 212) — Remove usage, rely on `.impl/plan-ref.json` discovery
- **`src/erk/cli/commands/land_pipeline.py`** (line 624-626) — Remove usage, use alternative plan ID discovery

### Delete tests

- **`tests/core/utils/test_naming.py`** (lines 505-531) — Delete `extract_leading_issue_number` test cases

## Phase 4: Clean up documentation

- Update docs referencing `ERK_PLAN_BACKEND`, `GitHubPlanStore`, `RealPlanListService`, `extract_leading_issue_number`:
  - `docs/learned/planning/draft-pr-plan-backend.md`
  - `docs/learned/planning/plan-creation-pathways.md`
  - `docs/learned/planning/branch-plan-resolution.md`
  - `docs/learned/testing/dual-backend-testing.md`
  - `docs/learned/testing/environment-variable-isolation.md`
  - `docs/learned/testing/backend-testing-composition.md`
  - `docs/learned/architecture/gateway-vs-backend.md`
  - `docs/learned/architecture/plan-backend-migration.md`

## Verification

1. `make fast-ci` — all unit tests pass
2. `make all-ci` — all integration tests pass
3. `ruff check` + `ty check` — no lint/type errors
4. Grep for deleted symbols to confirm no remaining references:
   - `GitHubPlanStore`, `RealPlanListService`, `get_plan_backend`, `ERK_PLAN_BACKEND`, `extract_leading_issue_number`, `PlanBackendType`