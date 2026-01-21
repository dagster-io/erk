# Plan: Delete Planner Group and Exclusively-Used Code

## Summary

Delete the `erk planner` CLI command group and all code that exists only to support it. The planner feature manages GitHub Codespaces for remote planning - it has a CLI group, registry abstraction, and test infrastructure.

## Files to Delete

### CLI Commands (8 files)
- `src/erk/cli/commands/planner/__init__.py` - Group definition
- `src/erk/cli/commands/planner/connect_cmd.py`
- `src/erk/cli/commands/planner/configure_cmd.py`
- `src/erk/cli/commands/planner/create_cmd.py`
- `src/erk/cli/commands/planner/list_cmd.py`
- `src/erk/cli/commands/planner/register_cmd.py`
- `src/erk/cli/commands/planner/set_default_cmd.py`
- `src/erk/cli/commands/planner/unregister_cmd.py`

### Core Implementation (5 files)
- `src/erk/core/planner/__init__.py`
- `src/erk/core/planner/registry_abc.py` - Re-export (wrapper)
- `src/erk/core/planner/registry_fake.py`
- `src/erk/core/planner/registry_real.py` - TOML file storage
- `src/erk/core/planner/types.py` - Re-export (wrapper)

### Tests (4 files)
- `tests/commands/planner/__init__.py`
- `tests/commands/planner/test_planner_connect.py`
- `tests/commands/planner/test_planner_register.py`
- `tests/unit/fakes/test_fake_planner_registry.py`

### Shared Package (1 file)
- `packages/erk-shared/src/erk_shared/core/planner_registry.py` - ABC + types

## Files to Modify

### 1. `src/erk/cli/cli.py`
- Remove import: `from erk.cli.commands.planner import planner_group` (line 30)
- Remove registration: `cli.add_command(planner_group)` (line 199)

### 2. `src/erk/cli/help_formatter.py`
- Remove `"planner"` from `grouped_commands` list (line 269)

### 3. `packages/erk-shared/src/erk_shared/context/context.py`
- Remove field: `planner_registry: PlannerRegistry` (line 89)
- Remove import: `from erk_shared.core.planner_registry import PlannerRegistry` (line 28)

### 4. `packages/erk-shared/src/erk_shared/core/fakes.py`
- Remove import: `from erk_shared.core.planner_registry import PlannerRegistry, RegisteredPlanner` (line 21)
- Remove entire `FakePlannerRegistry` class (lines 215-280)

### 5. `packages/erk-shared/src/erk_shared/context/testing.py`
- Remove import: `FakePlannerRegistry` from fakes import (line 16)
- Remove: `planner_registry=FakePlannerRegistry()` (line 156)

### 6. `packages/erk-shared/src/erk_shared/context/factories.py`
- Remove import: `FakePlannerRegistry` from fakes import (line 17)
- Remove: `planner_registry=FakePlannerRegistry()` (line 143)

### 7. `packages/erk-shared/src/erk_shared/core/__init__.py`
- Remove docstring line: `- erk_shared.core.planner_registry: PlannerRegistry, RegisteredPlanner` (line 13)

### 8. `src/erk/core/context.py`
- Remove import: `from erk.core.planner.registry_real import RealPlannerRegistry` (line 21)
- Remove import: `from erk_shared.core.planner_registry import PlannerRegistry` (line 42)
- Remove in `minimal_context()`: import `FakePlannerRegistry` (line 102) and usage (line 142)
- Remove in `context_for_test()`: import `FakePlannerRegistry` (line 223) and parameter/usage (lines 173, 312-313)
- Remove in `create_context()`: `planner_registry=RealPlannerRegistry(...)` (line 583)

## Execution Order

1. Delete all files (CLI commands, core implementation, tests, shared ABC)
2. Edit `cli.py` to remove import and registration
3. Edit `help_formatter.py` to remove from grouped_commands
4. Edit `context/context.py` to remove field and import
5. Edit `core/fakes.py` to remove FakePlannerRegistry class and imports
6. Edit `context/testing.py` to remove import and usage
7. Edit `context/factories.py` to remove import and usage
8. Edit `core/__init__.py` to remove docstring reference
9. Edit `src/erk/core/context.py` to remove all planner references

## Verification

1. Run `make fast-ci` to verify all tests pass
2. Run `erk --help` to verify planner is no longer listed
3. Run `ty check` to verify no type errors from removed field