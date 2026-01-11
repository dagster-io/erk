---
title: Slot Pool Architecture
read_when:
  - "understanding slot pool design"
  - "implementing slot-related features"
  - "debugging slot assignment issues"
---

# Slot Pool Architecture

The worktree slot pool is a reusable pool of pre-allocated git worktrees for fast branch switching. Instead of creating and destroying worktrees on demand, erk maintains a fixed-size pool of worktree directories that can be reassigned to different branches.

## Core Concepts

### Pool Basics

- **Pool size**: Default 4 slots, configurable via `local_config.pool_size`
- **Slot names**: `erk-slot-NN` format (e.g., `erk-slot-01`, `erk-slot-02`)
- **Placeholder branches**: `__erk-slot-NN-br-stub__` for unassigned slots
- **Pool persistence**: `~/.erk/repos/{repo_name}/pool.json`

### Why a Pool?

Creating git worktrees is relatively slow (file system operations, git setup). The pool enables:

1. **Fast branch switching**: Reuse existing worktrees instead of creating new ones
2. **Resource bounds**: Limit disk usage to a fixed number of worktrees
3. **Automatic eviction**: LRU eviction when pool is full

## Data Structures

### PoolState (`src/erk/core/worktree_pool.py`)

The top-level state container:

```python
@dataclass(frozen=True)
class PoolState:
    version: str                          # Schema version (currently "1.0")
    pool_size: int                        # Maximum slots in pool
    slots: tuple[SlotInfo, ...]           # Initialized slot metadata
    assignments: tuple[SlotAssignment, ...]  # Current branch-to-slot mappings
```

### SlotInfo

Metadata for an initialized slot:

```python
@dataclass(frozen=True)
class SlotInfo:
    name: str                      # e.g., "erk-slot-01"
    last_objective_issue: int | None  # For objective tracking continuity
```

### SlotAssignment

An active mapping of a branch to a slot:

```python
@dataclass(frozen=True)
class SlotAssignment:
    slot_name: str        # e.g., "erk-slot-01"
    branch_name: str      # The git branch assigned
    assigned_at: str      # ISO timestamp for LRU ordering
    worktree_path: Path   # Filesystem path to worktree
```

## Slot Allocation Algorithm

The `allocate_slot_for_branch()` function in `src/erk/cli/commands/slot/common.py` implements the unified allocation strategy:

### Step 1: Check Existing Assignment

If the branch is already assigned to a slot, return that assignment immediately (idempotent).

### Step 2: Fast Path - Reuse Inactive Slot

`find_inactive_slot()` searches for worktrees that:

- Exist in git's worktree registry
- Are not currently assigned to any branch

This is the fast path because it reuses an existing worktree directory.

### Step 3: Slow Path - Create New Slot

`find_next_available_slot()` finds a slot number that:

- Is within pool_size bounds
- Is not assigned to a branch
- Is not already initialized as a worktree
- Does not have an orphaned directory on disk

### Step 4: Pool Full - Eviction

If no slots are available, `handle_pool_full_interactive()` handles eviction:

- **With `--force`**: Auto-evict oldest assignment (by `assigned_at` timestamp)
- **Interactive (TTY)**: Prompt user to confirm eviction
- **Non-interactive**: Error with instructions

## Naming Conventions

| Component           | Pattern                   | Example                          |
| ------------------- | ------------------------- | -------------------------------- |
| Slot name           | `erk-slot-NN`             | `erk-slot-01`                    |
| Placeholder branch  | `__erk-slot-NN-br-stub__` | `__erk-slot-01-br-stub__`        |
| Pool state file     | `pool.json`               | `~/.erk/repos/my-repo/pool.json` |
| Worktrees directory | `{repo}/.worktrees/`      | `/path/to/repo/.worktrees/`      |

## Artifact Cleanup

When reusing a slot, `cleanup_worktree_artifacts()` removes stale data:

- `.impl/` - Previous implementation plans
- `.erk/scratch/` - Session-specific scratch data

These directories are in `.gitignore` so they persist across branch switches without cleanup.

## Diagnostics & Repair

### Sync Issues (`src/erk/cli/commands/slot/diagnostics.py`)

The diagnostic system detects inconsistencies between:

- Pool state (`pool.json`)
- Git worktree registry (`git worktree list`)
- Filesystem directories

| Issue Code             | Description                                      |
| ---------------------- | ------------------------------------------------ |
| `orphan-state`         | Assignment exists but worktree directory missing |
| `orphan-dir`           | Directory exists but not in pool state           |
| `missing-branch`       | Assigned branch no longer exists in git          |
| `branch-mismatch`      | Worktree on different branch than pool says      |
| `git-registry-missing` | Pool assignment not in git worktree registry     |
| `untracked-worktree`   | Git worktree exists but not erk-managed          |

### Repair (`src/erk/cli/commands/slot/repair_cmd.py`)

`erk slot repair` auto-fixes by removing stale assignments:

- `orphan-state` - Remove assignment (worktree gone)
- `missing-branch` - Remove assignment (branch deleted)
- `branch-mismatch` - Remove assignment (let user re-assign)
- `git-registry-missing` - Remove assignment (not a valid worktree)

## Entry Points

Commands that allocate slots via `allocate_slot_for_branch()`:

| Command             | Description                             |
| ------------------- | --------------------------------------- |
| `erk branch create` | Creates branch and assigns to slot      |
| `erk slot assign`   | Assigns existing branch to slot         |
| `erk implement`     | Assigns branch for issue implementation |
| `erk pr checkout`   | Assigns branch when checking out PR     |

## Configuration

In `.erk/config.toml` (local config):

```toml
pool_size = 6  # Override default of 4
```

## Key Source Files

- [`src/erk/core/worktree_pool.py`](../../../src/erk/core/worktree_pool.py) - Data structures and persistence
- [`src/erk/cli/commands/slot/common.py`](../../../src/erk/cli/commands/slot/common.py) - Allocation algorithm
- [`src/erk/cli/commands/slot/diagnostics.py`](../../../src/erk/cli/commands/slot/diagnostics.py) - Health checks
- [`src/erk/cli/commands/slot/repair_cmd.py`](../../../src/erk/cli/commands/slot/repair_cmd.py) - Auto-repair

## Related Topics

- [Branch Cleanup](branch-cleanup.md) - Cleaning up branches and worktrees
- Load `gt-graphite` skill for worktree stack mental model
