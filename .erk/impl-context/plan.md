# Remove Backend Dispatching Layer

**Part of Objective #7911, Nodes 1.1, 1.2, 1.3, 1.4**

## Context

The plan backend dispatching layer (`get_plan_backend()`, `ERK_PLAN_BACKEND`, `PlanBackendType`) supported both issue-based and draft-PR-based plan storage. PR #7891 switched the default to `"draft_pr"` and the function already returns `"draft_pr"` unconditionally. The dispatching infrastructure is now dead code. This plan removes it, making draft-PR the sole backend.

**Direction: KEEP draft-PR behavior, DELETE github/issue-based code paths.**

Previous attempt (PR #7922) was dispatched remotely but CI never ran. This is a fresh replan against current master.

## Changes

### Node 1.1: Delete definitions

**`packages/erk-shared/src/erk_shared/plan_store/__init__.py`**
- Delete `get_plan_backend()` function (lines 24-37)
- Delete imports: `os` (line 18), `cast` (line 19), `PlanBackendType` (line 21)
- Update module docstring to remove multi-backend references

**`packages/erk-shared/src/erk_shared/context/types.py`**
- Delete `PlanBackendType = Literal["draft_pr", "github"]` (line 26)
- Delete comment on line 25

### Node 1.2: Remove all callers and dead branches

**`src/erk/core/context.py`** (lines 609-617)
- Remove `get_plan_backend` import (line ~81)
- Remove `GitHubPlanStore`, `RealPlanListService` imports
- Replace conditional with direct construction:
  ```python
  plan_store: PlanStore = DraftPRPlanBackend(github, issues, time=RealTime())
  plan_list_service: PlanListService = DraftPRPlanListService(github)
  ```
- Delete `PLAN_BACKEND_SPLIT` comment

**`packages/erk-shared/src/erk_shared/issue_workflow.py`** (lines 62-146)
- Remove `plan_backend: Literal["draft_pr", "github"]` parameter (line 66)
- Keep only draft-PR path (lines 110-118): read `branch_name` from plan-header metadata
- Delete `else:` branch (lines 119-125) that calls `generate_issue_branch_name()`
- Remove `generate_issue_branch_name` from imports (line 15) if now unused
- Remove `from typing import Literal` import if now unused

**`src/erk/cli/commands/branch/create_cmd.py`** (lines 144, 172-208)
- Delete `get_plan_backend` import (line 30)
- Delete `plan_backend = get_plan_backend()` (line 144)
- Keep only draft-PR branch, delete `elif plan_backend == "github":` branch

**`src/erk/cli/commands/branch/checkout_cmd.py`** (lines 413, 440-460)
- Delete `get_plan_backend` import (line 38)
- Delete `plan_backend = get_plan_backend()` (line 413)
- Keep only draft-PR path

**`src/erk/cli/commands/plan/list_cmd.py`** (line 43)
- Delete `get_plan_backend` import — it's already unused

**`src/erk/cli/commands/implement_shared.py`** (line 29, 534)
- Delete `get_plan_backend` import
- Remove `plan_backend=get_plan_backend()` from `prepare_plan_for_worktree()` call

**`src/erk/cli/commands/wt/create_cmd.py`** (line 39)
- Delete `get_plan_backend` import and remove from `prepare_plan_for_worktree()` call

**`src/erk/cli/commands/exec/scripts/plan_save.py`** (lines 437-466)
- Delete `get_plan_backend` import (line 52)
- Remove dispatch conditional (lines 442-455)
- Call `_save_plan_via_draft_pr()` directly
- Delete `plan_save_to_issue` import

**`src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`** (lines 61, 767)
- Delete `get_plan_backend` import (line 61)
- Remove `plan_backend=get_plan_backend()` from HookInput construction (line 767)
- Check if `plan_backend` is a field on `HookInput` — if so, remove it and update all `HookInput.for_test()` calls

**`packages/erk-shared/src/erk_shared/context/testing.py`** (lines 186-196)
- Delete `get_plan_backend` import (line 14)
- Remove conditional dispatch (lines 188-196)
- Always create `DraftPRPlanBackend(resolved_github, resolved_issues, time=FakeTime())`
- Remove `issues_explicitly_passed` guard logic

**`packages/erk-statusline/src/erk_statusline/statusline.py`** (lines 1192-1193)
- Delete `get_plan_backend` import (line 24)
- Remove `backend_type = get_plan_backend()` (line 1192)
- Hardcode `backend_display = "draft-pr"` or remove the display entirely

### Node 1.3: Remove `plan_backend` from TUI

**`src/erk/tui/app.py`**
- Delete `PlanBackendType` import (line 39)
- Remove `plan_backend` parameter from `__init__` (line 114) and `self._plan_backend` storage (line 129)
- At line 157: remove `self._plan_backend == "draft_pr"` check — always use draft-PR display name
- Remove `plan_backend=self._plan_backend` from `PlanDataTable()` (line 173) and `reconfigure()` (lines 397, 433) calls

**`src/erk/tui/widgets/plan_table.py`**
- Remove `plan_backend` parameter from `__init__` (line 74) and `reconfigure()` (line 112)
- Remove `self._plan_backend` field
- At all `_plan_backend == "draft_pr"` checks (lines 152, 175, 315): keep the draft-PR branch only
- At all `_plan_backend != "draft_pr"` checks (lines 199, 329): delete the block entirely

**`src/erk/tui/commands/types.py`**
- Remove `plan_backend: PlanBackendType` field from `CommandContext` (line 34)
- Remove `PlanBackendType` import

**`src/erk/tui/commands/provider.py`**
- Remove `plan_backend=self._app._plan_backend` from `CommandContext` construction (lines 97, 206)

**`src/erk/tui/commands/registry.py`**
- Delete `_is_github_backend()` function (lines 31-33)
- Remove any `is_available=_is_github_backend` from command registrations — these commands become unconditionally unavailable (they were github-only) or unconditionally available

### Node 1.4: Remove `get_provider_name()=="github-draft-pr"` conditionals

For each file: the `get_provider_name() == "github-draft-pr"` check is always true now. Keep the draft-PR branch, delete the else.

**`src/erk/cli/commands/pr/submit_pipeline.py`** (line 680)
- Keep draft-PR branch content, delete else

**`src/erk/cli/commands/one_shot_dispatch.py`** (lines 183, 193-230+)
- Delete `is_draft_pr` variable, delete `if not is_draft_pr:` skeleton issue block
- Keep draft-PR path only

**`src/erk/cli/commands/exec/scripts/trigger_async_learn.py`** (lines 298, 651)
- Keep draft-PR branch at line 298
- Hardcode `"draft_pr"` at line 651

**`src/erk/cli/commands/exec/scripts/update_pr_description.py`** (line 153)
- Keep draft-PR branch, delete else

**`src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`** (line 77)
- Keep draft-PR branch, delete else

**`src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`** (line 410)
- Always call `_setup_draft_pr_plan()`, delete `_setup_issue_plan()` conditional

**`src/erk/cli/commands/pr/rewrite_cmd.py`** (line 166)
- Keep draft-PR branch, delete else

**`src/erk/cli/commands/submit.py`** (line 1246)
- Delete `is_draft_pr` variable, keep draft-PR validation path, delete else

**`src/erk/cli/commands/exec/scripts/handle_no_changes.py`** (line 195)
- Delete `is_draft_pr` variable, keep draft-PR path

**`src/erk/cli/commands/exec/scripts/get_plan_info.py`** (line 69)
- Hardcode `"backend": "github-draft-pr"` or remove field

**`src/erk/cli/commands/exec/scripts/create_impl_context_from_plan.py`** (line 56)
- Remove `provider = backend.get_provider_name()` if it feeds only deleted conditionals

**`src/erk/cli/commands/implement.py`** (line 152)
- Remove `provider_name = ctx.plan_store.get_provider_name()` if unused after deletions

## Test Updates

**Delete entirely:**
- `tests/unit/plan_store/test_get_plan_backend.py`

**Update (remove `plan_backend` parameters and github-backend test cases):**
- `tests/unit/shared/test_issue_workflow.py` — remove `plan_backend` parameter from test calls
- `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` — remove `plan_backend` from `HookInput.for_test()`
- `tests/unit/cli/commands/exec/scripts/test_plan_save.py` — remove dispatch tests
- `tests/tui/test_app.py` — remove `plan_backend` from `ErkDashApp` construction
- `tests/tui/test_plan_table.py` — remove `plan_backend` from `PlanDataTable` construction
- `tests/tui/commands/test_registry.py` — remove `_is_github_backend` tests
- `tests/tui/screens/test_launch_screen.py` — remove `plan_backend` if present
- `tests/commands/branch/test_checkout_cmd.py` — remove github-backend test cases
- `tests/unit/cli/commands/branch/test_create_cmd.py` — remove github-backend test cases
- `tests/commands/implement/test_issue_mode.py` — remove github-backend test cases
- `tests/commands/implement/test_execution_modes.py`, `test_flags.py`, `test_model_flag.py`
- `tests/commands/one_shot/test_one_shot_dispatch.py` — remove skeleton issue tests
- `tests/commands/plan/test_submit.py` — remove github-backend submit tests
- `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py`
- `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`
- `tests/unit/plan_store/test_plan_backend_interface.py` — simplify to single backend
- `tests/test_utils/plan_helpers.py` — remove `plan_backend` helpers
- `tests/commands/plan/test_view.py`, `tests/core/test_plan_context_provider.py`
- `tests/integration/test_plan_repo_root.py`

## Verification

1. Grep verification: `get_plan_backend`, `ERK_PLAN_BACKEND`, `PlanBackendType`, `plan_backend == "github"` — 0 hits in `src/` and `packages/`
2. `ruff check` and `ruff format` — no lint errors
3. `ty` — no type errors
4. Scoped unit tests for each modified file
5. Full `fast-ci` pass

## Implementation Order

1. **Node 1.1** first — delete definitions (creates import errors that guide remaining work)
2. **Node 1.2** — fix all callers of `get_plan_backend` and `prepare_plan_for_worktree`
3. **Node 1.3** — clean up TUI layer
4. **Node 1.4** — collapse `get_provider_name()` conditionals
5. **Tests** — update in parallel with each node
6. **Verification** — grep + lint + type check + test suite
