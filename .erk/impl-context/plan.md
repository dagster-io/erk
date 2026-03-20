# Plan: Extract slot naming utilities to `erk-shared`

## Context

PR #9294 has a review comment on `checkout_helpers.py:209` flagging an inline import of `allocate_slot_for_branch` from `erk_slots.common` without documented justification. The function itself depends on erk types (`ErkContext`, `RepoContext`, `PoolState`) so it can't move to `erk-shared`. However, `erk_slots/common.py` contains pure utility functions (no erk dependencies) that can be extracted to `erk-shared/slot_naming.py`. This reduces cross-package coupling and is a stepping stone toward eventually moving all slot features to `erk-slots`.

## Changes

### 1. Create `packages/erk-shared/src/erk_shared/slots/` subpackage

Create `packages/erk-shared/src/erk_shared/slots/__init__.py` (empty).

Create `packages/erk-shared/src/erk_shared/slots/naming.py` with these pure functions/constants extracted from `erk_slots/common.py` (lines 29-104):

- `SLOT_NAME_PREFIX = "erk-slot"`
- `DEFAULT_POOL_SIZE = 4`
- `extract_slot_number(slot_name: str) -> str | None`
- `get_placeholder_branch_name(slot_name: str) -> str | None`
- `is_placeholder_branch(branch_name: str) -> bool`
- `generate_slot_name(slot_number: int) -> str`

Only dependency: `import re`. Pattern reference: `erk_shared/naming.py`.

### 2. Update `packages/erk-slots/src/erk_slots/common.py`

- Remove the 6 definitions above (lines 29-104)
- Remove `import re` (only used by `is_placeholder_branch`)
- Add import for internal use:
  ```python
  from erk_shared.slots.naming import (
      DEFAULT_POOL_SIZE,
      SLOT_NAME_PREFIX,
      extract_slot_number,
      generate_slot_name,
      get_placeholder_branch_name,
      is_placeholder_branch,
  )
  ```
  These are NOT re-exports — `common.py` calls them internally (e.g., `find_next_available_slot` calls `generate_slot_name`).

### 3. Update consumers in main `erk` package (5 files)

Switch to canonical `erk_shared.slots.naming` import path:

| File | Old import from `erk_slots.common` | New import from `erk_shared.slots.naming` |
|------|-------|-------|
| `src/erk/cli/commands/config.py` | `DEFAULT_POOL_SIZE` | `DEFAULT_POOL_SIZE` |
| `src/erk/cli/commands/land_cmd.py` | `extract_slot_number, get_placeholder_branch_name` (keep `find_branch_assignment` on `erk_slots.common`) | split into two imports |
| `src/erk/cli/commands/wt/list_cmd.py` | `is_placeholder_branch` | `is_placeholder_branch` |
| `src/erk/cli/commands/branch/list_cmd.py` | `is_placeholder_branch` | `is_placeholder_branch` |
| `src/erk/cli/commands/pr/dispatch_cmd.py` | `is_placeholder_branch` | `is_placeholder_branch` |

### 4. Update consumers in `erk-slots` package

Switch pure-utility imports to canonical path in:
- `erk_slots/init_pool_cmd.py` — `generate_slot_name`, `get_placeholder_branch_name`, `get_pool_size`, `is_slot_initialized` (only the first two move)
- `erk_slots/list_cmd.py` — `DEFAULT_POOL_SIZE`, `generate_slot_name`
- `erk_slots/unassign_cmd.py` — `get_placeholder_branch_name`
- `erk_slots/diagnostics.py` — `generate_slot_name`
- `erk_slots/checkout_cmd.py` — keep `allocate_slot_for_branch`, `find_current_slot_assignment`, `update_slot_assignment_tip` on `common`

### 5. Add justification comment in `checkout_helpers.py:209`

```python
# Inline: erk_slots.common depends on erk types (ErkContext, RepoContext,
# PoolState); module-level import creates circular dep through
# erk.cli.commands -> erk_slots -> erk.core.
from erk_slots.common import allocate_slot_for_branch
```

### 6. Move tests to `packages/erk-shared/tests/unit/slots/test_naming.py`

Create `packages/erk-shared/tests/unit/slots/__init__.py` (empty).

Move pure-utility tests from `packages/erk-slots/tests/unit/test_common.py` and update imports to `erk_shared.slots.naming`.

## Verification

1. `make fast-ci` — all lint/format/type/unit checks pass
2. Confirm no remaining imports of moved symbols from `erk_slots.common` in main `erk` package (grep)
