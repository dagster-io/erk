---
title: Slot Pool State Sync
read_when:
  - "modifying slot pool allocation or assignment logic"
  - "debugging branch mismatches in pool slots"
  - "understanding how manual git operations interact with the pool"
tripwires:
  - action: "calling allocate_slot_for_branch without sync_pool_assignments running first"
    warning: "Pool sync must run BEFORE find_branch_assignment call. Without it, stale pool.json entries cause silent misassignment — a slot may appear free when it's actually occupied by a different branch."
    score: 9
---

# Slot Pool State Sync

The pool sync algorithm reconciles `pool.json` assignments with actual git worktree branch state. It runs lazily — only before allocation decisions — and skips disk writes when no changes are detected.

## Why Sync Exists

Users may run `gt create` or `git checkout` directly inside a pool slot worktree, causing the recorded branch in `pool.json` to diverge from the actual branch. Without sync, the pool would make allocation decisions based on stale data: a slot might appear assigned to branch A when it's actually on branch B.

## Sync Timing

<!-- Source: src/erk/cli/commands/slot/common.py:609, allocate_slot_for_branch -->

`sync_pool_assignments()` is called at the beginning of `allocate_slot_for_branch()` (line 609 in `common.py`), before any allocation decisions. This ensures the pool state reflects reality before checking if a branch is already assigned or if slots are available.

## Algorithm

<!-- Source: src/erk/cli/commands/slot/common.py:223-287, sync_pool_assignments -->

For each assignment in `pool.json`:

1. **Missing worktree directory** — skip, leave unchanged
2. **Detached HEAD** — skip, leave unchanged (user may be mid-operation)
3. **Branch matches recorded** — skip, no correction needed
4. **Placeholder branch** (`__erk-slot-NN-br-stub__`) — skip, don't update to stub name
5. **Branch actually changed** — update `branch_name`, preserve original `assigned_at`

The `assigned_at` timestamp is deliberately preserved when a branch changes. It tracks when the slot was originally assigned, not when the branch changed. This ordering is used for LRU eviction decisions.

## I/O Optimization: mtime Preservation

If no assignments were corrected (`synced_count == 0`), the function returns early without calling `save_pool_state()`. This avoids unnecessary disk writes and preserves the file's modification time, which matters for tools that watch `pool.json` for changes.

When `synced_count == 0`, the function returns early with the original state, skipping `save_pool_state()` entirely. Only when at least one assignment was corrected does the function write the updated state to disk. See `sync_pool_assignments()` in [`common.py`](../../../src/erk/cli/commands/slot/common.py) for the implementation.

## State-of-Truth Hierarchy

1. **Git worktree state** (actual branches checked out) — primary source
2. **pool.json assignments** (recorded state) — secondary
3. **Sync** reconciles them by reading git and updating pool.json

The pool never overrides git state. It only updates its own records to match what git reports.

## Key Source Files

- [`src/erk/cli/commands/slot/common.py`](../../../src/erk/cli/commands/slot/common.py) — `sync_pool_assignments()` (lines 223-287), called from `allocate_slot_for_branch()` (line 609)
- [`src/erk/core/worktree_pool.py`](../../../src/erk/core/worktree_pool.py) — `PoolState`, `SlotAssignment`, `PoolSyncResult` data structures
- [`tests/unit/cli/commands/slot/test_common.py`](../../../tests/unit/cli/commands/slot/test_common.py) — sync tests (lines 644-890)

## Related Topics

- [Slot Pool Architecture](../erk/slot-pool-architecture.md) — Overall pool design, allocation algorithm, diagnostics
