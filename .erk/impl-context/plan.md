# Implementation Plan: Node 1.6 — Decouple Pool Config from Core

## Context

Part of Objective #9272: Extract Slot System into Plugin Package

Node 1.6 removes pool configuration from the core erk config module, making it internal to the erk_slots plugin package. Currently, `LoadedConfig` in erk_shared contains pool-related fields (`pool_size`, `pool_checkout_commands`, `pool_checkout_shell`), and `src/erk/cli/config.py` parses these from the `[pool]` section of config.toml. This creates a hard dependency between the core erk module and slot-specific configuration.

**Goal:** After this change, the core erk package no longer knows about or parses pool configuration. The erk_slots package is responsible for all pool-related config.

## Current Pool Config Flow

- **Definition:** `DEFAULT_POOL_SIZE = 4` in `erk_shared/slots/naming.py:10`
- **LoadedConfig fields** (in `erk_shared/context/types.py`):
  - `pool_size: int | None`
  - `pool_checkout_commands: list[str]`
  - `pool_checkout_shell: str | None`
- **Parsing:** `src/erk/cli/config.py` parses `[pool]` and `[pool.checkout]` sections from TOML
- **Merging:** `merge_configs()` and `merge_configs_with_local()` handle pool field merging
- **Runtime usage:** `erk_slots/common.py:get_pool_size()` reads `ctx.local_config.pool_size` with fallback to `DEFAULT_POOL_SIZE`
- **Display only:** `src/erk/cli/commands/config.py` displays pool settings; `pool_checkout_commands/shell` are never executed

## What Needs to Change

### 1. Create erk_slots Config Module
**New file:** `packages/erk-slots/src/erk_slots/config.py`

Create a new config module for erk_slots that reads pool configuration directly from config.toml, independent of the core erk config system:

```python
from pathlib import Path
from dataclasses import dataclass

DEFAULT_POOL_SIZE = 4

@dataclass(frozen=True)
class PoolConfig:
    """Pool configuration read directly from .erk/config.toml."""
    pool_size: int  # Never None; uses DEFAULT_POOL_SIZE as fallback
    pool_checkout_commands: list[str]  # For future use (not executed yet)
    pool_checkout_shell: str | None

def load_pool_config(repo_root: Path) -> PoolConfig:
    """Load pool configuration from .erk/config.toml.

    Returns PoolConfig with DEFAULT_POOL_SIZE as fallback if not configured.
    """
    # Parse [pool] and [pool.checkout] sections from .erk/config.toml
    # Returns PoolConfig with sensible defaults
```

This module will be responsible for reading pool config from the TOML file without depending on LoadedConfig.

### 2. Update erk_slots/common.py
**File:** `packages/erk-slots/src/erk_slots/common.py`

Update `get_pool_size()` to read from erk_slots' own config instead of `ctx.local_config`:

```python
def get_pool_size(ctx: ErkContext) -> int:
    """Get the configured pool size from erk_slots config.

    Reads from .erk/config.toml [pool] section if present,
    otherwise returns DEFAULT_POOL_SIZE.
    """
    pool_cfg = load_pool_config(ctx.repo_root)
    return pool_cfg.pool_size
```

### 3. Remove Pool Fields from LoadedConfig
**File:** `packages/erk-shared/src/erk_shared/context/types.py`

Remove these three fields from the `LoadedConfig` class:
- `pool_size: int | None`
- `pool_checkout_commands: list[str]`
- `pool_checkout_shell: str | None`

Also update the `test()` class method to remove parameters for these three fields.

### 4. Remove Pool Parsing from config.py
**File:** `src/erk/cli/config.py`

In `_parse_config_file()` function (~lines 68-79):
- Remove the `[pool]` section parsing (lines 69-72)
- Remove the `[pool.checkout]` section parsing (lines 74-79)
- Remove these arguments from the returned `LoadedConfig()` call (lines 111-114):
  - `pool_size=pool_size`
  - `pool_checkout_commands=pool_checkout_commands`
  - `pool_checkout_shell=pool_checkout_shell`

Do the same in `load_config()` and `load_local_config()` functions — remove these three fields from the default `LoadedConfig()` constructor calls.

### 5. Update merge_configs() and merge_configs_with_local()
**File:** `src/erk/cli/config.py`

In both functions:
- Remove the lines that handle pool_size, pool_checkout_commands, pool_checkout_shell
- Remove these fields from the returned `LoadedConfig()` constructor calls

For `merge_configs()` (~lines 306-320):
- Remove line 311 (`pool_size=repo_config.pool_size`)
- Remove lines 312-313 (`pool_checkout_commands`, `pool_checkout_shell`)

For `merge_configs_with_local()` (~lines 347-394):
- Remove lines 360-370 (pool_size, pool_checkout_commands, pool_checkout_shell merging logic)

### 6. Remove Pool from RepoConfigSchema
**File:** `packages/erk-shared/src/erk_shared/config/schema.py`

Remove the pool-related fields from the `RepoConfigSchema` class:
- `pool_max_slots: int | None`
- `pool_checkout_commands: list[str]`
- `pool_checkout_shell: str | None`

Also remove the pool section from the Pydantic validator if one exists.

### 7. Remove Pool Config Display Commands
**File:** `src/erk/cli/commands/config.py`

In `config_list()` function (~lines 263-271, 300-320):
- Remove the pool.max_slots, pool.checkout.shell, pool.checkout.commands display lines
- Remove the check for "no custom pool config"

In `config_get()` function (~line 382):
- Remove the `pool.max_slots` key handling

In `config_set()` function:
- Remove any handling for pool.* keys

Remove any pool-related imports at the top of the file if needed.

### 8. Update erk_slots/list_cmd.py
**File:** `packages/erk-slots/src/erk_slots/list_cmd.py`

Change the import on line 14 from:
```python
from erk_shared.slots.naming import DEFAULT_POOL_SIZE
```

to:
```python
from erk_slots.config import DEFAULT_POOL_SIZE
```

## Tests to Update

1. **New tests for `erk_slots/config.py`**:
   - Create `packages/erk-slots/tests/unit/test_config.py` to test `load_pool_config()` with various TOML configurations
   - Test that DEFAULT_POOL_SIZE is used as fallback when [pool] section is missing
   - Test merging of local and repo pool config if applicable

2. **`tests/unit/cli/test_project_config.py`** — Tests for pool config loading/merging (~lines 380-508, 587-690):
   - Delete test methods: `test_load_pool_size_from_file`, `test_load_pool_size_defaults_to_none`, `test_load_pool_checkout_commands`, `test_load_pool_checkout_shell`, `test_local_pool_size_overrides_base`, `test_pool_checkout_commands_concatenate`, `test_local_pool_checkout_shell_overrides_base`, and similar merge tests
   - These tests move to `packages/erk-slots/tests/unit/test_config.py`

3. **`tests/unit/cli/test_config_worktree.py`** — Tests for pool config in worktree context:
   - Delete tests that specifically validate pool_size is loaded from main_repo_root (pool config is now erk_slots' concern)

4. **`tests/commands/setup/test_config.py`** — Tests for `erk config list/get/set` commands (~lines 585, 616, 738, 769, 1106, 1144, 1545):
   - Delete or update tests that check for pool.max_slots, pool.checkout.shell, pool.checkout.commands in output (these keys no longer exist in core config)
   - Update any tests that use pool config in their setup

5. **`packages/erk-slots/tests/unit/test_assign_cmd.py`** and **`test_init_pool_cmd.py`**:
   - These tests use `LoadedConfig.test(pool_size=2)` — remove this parameter from the test setup
   - These tests should still pass because `get_pool_size()` behavior is unchanged (now reads from erk_slots.config instead of LoadedConfig)

6. **`packages/erk-shared/tests/unit/config/test_schema.py`**:
   - Remove tests that validate pool fields in the schema

7. **`tests/core/test_slot_allocation.py`**:
   - Tests for `get_pool_size()` should still pass because the function behavior doesn't change (it reads from erk_slots.config with DEFAULT_POOL_SIZE fallback)
   - Update imports: `DEFAULT_POOL_SIZE` should now be imported from `erk_slots.config` instead of `erk_shared.slots.naming`

## Implementation Order

1. Create new `erk_slots/config.py` module with `DEFAULT_POOL_SIZE` and `load_pool_config()`
2. Update `erk_slots/common.py:get_pool_size()` to call `load_pool_config()` instead of reading from `ctx.local_config`
3. Update imports in `erk_slots/list_cmd.py` to get `DEFAULT_POOL_SIZE` from erk_slots.config
4. Remove pool fields from LoadedConfig (erk_shared/context/types.py)
5. Remove pool field from RepoConfigSchema (erk_shared/config/schema.py)
6. Remove pool parsing from src/erk/cli/config.py (all functions)
7. Remove pool config commands from src/erk/cli/commands/config.py
8. Delete tests for pool config in core erk modules
9. Create tests for erk_slots.config module
10. Update remaining tests that reference LoadedConfig.test(pool_size=X)
11. Update any other imports of DEFAULT_POOL_SIZE
12. Run tests to verify no regressions

## Verification

After implementation:
- `uv run make fast_ci` — Ensure all fast tests pass
- `uv run make all_ci` — Ensure all tests pass including integration tests
- `erk config list` — Should not display pool.max_slots or pool.checkout.* anymore
- `erk slot init-pool --pool-size 8` — Should still work and respect configured pool_size
- Test with a config.toml that has `[pool] max_slots = 8` — should create 8 slots when init-pool is run
- Check that no code in `src/erk/` or `packages/erk-shared/` imports from `erk_slots` — the dependency should only go one way (erk_slots imports from erk)
- Verify that DEFAULT_POOL_SIZE is only defined in erk_slots/config.py and no longer in erk_shared
