# Plan: Skip Dirty Slots in find_inactive_slot()

## Problem

`find_inactive_slot()` selects the first unassigned slot without checking for uncommitted changes. The uncommitted changes check happens AFTER slot selection, causing unnecessary errors when clean slots are available.

**Current sequence:**
```
Select slot → Check if clean → Fail if dirty
```

**Better sequence:**
```
Select from CLEAN slots only → Then checkout
```

## Solution

Modify `find_inactive_slot()` to check `git.has_uncommitted_changes()` for each candidate slot and skip dirty ones.

## Files to Modify

### 1. `src/erk/cli/commands/slot/common.py`

Update `find_inactive_slot()` (lines 124-163):

```python
def find_inactive_slot(
    state: PoolState,
    git: Git,
    repo_root: Path,
) -> tuple[str, Path] | None:
    """Find an available managed slot for reuse.

    Searches for worktrees that exist but are not assigned.
    Uses git as source of truth for which worktrees exist.
    Prefers slots in order (lowest slot number first).
    Skips slots with uncommitted changes.
    ...
    """
    assigned_slots = {a.slot_name for a in state.assignments}
    worktrees = git.list_worktrees(repo_root)

    managed_worktrees: dict[str, Path] = {}
    for wt in worktrees:
        slot_name = wt.path.name
        if extract_slot_number(slot_name) is not None:
            managed_worktrees[slot_name] = wt.path

    for slot_num in range(1, state.pool_size + 1):
        slot_name = generate_slot_name(slot_num)
        if slot_name in managed_worktrees and slot_name not in assigned_slots:
            wt_path = managed_worktrees[slot_name]
            # Skip slots with uncommitted changes
            if git.has_uncommitted_changes(wt_path):
                continue
            return (slot_name, wt_path)

    return None
```

### 2. `tests/unit/cli/commands/slot/test_common.py`

Add test to `TestFindInactiveSlot`:

```python
def test_skips_slot_with_uncommitted_changes(self, tmp_path: Path) -> None:
    """Skips slots with uncommitted changes, returns next clean slot."""
    repo_root = tmp_path / "repo"
    wt1_path = tmp_path / "worktrees" / "erk-managed-wt-01"
    wt2_path = tmp_path / "worktrees" / "erk-managed-wt-02"
    git = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=wt1_path, branch="feature-a"),
                WorktreeInfo(path=wt2_path, branch="feature-b"),
            ]
        },
        # Slot 1 has uncommitted changes
        file_statuses={wt1_path: ([], ["dirty.py"], [])},
    )
    state = PoolState.test(pool_size=4)

    result = find_inactive_slot(state, git, repo_root)

    # Should skip dirty slot 1 and return clean slot 2
    assert result is not None
    slot_name, worktree_path = result
    assert slot_name == "erk-managed-wt-02"
    assert worktree_path == wt2_path
```

Add test for all-dirty case:

```python
def test_returns_none_when_all_slots_dirty(self, tmp_path: Path) -> None:
    """Returns None when all available slots have uncommitted changes."""
    repo_root = tmp_path / "repo"
    wt1_path = tmp_path / "worktrees" / "erk-managed-wt-01"
    git = FakeGit(
        worktrees={
            repo_root: [
                WorktreeInfo(path=wt1_path, branch="feature-a"),
            ]
        },
        file_statuses={wt1_path: ([], ["dirty.py"], [])},
    )
    state = PoolState.test(pool_size=4)

    result = find_inactive_slot(state, git, repo_root)

    assert result is None
```

## Impact

- When a dirty unassigned slot exists alongside clean slots, the clean slot is selected
- When ALL unassigned slots are dirty, `find_inactive_slot()` returns None, causing the code to fall through to `find_next_available_slot()` which creates a new slot
- If no new slots available (pool full), the existing error path handles it

## Verification

Run tests:
```
uv run pytest tests/unit/cli/commands/slot/test_common.py -v
uv run pytest tests/commands/implement/test_pool_slots.py -v
```