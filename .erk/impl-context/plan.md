# Fix: `find_inactive_slot` fails to reuse slots due to untracked files

## Context

`erk br co --for-plan 8681 --script` allocated a brand new slot (erk-slot-62) instead of reusing one of ~25 unassigned existing slots. The `reuse_inactive_slots=True` path in `allocate_slot_for_branch` calls `find_inactive_slot`, which should find an unassigned worktree to reuse. Instead it returns None for all of them, causing fallthrough to `find_next_available_slot` which creates slot 62.

**Root cause:** `find_inactive_slot` (common.py:180) calls `git.status.has_uncommitted_changes(wt_path)` to skip dirty slots. This method uses `git status --porcelain` and returns True for ANY output including untracked files. Every slot worktree has `.erk/bin/` as untracked (`?? .erk/bin/`), so ALL unassigned slots are skipped.

Untracked files are irrelevant for branch switching safety — git leaves them untouched. Only staged/modified tracked files matter.

## Fix

### 1. Change `find_inactive_slot` to ignore untracked files

**File:** `src/erk/cli/commands/slot/common.py`, line 180

Replace:
```python
if git.status.has_uncommitted_changes(wt_path):
    continue
```
With:
```python
staged, modified, _untracked = git.status.get_file_status(wt_path)
if staged or modified:
    continue
```

`get_file_status` already exists on the StatusOps ABC and all implementations. No gateway changes needed.

### 2. Add tests

**File:** `tests/unit/cli/commands/slot/test_common.py` — add to `TestFindInactiveSlot` class:

- `test_reuses_slot_with_only_untracked_files` — slot with only untracked files (e.g. `.erk/bin/`) should be reused
- `test_skips_slot_with_staged_changes_and_untracked` — slot with staged+untracked should still be skipped; next slot with only untracked should be returned

### Why not change `has_uncommitted_changes`

All other callers (unassign, land, submit, navigation, etc.) correctly want to detect untracked files. Only `find_inactive_slot` has the "can I safely switch branches?" semantic where untracked files are irrelevant.

## Verification

- Run `pytest tests/unit/cli/commands/slot/test_common.py` — existing tests pass, new tests pass
- Run fast-ci
