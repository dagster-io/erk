# Plan: Lazy Tip Sync for Worktree Pool

**Part of Objective #7709, Nodes 3.1 and 3.2**

## Context

When users manually run `gt create` or `git checkout` in a pool slot, the actual branch changes but `pool.json` still records the old branch. This causes stale state and incorrect eviction decisions — `find_inactive_slot()` may evict a slot that's actively in use because it doesn't know the branch changed.

Design decision 4 from the objective: "Lazy tip sync: The slot reflects whatever `git branch --show-current` returns. `pool.json` is a cache that re-syncs on any `erk wt` operation."

## Approach

Add a `sync_pool_assignments` function that checks actual git branches for each assignment and updates `pool.json` when mismatches are detected. Integrate it into `allocate_slot_for_branch` (the critical path for allocation/eviction decisions).

## Changes

### 1. Add `PoolSyncResult` and `sync_pool_assignments` to `src/erk/cli/commands/slot/common.py`

New frozen dataclass and function, placed after `find_branch_assignment` (~line 213):

```python
@dataclass(frozen=True)
class PoolSyncResult:
    """Result of syncing pool assignments with actual git state."""
    state: PoolState
    synced_count: int

def sync_pool_assignments(
    state: PoolState,
    git: Git,
    pool_json_path: Path,
) -> PoolSyncResult:
```

**Logic**: For each assignment:
- Skip if `worktree_path` doesn't exist (handled by other repair logic)
- Call `git.branch.get_current_branch(assignment.worktree_path)`
- Skip if detached HEAD (`None`) or branch matches
- Skip if actual branch is a placeholder (`is_placeholder_branch`)
- Otherwise: create updated assignment with new `branch_name`, preserve original `assigned_at`
- Save to disk only if `synced_count > 0`

### 2. Integrate sync into `allocate_slot_for_branch` in `src/erk/cli/commands/slot/common.py`

After loading pool state (line ~524) and before the allocation logic, add:

```python
sync_result = sync_pool_assignments(state, ctx.git, repo.pool_json_path)
state = sync_result.state
```

This ensures `find_branch_assignment` and `find_inactive_slot` both operate on accurate state, fixing the eviction bug (Node 3.2).

### 3. Add tests to `tests/unit/cli/commands/slot/test_common.py`

New test functions (plain functions, not class — these test a standalone function):

| Test | Verifies |
|------|----------|
| `test_sync_no_changes_when_branches_match` | Returns same state, synced_count=0 |
| `test_sync_updates_when_branch_changed` | Updates branch_name, preserves assigned_at |
| `test_sync_saves_to_disk_on_change` | pool.json updated after sync |
| `test_sync_does_not_save_when_unchanged` | pool.json mtime unchanged |
| `test_sync_skips_missing_worktree_path` | Non-existent paths left alone |
| `test_sync_skips_detached_head` | None branch left alone |
| `test_sync_skips_placeholder_branch` | Placeholder branches left alone |
| `test_sync_multiple_assignments` | Syncs changed, preserves unchanged |
| `test_eviction_uses_synced_state` | End-to-end: sync + find_inactive_slot avoids evicting active slot |

### Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/slot/common.py` | Add `PoolSyncResult`, `sync_pool_assignments`; integrate into `allocate_slot_for_branch` |
| `tests/unit/cli/commands/slot/test_common.py` | Add 9 test functions |

### Files NOT Modified (and why)

- `src/erk/core/worktree_pool.py` — pure data layer, no Git dependency
- `src/erk/cli/commands/wt/list_cmd.py` — already reads git directly, doesn't use pool.json
- `src/erk/cli/commands/slot/list_cmd.py` — serves as diagnostic tool showing mismatches; auto-sync would hide them

## Verification

1. Run `pytest tests/unit/cli/commands/slot/test_common.py` — all new tests pass
2. Run `make fast-ci` — no regressions
3. Manual scenario: manually `gt create` in a slot, then `erk br create --for-plan <plan>` should not evict the manually-changed slot
