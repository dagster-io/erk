# Plan: Delete `get_plan_backend()` and `PlanBackendType`

**Part of Objective #7911, Node 1.1**

## Context

Objective #7911 eliminates the issue-based plan backend, leaving only the draft-PR backend. Node 1.1 is the first step: delete the two symbols that provide backend selection (`get_plan_backend()` function and `PlanBackendType` type alias), replacing all references with hardcoded `"draft_pr"` values.

This is a **mechanical replacement** — no behavioral branching logic is removed. Dead branches like `if plan_backend == "github":` will remain as always-false code paths until node 1.2 cleans them up. The system continues to work identically since `get_plan_backend()` already defaults to `"draft_pr"`.

## Changes

### 1. Delete definitions

**`packages/erk-shared/src/erk_shared/plan_store/__init__.py`**
- Delete `get_plan_backend()` function (lines 24-37)
- Remove imports: `os`, `cast`, `PlanBackendType`
- Module retains only the docstring (submodules `types`, `store`, `backend`, `github` still exist)

**`packages/erk-shared/src/erk_shared/context/types.py`**
- Delete `PlanBackendType = Literal["draft_pr", "github"]` (line 26) and its comment (line 25)

### 2. Update production callers (10 files)

At each file: remove the `from erk_shared.plan_store import get_plan_backend` import, replace `get_plan_backend()` calls with the string literal `"draft_pr"`.

| File | Change |
|------|--------|
| `src/erk/core/context.py:609-612` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/exec/scripts/plan_save.py:448` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py:767` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/implement_shared.py:534` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/wt/create_cmd.py:679` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/branch/checkout_cmd.py:413` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/branch/create_cmd.py:144` | `get_plan_backend()` → `"draft_pr"` |
| `src/erk/cli/commands/plan/list_cmd.py:280,388` | `get_plan_backend()` → `"draft_pr"` (two calls) |
| `packages/erk-shared/src/erk_shared/context/testing.py:195` | `get_plan_backend()` → `"draft_pr"` |
| `packages/erk-statusline/src/erk_statusline/statusline.py:1192` | `get_plan_backend()` → `"draft_pr"` |

### 3. Update `PlanBackendType` usages (3 TUI files)

Replace `PlanBackendType` import and type annotations with `Literal["draft_pr"]`. These parameters will be removed entirely by node 1.3, but must compile now.

| File | Change |
|------|--------|
| `src/erk/tui/app.py` | Replace `PlanBackendType` annotation with `Literal["draft_pr"]` |
| `src/erk/tui/widgets/plan_table.py` | Replace `PlanBackendType` annotation with `Literal["draft_pr"]` |
| `src/erk/tui/commands/types.py` | Replace `PlanBackendType` annotation with `Literal["draft_pr"]` |

### 4. Update test callers (3 files)

Same mechanical replacement as production callers.

| File | Change |
|------|--------|
| `tests/commands/branch/test_checkout_cmd.py:711,911` | `get_plan_backend()` → `"draft_pr"` |
| `tests/unit/cli/commands/branch/test_create_cmd.py:380,464,582,761,985` | `get_plan_backend()` → `"draft_pr"` |
| `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py:967,1073` | `get_plan_backend()` → `"draft_pr"` |

### 5. Delete test file

- Delete `tests/unit/plan_store/test_get_plan_backend.py` (tests the deleted function)

### 6. Not in scope (deferred to later nodes)

- **Dead branches** (`if plan_backend == "github":`) — node 1.2
- **TUI `plan_backend` parameter removal** — node 1.3
- **`get_provider_name()` conditionals** — node 1.4
- **`ERK_PLAN_BACKEND` env var in CI workflows** — later cleanup
- **`ERK_PLAN_BACKEND` env var in test fixtures** — nodes 2.x
- **Inline `Literal["draft_pr", "github"]` in `issue_workflow.py`** — node 1.2 or 1.4

## Verification

1. Run `ty` for type checking across all three packages
2. Run `ruff check` for lint
3. Run scoped tests:
   - `pytest tests/unit/plan_store/` — confirm deleted test is gone, no other breakage
   - `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py` — plan save still works
   - `pytest tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py`
   - `pytest tests/unit/cli/commands/branch/`
   - `pytest tests/commands/branch/test_checkout_cmd.py`
   - `pytest tests/commands/plan/`
   - `pytest packages/erk-statusline/tests/test_statusline.py`
4. Run `make fast-ci` for full validation
