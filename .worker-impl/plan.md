# Plan: Move TUI Gateways to gateway/

Part of **Objective #5930**, Steps 9.1-9.4 (Final Phase)

## Overview

Consolidate CommandExecutor and PlanDataProvider into `erk_shared/gateway/` following the established gateway pattern from prior phases.

## Current State

**CommandExecutor:**
- ABC: `src/erk/tui/commands/executor.py`
- Real: `src/erk/tui/commands/real_executor.py`
- Fake: `tests/fakes/command_executor.py`

**PlanDataProvider:**
- ABC + Real: `src/erk/tui/data/provider.py` (both in same file)
- Fake: `tests/fakes/plan_data_provider.py`

## Target Structure

```
packages/erk-shared/src/erk_shared/gateway/command_executor/
├── __init__.py          # Docstring only
├── abc.py               # CommandExecutor ABC
├── real.py              # RealCommandExecutor
└── fake.py              # FakeCommandExecutor

packages/erk-shared/src/erk_shared/gateway/plan_data_provider/
├── __init__.py          # Docstring only
├── abc.py               # PlanDataProvider ABC
├── real.py              # RealPlanDataProvider
└── fake.py              # FakePlanDataProvider + make_plan_row helper
```

## Import Sites

**CommandExecutor (4 files):**
- `src/erk/tui/commands/real_executor.py` (imports ABC)
- `tests/fakes/command_executor.py` (imports ABC)
- `src/erk/tui/app.py` (imports ABC, creates RealCommandExecutor)
- `src/erk/tui/screens/plan_detail_screen.py` (imports ABC)

**PlanDataProvider (7 files):**
- `tests/fakes/plan_data_provider.py` (imports ABC)
- `src/erk/cli/commands/plan/list_cmd.py` (creates RealPlanDataProvider)
- `src/erk/tui/app.py` (imports ABC)
- `src/erk/tui/screens/plan_detail_screen.py` (imports ABC)
- `src/erk/tui/screens/issue_body_screen.py` (imports ABC)
- `tests/tui/data/test_provider.py` (tests)
- `tests/integration/test_plan_repo_root.py` (tests)

## Implementation Steps

### Step 1: Create gateway/command_executor/

**1a. Create `__init__.py`:**
```python
"""Command execution interface for TUI operations.

Import from submodules:
- abc: CommandExecutor
- real: RealCommandExecutor
- fake: FakeCommandExecutor
"""
```

**1b. Create `abc.py`:** Move from `src/erk/tui/commands/executor.py`

**1c. Create `real.py`:** Move from `src/erk/tui/commands/real_executor.py`, update imports

**1d. Create `fake.py`:** Move from `tests/fakes/command_executor.py`, update imports

### Step 2: Create gateway/plan_data_provider/

**2a. Create `__init__.py`:**
```python
"""Plan data provider interface for TUI plan tables.

Import from submodules:
- abc: PlanDataProvider
- real: RealPlanDataProvider
- fake: FakePlanDataProvider, make_plan_row
"""
```

**2b. Create `abc.py`:** Extract PlanDataProvider ABC from `src/erk/tui/data/provider.py`

**2c. Create `real.py`:** Extract RealPlanDataProvider from `src/erk/tui/data/provider.py`, update imports

**2d. Create `fake.py`:** Move from `tests/fakes/plan_data_provider.py`, update imports

### Step 3: Update ALL import sites

**Pattern for CommandExecutor:**
```python
# OLD
from erk.tui.commands.executor import CommandExecutor
from erk.tui.commands.real_executor import RealCommandExecutor

# NEW
from erk_shared.gateway.command_executor.abc import CommandExecutor
from erk_shared.gateway.command_executor.real import RealCommandExecutor
```

**Pattern for PlanDataProvider:**
```python
# OLD
from erk.tui.data.provider import PlanDataProvider, RealPlanDataProvider

# NEW
from erk_shared.gateway.plan_data_provider.abc import PlanDataProvider
from erk_shared.gateway.plan_data_provider.real import RealPlanDataProvider
```

### Step 4: Delete old locations

- Delete `src/erk/tui/commands/executor.py`
- Delete `src/erk/tui/commands/real_executor.py`
- Delete `tests/fakes/command_executor.py`
- Delete `tests/fakes/plan_data_provider.py`
- Update `src/erk/tui/data/provider.py` to only contain types/helpers (or delete if empty)

## Files to Modify

**Create (8 files):**
- `packages/erk-shared/src/erk_shared/gateway/command_executor/__init__.py`
- `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/command_executor/real.py`
- `packages/erk-shared/src/erk_shared/gateway/command_executor/fake.py`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/__init__.py`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`

**Delete (4 files):**
- `src/erk/tui/commands/executor.py`
- `src/erk/tui/commands/real_executor.py`
- `tests/fakes/command_executor.py`
- `tests/fakes/plan_data_provider.py`

**Update imports (~9 files):**
- `src/erk/tui/app.py`
- `src/erk/tui/screens/plan_detail_screen.py`
- `src/erk/tui/screens/issue_body_screen.py`
- `src/erk/tui/data/provider.py` (remove ABC, keep only RealPlanDataProvider or delete)
- `src/erk/cli/commands/plan/list_cmd.py`
- `tests/tui/data/test_provider.py`
- `tests/integration/test_plan_repo_root.py`

## Notes

**PlanDataProvider complexity:** The real implementation has many dependencies (ErkContext, HttpClient, etc.). These stay the same - only the import path changes.

**Helper function:** `make_plan_row()` helper in the fake module stays with FakePlanDataProvider since it's test-only.

## Verification

1. **Import check:** Verify no imports from old locations
   ```bash
   rg "from erk\.tui\.commands\.executor" --type py
   rg "from erk\.tui\.commands\.real_executor" --type py
   rg "from tests\.fakes\.command_executor" --type py
   rg "from tests\.fakes\.plan_data_provider" --type py
   ```
   All should return empty.

2. **Run CI:** `make all-ci` passes

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Reference: `docs/learned/architecture/gateway-abc-implementation.md`

## Objective Completion

This is the **final phase** of Objective #5930. After this PR merges:
- All gateways will be consolidated under `erk_shared/gateway/`
- Consider closing Objective #5930