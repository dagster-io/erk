# Plan: Move CodespaceRegistry Gateway to gateway/

Part of **Objective #5930**, Step 8.1-8.3

## Overview

Consolidate CodespaceRegistry into `erk_shared/gateway/codespace_registry/` following the established gateway pattern from prior phases.

## Current State

**ABC + types location:**

- `packages/erk-shared/src/erk_shared/core/codespace_registry.py` (ABC + RegisteredCodespace dataclass)

**Implementations location:**

- `src/erk/core/codespace/registry_real.py` (RealCodespaceRegistry + standalone mutation functions)
- `src/erk/core/codespace/registry_fake.py` (FakeCodespaceRegistry)
- `src/erk/core/codespace/registry_abc.py` (re-export shim)
- `src/erk/core/codespace/types.py` (re-export shim)

**Note:** `erk_shared/gateway/codespace/` already exists for a different gateway (SSH execution). Use `codespace_registry/` to avoid conflict.

## Target Structure

```
packages/erk-shared/src/erk_shared/gateway/codespace_registry/
├── __init__.py          # Docstring only (pattern from github_admin)
├── abc.py               # CodespaceRegistry ABC + RegisteredCodespace
├── real.py              # RealCodespaceRegistry + mutation functions
└── fake.py              # FakeCodespaceRegistry
```

## Import Sites (20 files)

From `rg "from erk_shared\.core\.codespace_registry|from erk\.core\.codespace"`:

| Category     | Files                                                                                                                     |
| ------------ | ------------------------------------------------------------------------------------------------------------------------- |
| Core context | `src/erk/core/context.py`, `packages/erk-shared/src/erk_shared/context/context.py`                                        |
| CLI commands | `src/erk/cli/commands/codespace/*.py`, `src/erk/cli/commands/codespace_executor.py`                                       |
| Tests        | `tests/unit/cli/commands/codespace/*.py`, `tests/unit/core/codespace/*.py`, `tests/commands/implement/test_issue_mode.py` |
| Fakes        | `packages/erk-shared/src/erk_shared/core/fakes.py`                                                                        |

## Implementation Steps

### Step 1: Create gateway/codespace_registry/ directory structure

Create new directory with files:

- `__init__.py` - docstring only
- `abc.py` - move ABC + RegisteredCodespace from `erk_shared/core/codespace_registry.py`
- `real.py` - move from `src/erk/core/codespace/registry_real.py`
- `fake.py` - move from `src/erk/core/codespace/registry_fake.py`

### Step 2: Update imports in moved files

In `real.py`:

```python
# OLD
from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace

# NEW
from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry, RegisteredCodespace
```

In `fake.py`:

```python
# OLD
from erk.core.codespace.registry_abc import CodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace

# NEW
from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry, RegisteredCodespace
```

### Step 3: Update ALL import sites

**Pattern for each file:**

```python
# OLD patterns
from erk_shared.core.codespace_registry import CodespaceRegistry, RegisteredCodespace
from erk.core.codespace.registry_real import RealCodespaceRegistry, register_codespace, ...
from erk.core.codespace.registry_fake import FakeCodespaceRegistry

# NEW patterns
from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry, RegisteredCodespace
from erk_shared.gateway.codespace_registry.real import RealCodespaceRegistry, register_codespace, ...
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry
```

### Step 4: Delete old locations

- Delete `packages/erk-shared/src/erk_shared/core/codespace_registry.py`
- Delete `src/erk/core/codespace/` directory entirely (registry_abc.py, registry_real.py, registry_fake.py, types.py, **init**.py)

### Step 5: Update erk_shared/core/fakes.py

Update the FakeCodespaceRegistry import in the fakes module:

```python
# OLD
from erk_shared.core.codespace_registry import CodespaceRegistry

# NEW
from erk_shared.gateway.codespace_registry.abc import CodespaceRegistry
```

## Files to Modify

**Create (4 files):**

- `packages/erk-shared/src/erk_shared/gateway/codespace_registry/__init__.py`
- `packages/erk-shared/src/erk_shared/gateway/codespace_registry/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/codespace_registry/real.py`
- `packages/erk-shared/src/erk_shared/gateway/codespace_registry/fake.py`

**Delete (5 files):**

- `packages/erk-shared/src/erk_shared/core/codespace_registry.py`
- `src/erk/core/codespace/__init__.py`
- `src/erk/core/codespace/registry_abc.py`
- `src/erk/core/codespace/registry_real.py`
- `src/erk/core/codespace/registry_fake.py`
- `src/erk/core/codespace/types.py`

**Update imports (~20 files):**

- `src/erk/core/context.py`
- `packages/erk-shared/src/erk_shared/context/context.py`
- `packages/erk-shared/src/erk_shared/core/fakes.py`
- `src/erk/cli/commands/codespace_executor.py`
- `src/erk/cli/commands/codespace/setup_cmd.py`
- `src/erk/cli/commands/codespace/remove_cmd.py`
- `src/erk/cli/commands/codespace/set_default_cmd.py`
- `tests/unit/cli/commands/codespace/test_setup_cmd.py`
- `tests/unit/cli/commands/codespace/test_connect_cmd.py`
- `tests/unit/cli/commands/codespace/test_list_cmd.py`
- `tests/unit/cli/commands/codespace/test_remove_cmd.py`
- `tests/unit/cli/commands/codespace/test_set_default_cmd.py`
- `tests/unit/cli/commands/test_codespace_executor.py`
- `tests/unit/core/codespace/test_registry_real.py`
- `tests/unit/core/codespace/test_registry_fake.py`
- `tests/commands/implement/test_issue_mode.py`

## Verification

1. **Import check:** Verify no imports from old locations

   ```bash
   rg "from erk_shared\.core\.codespace_registry" --type py
   rg "from erk\.core\.codespace" --type py
   ```

   Both should return empty.

2. **Run CI:** `make all-ci` passes

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Reference: `docs/learned/architecture/gateway-abc-implementation.md`
