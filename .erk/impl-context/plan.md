# Plan: Phase 3 — Rename plan_store/plan_backend properties and helper functions

**Part of Objective #9318, Nodes 3.1–3.5**

## Context

Objective #9318 is systematically renaming "plan" terminology to "PR" across the codebase. Phases 1-2 renamed types, classes, and module files. Phase 3 renames context properties and standalone helper functions — the next layer in the dependency chain.

**Node 3.4 is already complete** — `extract_title_from_plan()` was renamed to `extract_title_from_pr()` in PR #9352. Will be marked done as part of this PR.

## Scope

| Node | Rename | Definition | Src Sites | Test Sites |
|------|--------|-----------|-----------|------------|
| 3.1 | `plan_store` → `pr_store` (field) | `erk_shared/context/context.py:90` | ~12 | ~334 |
| 3.2 | `plan_backend` → `pr_backend` (property) | `erk_shared/context/context.py:176` | ~100 | ~93 |
| 3.2 | `require_plan_backend()` → `require_pr_backend()` | `erk_shared/context/helpers.py` | ~25 exec scripts | tests |
| 3.3 | Delete `extract_plan_number()` (replacement exists) | `src/erk/cli/commands/run/shared.py:26` | 0 callers | 1 test file |
| 3.4 | *Already done* | — | — | — |
| 3.5 | `build_original_plan_section()` → `build_original_pr_section()` | `erk_shared/pr_store/planned_pr_lifecycle.py:111` | ~4 | ~4 |

## Implementation Steps

### Step 1: Rename `plan_store` field → `pr_store` (Node 3.1)

**Definition** — `packages/erk-shared/src/erk_shared/context/context.py:90`:
- Rename field `plan_store: ManagedPrBackend` → `pr_store: ManagedPrBackend`
- Update constructor param at `__init__` (if present) and any docstrings referencing `plan_store`

**Call sites** — Replace `ctx.plan_store` / `self.plan_store` across:
- `src/erk/cli/commands/wt/create_cmd.py` (1)
- `src/erk/cli/commands/wt/delete_cmd.py` (2)
- `src/erk/cli/commands/pr/close_cmd.py` (2)
- `src/erk/cli/commands/pr/dispatch_cmd.py` (1)
- `src/erk/cli/commands/implement.py` (2)
- `src/erk/cli/commands/land_learn.py` (1)
- `src/erk/cli/commands/objective_helpers.py` (2)
- `src/erk/cli/commands/branch/checkout_cmd.py` (1)
- `src/erk/cli/commands/objective/plan_cmd.py` (if present)
- ~48 test files (mostly `plan_store=` kwarg in context construction)

Use `libcst-refactor` agent or `rename-swarm` for the mechanical bulk rename.

### Step 2: Rename `plan_backend` property → `pr_backend` (Node 3.2)

**Definition** — `packages/erk-shared/src/erk_shared/context/context.py:176`:
- Rename property `plan_backend` → `pr_backend`
- Update docstring

**Helper** — `packages/erk-shared/src/erk_shared/context/helpers.py`:
- Rename `require_plan_backend()` → `require_pr_backend()`
- Update docstring examples

**Call sites** — Replace `ctx.plan_backend` / `require_plan_backend(ctx)` across:
- 41 src files (mostly exec scripts using `require_plan_backend`)
- ~13 test files

Also update the property body: `return self.plan_store` → `return self.pr_store` (after Step 1).

### Step 3: Delete `extract_plan_number()` (Node 3.3)

**File**: `src/erk/cli/commands/run/shared.py:26-43`
- Delete the `extract_plan_number()` function (no callers in src/)
- `extract_pr_number()` already exists at line 6 as the replacement

**Test file**: `tests/commands/run/test_shared.py`
- Remove tests for `extract_plan_number()`
- Keep tests for `extract_pr_number()`

**Doc reference**: `docs/learned/cli/workflow-run-list.md` — update any mention

### Step 4: Mark Node 3.4 as done

Run: `erk exec update-objective-node 9318 --node 3.4 --status done --pr "#9352"`

(Already renamed in Phase 2 PR)

### Step 5: Rename `build_original_plan_section()` → `build_original_pr_section()` (Node 3.5)

**Definition** — `packages/erk-shared/src/erk_shared/pr_store/planned_pr_lifecycle.py:111`:
- Rename function and update docstring

**Call sites (src/)**:
- `src/erk/cli/commands/pr/shared.py` (import + usage)
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` (import + usage)

**Test file**:
- `tests/unit/pr_store/test_planned_pr_lifecycle.py` (import + test)

### Step 6: Update documentation references

- `docs/learned/architecture/plan-backend-migration.md` — update `plan_backend` → `pr_backend`
- `docs/learned/planning/plan-backend-migration.md` — same
- `docs/learned/cli/backend-aware-display.md` — update references
- `docs/learned/ci/exec-script-environment-requirements.md` — update `require_plan_backend`
- `docs/learned/cli/workflow-run-list.md` — update `extract_plan_number` references

## Execution Strategy

Use `libcst-refactor` agent for the two high-volume renames (Steps 1-2) to batch the mechanical changes across 100+ files. Steps 3 and 5 are small enough to do manually.

## Verification

1. `make fast-ci` — run unit tests + lint + type checking
2. Grep audit: confirm zero remaining references to `plan_store`, `plan_backend`, `require_plan_backend`, `extract_plan_number`, `build_original_plan_section` in src/ and tests/ (excluding `__pycache__`, docs that were updated)
3. `make all-ci` — full integration test suite

## Key Files

- `packages/erk-shared/src/erk_shared/context/context.py` — field + property definitions
- `packages/erk-shared/src/erk_shared/context/helpers.py` — `require_plan_backend()`
- `src/erk/cli/commands/run/shared.py` — `extract_plan_number()` deletion
- `packages/erk-shared/src/erk_shared/pr_store/planned_pr_lifecycle.py` — `build_original_plan_section()`
- `tests/fakes/tests/shared_context.py` — test context construction (plan_store kwarg)
- `tests/test_utils/test_context.py` — test context utilities
