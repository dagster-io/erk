# Plan: Remove Backend Dispatching Layer (Objective #7911, Phase 1)

Part of Objective #7911, Nodes 1.1, 1.2, 1.3, 1.4

## Context

The plan backend dispatching layer (`get_plan_backend()`, `ERK_PLAN_BACKEND`, `PlanBackendType`) was introduced to support both issue-based and draft-PR-based plan storage. PR #7871 already switched the default to "draft_pr" and removed most conditional branches, but the dispatching infrastructure and several remaining conditionals still exist. This plan removes them entirely, making draft-PR the sole backend.

**Direction**: KEEP draft-PR behavior, DELETE github/issue-based behavior.

## Changes

### Node 1.1: Delete `get_plan_backend()` and `PlanBackendType`

**`packages/erk-shared/src/erk_shared/plan_store/__init__.py`**
- Delete `get_plan_backend()` function (lines 24-37)
- Delete `import os` and `from typing import cast` (only used by this function)
- Keep module docstring (update to remove references to multi-backend)

**`packages/erk-shared/src/erk_shared/context/types.py`**
- Delete `PlanBackendType = Literal["draft_pr", "github"]` (line 26)

### Node 1.2: Remove all callers and dead branches

**`src/erk/core/context.py`** (lines 609-617)
- Remove conditional: always create `DraftPRPlanBackend` and `DraftPRPlanListService`
- Delete `else:` branch (GitHubPlanStore/RealPlanListService)
- Remove imports: `get_plan_backend`, `GitHubPlanStore`, `RealPlanListService`

**`packages/erk-shared/src/erk_shared/issue_workflow.py`** (lines 62-125)
- Remove `plan_backend` parameter from `prepare_plan_for_worktree()`
- Keep only the draft-PR branch (lines 110-118): read `branch_name` from plan-header metadata
- Delete the `else:` branch (lines 119-125) that calls `generate_issue_branch_name()`

**`src/erk/cli/commands/branch/create_cmd.py`** (lines 144-194)
- Remove `plan_backend = get_plan_backend()` (line 144)
- Remove `plan_backend=plan_backend` from `prepare_plan_for_worktree()` call
- Keep only the draft-PR branch (lines 174-185): fetch/track existing branch
- Delete `elif setup is None or plan_backend == "github":` branch (lines 186-193)
- The `setup is None` case (no --for-plan) stays as-is — it doesn't go through this path

**`src/erk/cli/commands/branch/checkout_cmd.py`** (lines 413-457)
- Same pattern as create_cmd: remove `plan_backend`, keep draft-PR branch (lines 440-448)
- Delete `elif plan_backend == "github":` branch (lines 449-457)

**`src/erk/cli/commands/plan/list_cmd.py`** (line 650)
- Delete `plan_backend = get_plan_backend()` — dead code, variable is unused

**`src/erk/cli/commands/implement_shared.py`** (line 534)
- Remove `plan_backend=get_plan_backend()` from `prepare_plan_for_worktree()` call

**`src/erk/cli/commands/wt/create_cmd.py`** (line 679)
- Remove `plan_backend = get_plan_backend()` and pass-through to `prepare_plan_for_worktree()`

**`src/erk/cli/commands/exec/scripts/plan_save.py`** (lines 437-466)
- Remove the dispatch conditional (`if get_plan_backend() != "draft_pr":`)
- Always call `_save_plan_via_draft_pr()` directly
- Delete the `ctx.invoke(plan_save_to_issue, ...)` branch
- Remove import of `get_plan_backend` and `plan_save_to_issue`

**`src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`**
- Remove `plan_backend` field from `HookInput` dataclass (line 143)
- Remove `plan_backend` parameter from `HookInput.for_test()` (line 163)
- Remove `plan_backend` parameter from `build_blocking_message()` (line 262)
- Remove `is_draft_pr = plan_backend == "draft_pr"` (line 281)
- Keep only the `is_draft_pr` branch content (lines 341-398), delete the `else:` branch (lines 352-424) which shows issue-based options
- Remove `plan_backend=get_plan_backend()` from `HookInput` construction (line 767)

**`packages/erk-shared/src/erk_shared/context/testing.py`** (lines 186-196)
- Remove conditional backend dispatch
- Always create `DraftPRPlanBackend(resolved_github, resolved_issues, time=FakeTime())`
- Remove `issues_explicitly_passed` guard logic
- Remove imports of `get_plan_backend`, `GitHubPlanStore`

**`packages/erk-shared/src/erk_shared/context/context.py`** and **`factories.py`**
- Remove any `PlanBackendType` references or imports

### Node 1.3: Remove `plan_backend` from TUI code

**`src/erk/tui/app.py`**
- Remove `plan_backend` parameter from `__init__` (line 114)
- Remove `self._plan_backend` storage (line 129)
- Hardcode draft-PR behavior at line 157: `if mode == ViewMode.PLANS:` (remove condition on `_plan_backend`)
- Remove `plan_backend=self._plan_backend` from `PlanDataTable()` and `reconfigure()` calls

**`src/erk/tui/widgets/plan_table.py`**
- Remove `plan_backend` parameter from `__init__` and `reconfigure()`
- Remove `self._plan_backend` storage
- At all `_plan_backend == "draft_pr"` checks (lines 152, 177, 318): keep the draft-PR branch, delete the else/fallback
- At all `_plan_backend != "draft_pr"` checks (lines 201, 332): delete the block (it's the github-only path)

**`src/erk/tui/commands/registry.py`**
- Delete `_is_github_backend()` function (lines 31-33)
- Lines 318, 327: commands using `_is_github_backend` as availability predicate — delete the `is_available` condition or remove command entries if they're github-only (close_plan, submit_to_queue)

### Node 1.4: Remove `get_provider_name()=="github-draft-pr"` conditionals

These conditionals check if the current backend is draft-PR. Since draft-PR is now the ONLY backend, the check is always true — keep the draft-PR branch, delete the else.

**`src/erk/cli/commands/pr/submit_pipeline.py`** (line 680)
- Keep draft-PR branch: extract metadata prefix, set `issue_number = None`
- Delete else branch: closing ref fallback logic

**`src/erk/cli/commands/one_shot_dispatch.py`** (lines 178, 346)
- Delete `is_draft_pr` variable
- Delete `if not is_draft_pr:` skeleton issue creation block
- Hardcode `"plan_backend": "draft_pr"` in inputs dict

**`src/erk/cli/commands/exec/scripts/trigger_async_learn.py`** (lines 298, 651)
- Keep draft-PR branch at line 298: `github.get_pr(repo_root, int(plan_id))`
- Delete else branch (resolve PR from branch metadata)
- Hardcode `"plan_backend": "draft_pr"` at line 651

**`src/erk/cli/commands/exec/scripts/update_pr_description.py`** (line 153)
- Always extract metadata prefix, always set issue_number/plans_repo to None
- Delete else branch (discover_issue_for_footer)

**`src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`** (line 77)
- Keep draft-PR branch: `github.get_pr(repo_root, issue_number)`
- Delete else branch (resolve PR from branch metadata)

**`src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`** (line 410)
- Always call `_setup_draft_pr_plan()`, delete the `_setup_issue_plan()` call and the conditional
- Can delete `_setup_issue_plan()` function if it's no longer called

**`src/erk/cli/commands/pr/rewrite_cmd.py`** (line 166)
- Same pattern as update_pr_description: always extract metadata prefix
- Delete else branch

**`src/erk/cli/commands/submit.py`** (line 1243)
- Delete `is_draft_pr` variable
- Keep draft-PR validation/trigger path
- Delete else branch (GitHub creation workflow)

## Files Modified (summary)

~20 source files across `src/erk/` and `packages/erk-shared/`

## Test Updates

- Update all tests for `exit_plan_mode_hook` that pass `plan_backend` parameter
- Update tests for `prepare_plan_for_worktree` that pass `plan_backend` parameter
- Update tests for `HookInput.for_test()` calls
- Update TUI tests that pass `plan_backend` to `ErkDashApp` or `PlanDataTable`
- Delete test cases for the github/issue-based code paths

## Verification

1. Run `ruff check` and `ruff format` — no lint errors
2. Run `ty` — no type errors
3. Run scoped unit tests:
   - `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
   - `tests/unit/cli/commands/exec/scripts/test_plan_save.py`
   - `tests/unit/shared/test_issue_workflow.py`
   - `tests/tui/`
   - `tests/unit/cli/commands/` (branch, plan, pr, wt commands)
4. Grep verification: `get_plan_backend`, `ERK_PLAN_BACKEND`, `plan_backend == "github"`, `PlanBackendType` — 0 hits in `src/` and `packages/`
5. Run full fast-ci to catch any remaining breakage
