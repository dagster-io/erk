---
title: erk_slots Package Overview
read_when:
  - "working with slot commands (assign, checkout, goto, up, down, teleport)"
  - "adding navigation commands to erk slot"
  - "understanding pool config loading"
  - "working with worktree pool slot allocation"
tripwires:
  - action: "reading pool config from LoadedConfig"
    warning: "Pool config is no longer in LoadedConfig. Use erk_slots.config.load_pool_config(repo_root) directly. See pool-config-decoupling.md."
  - action: "adding a navigation command to src/erk/cli/ instead of packages/erk-slots/"
    warning: "Navigation commands (up, down, goto, teleport) live in packages/erk-slots/src/erk_slots/. Core navigation orchestration is in erk_slots/navigation.py; shared utilities are in src/erk/cli/commands/navigation_helpers.py."
---

# erk_slots Package Overview

The `erk_slots` package (`packages/erk-slots/`) is a self-contained package for slot/pool management. It owns all slot commands and pool allocation logic.

## Module Breakdown

| Module             | Purpose                                                  |
| ------------------ | -------------------------------------------------------- |
| `group.py`         | Click group registering all slot subcommands             |
| `common.py`        | Core allocation utilities and `SlotAllocationResult`     |
| `config.py`        | Pool config loading (independent of LoadedConfig)        |
| `assign_cmd.py`    | `erk slot assign` — assign a branch to a slot            |
| `checkout_cmd.py`  | `erk slot checkout` — checkout a branch in a slot        |
| `goto_cmd.py`      | `erk slot goto` — navigate to a specific slot            |
| `unassign_cmd.py`  | `erk slot unassign` — free a slot assignment             |
| `init_pool_cmd.py` | `erk slot init-pool` — initialize the slot pool          |
| `list_cmd.py`      | `erk slot list` — list current slot assignments          |
| `repair_cmd.py`    | `erk slot repair` — repair inconsistent pool state       |
| `diagnostics.py`   | Diagnostic utilities for pool state inspection           |
| `navigation.py`    | Navigation orchestration for `up/down` commands          |
| `teleport_cmd.py`  | `erk slot teleport` — force-reset local branch to remote |
| `up_cmd.py`        | `erk slot up` — navigate up the stack                    |
| `down_cmd.py`      | `erk slot down` — navigate down the stack                |

## Key Functions in common.py

| Function                     | Purpose                                                                 |
| ---------------------------- | ----------------------------------------------------------------------- |
| `allocate_slot_for_branch()` | Find or create a slot for a branch; returns `SlotAllocationResult`      |
| `find_inactive_slot()`       | Find a slot that has no active branch assignment                        |
| `find_next_available_slot()` | Find a slot number not assigned and with no existing worktree directory |
| `sync_pool_assignments()`    | Reconcile pool state with actual worktree state on disk                 |

## Navigation Command Split

Navigation logic is split between two locations:

- **Orchestration**: `packages/erk-slots/src/erk_slots/navigation.py` — `execute_stack_navigation()` handles the up/down flow (N steps, --delete-current, worktree creation)
- **Shared utilities**: `src/erk/cli/commands/navigation_helpers.py` — `activate_target()`, `find_assignment_by_worktree_path()`, `validate_for_deletion()` — shared with non-slot navigation paths

## Config Independence

Pool config is loaded via `erk_slots.config.load_pool_config()`, not through `LoadedConfig`. This makes the slots package self-contained:

```python
from erk_slots.config import load_pool_config

pool_cfg = load_pool_config(repo_root)
pool_size = pool_cfg.pool_size  # Falls back to DEFAULT_POOL_SIZE = 4
```

Fields: `pool_size`, `pool_checkout_commands`, `pool_checkout_shell`

## Related Documentation

- [Pool Config Decoupling](pool-config-decoupling.md) — Why pool config moved out of LoadedConfig
- [Action Plan Pattern](../architecture/action-plan-pattern.md) — Used by teleport_cmd.py's dry-run support
