# Plan: Rename plan-oriented types to PR terminology (Nodes 1.1–1.4)

Part of Objective #9318, Nodes 1.1, 1.2, 1.3, 1.4

## Context

Objective #9318 tracks the complete plan-to-PR terminology rename across the codebase. Nodes 1.1–1.4 are purely mechanical class/type renames with no behavioral changes — ideal for the `rename-swarm` skill which parallelizes bulk renames across many files using haiku agents.

## Renames

### Node 1.1: PlanNotFound → PrNotFound
- **Definition:** `packages/erk-shared/src/erk_shared/plan_store/types.py:84`
- **Import sites:** 31 files across `src/erk/` and `tests/`

### Node 1.2: PlanListService → PrListService, PlanListData → PrListData
- **Definition:** `packages/erk-shared/src/erk_shared/core/plan_list_service.py`
  - `PlanListData` (line 26) → `PrListData`
  - `PlanListService` (line 48) → `PrListService`
- **Import sites:** 19 files
- Also rename method `get_plan_list_data()` → `get_pr_list_data()` on the ABC and all implementations

### Node 1.3: PlannedPRPlanListService → ManagedPrListService
- **Definition:** `src/erk/core/services/plan_list_service.py:42`
- **Import sites:** 6 files
- Note: This fixes mixed terminology ("PlannedPR" + "Plan") into consistent "ManagedPr"

### Node 1.4: ValidPlanTitle → ValidPrTitle, InvalidPlanTitle → InvalidPrTitle
- **Definition:** `packages/erk-shared/src/erk_shared/naming.py` (lines 88, 99)
- **Import sites:** 3 files

## Implementation Strategy

Use `/rename-swarm` for each rename operation. The skill spawns parallel haiku agents to mechanically rename across all files.

### Phase 1: Rename class names (rename-swarm)

Run 5 rename-swarm operations sequentially (each one internally parallelizes across files):

1. `PlanNotFound` → `PrNotFound`
2. `PlanListData` → `PrListData`
3. `PlanListService` → `PrListService`
4. `PlannedPRPlanListService` → `ManagedPrListService`
5. `ValidPlanTitle` → `ValidPrTitle`
6. `InvalidPlanTitle` → `InvalidPrTitle`

### Phase 2: Rename method

- `get_plan_list_data` → `get_pr_list_data` (on ABC + all implementations and call sites)

### Phase 3: Update docstrings and comments

In the definition files only, update docstrings that reference the old names. The rename-swarm handles code references but docstrings describing the class purpose should be updated manually in:
- `packages/erk-shared/src/erk_shared/plan_store/types.py`
- `packages/erk-shared/src/erk_shared/core/plan_list_service.py`
- `src/erk/core/services/plan_list_service.py`
- `packages/erk-shared/src/erk_shared/naming.py`

### Phase 4: Update re-export in `__init__.py`

- Check `packages/erk-shared/src/erk_shared/core/__init__.py` for any re-exports of renamed symbols

## Key Files

- `packages/erk-shared/src/erk_shared/plan_store/types.py` — PlanNotFound definition
- `packages/erk-shared/src/erk_shared/core/plan_list_service.py` — PlanListService, PlanListData ABC
- `src/erk/core/services/plan_list_service.py` — PlannedPRPlanListService impl
- `packages/erk-shared/src/erk_shared/naming.py` — ValidPlanTitle, InvalidPlanTitle
- `packages/erk-shared/src/erk_shared/core/__init__.py` — possible re-exports

## Verification

1. Run `ruff check` to verify no import errors
2. Run `ty` for type checking
3. Run `pytest tests/unit/` for unit tests
4. Run `pytest tests/core/utils/test_naming.py` for naming tests
5. Run `pytest tests/unit/services/test_plan_list_service.py` for list service tests
6. Run `pytest tests/unit/plan_store/` for plan store tests
