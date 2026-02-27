# Fix: Thread `plan_id` through land execution pipeline so `create_learn_issue` fires

## Context

`create_learn_issue` never fires on `erk land` because `plan_id` is resolved during validation but lost when constructing execution state. `make_execution_state()` hardcodes `plan_id = None` (line 577 of `land_pipeline.py`), so the `create_learn_issue` step always early-returns. This affects both the direct path and the deferred exec script path.

The activation script generation already passes `--plan-number` correctly — the plumbing just stops short of reaching `make_execution_state()`.

## Changes

### 1. Add `plan_id` parameter to `make_execution_state()`

**File:** `src/erk/cli/commands/land_pipeline.py`

- Add `plan_id: str | None` keyword parameter to `make_execution_state()` (line 558)
- Remove hardcoded `plan_id = None` (line 577), use the parameter instead

### 2. Pass `plan_id` in direct path

**File:** `src/erk/cli/commands/land_cmd.py`

- In `_execute_land_directly()` (line 892): add `plan_id=plan_id` to the `make_execution_state()` call — `plan_id` is already resolved on line 888

### 3. Thread `plan_number` through deferred path

**File:** `src/erk/cli/commands/land_cmd.py`

- Add `plan_number: int | None` parameter to `_execute_land()` (line 1379)
- In `_execute_land()` (line 1423): pass `plan_id=str(plan_number) if plan_number is not None else None` to `make_execution_state()`

### 4. Pass `plan_number` from exec script

**File:** `src/erk/cli/commands/exec/scripts/land_execute.py`

- In `land_execute()` (line 166): add `plan_number=plan_number` to the `_execute_land()` call — `plan_number` is already accepted as a CLI option

### 5. Update existing tests

**File:** `tests/unit/cli/commands/land/pipeline/test_run_execution_pipeline.py`

- Both `test_make_execution_state_*` tests (lines 130, 149): add `plan_id=None` to `make_execution_state()` calls

## Verification

1. Run scoped tests: `pytest tests/unit/cli/commands/land/`
2. Run learn-specific tests: `pytest tests/unit/cli/commands/land/pipeline/test_create_learn_issue.py`
3. Run full fast-ci: `make fast-ci`
