# Fix: sync_pool_assignments doesn't clean up stale slot assignments

## Context

The worktree pool has 64 slots with 62 assignments, but **37 are stale** — the assigned branch no longer exists. Worktrees exist but are on placeholder branches or in detached HEAD state. This happens because `sync_pool_assignments()` (which runs before every allocation) preserves assignments even when the slot is clearly freed. Users must manually run `erk slot repair` to reclaim slots, and nobody does.

**Root cause:** Three cases in `sync_pool_assignments()` where stale assignments are preserved:
1. Worktree path doesn't exist → keeps assignment (line 250-251)
2. Worktree on placeholder branch → keeps assignment (line 265-267)
3. Worktree in detached HEAD with deleted branch → keeps assignment (line 256-259)

## Plan

### 1. Add `removed_count` to `PoolSyncResult`

**File:** `src/erk/cli/commands/slot/common.py:218-223`

Add `removed_count: int` field to distinguish removals from branch-sync updates.

### 2. Add `repo_root` parameter to `sync_pool_assignments`

**File:** `src/erk/cli/commands/slot/common.py:226-230`

New signature adds `repo_root: Path` (needed for `get_all_branch_heads` batch call).

### 3. Rewrite the assignment-processing loop

**File:** `src/erk/cli/commands/slot/common.py:246-278`

Call `git.branch.get_all_branch_heads(repo_root)` once at the top (single `git for-each-ref` call, already exists in ABC/real/fake). Then for each assignment:

1. **Worktree path doesn't exist** → remove, warn via `user_output`
2. **Assigned branch not in `all_heads`** → remove, warn
3. **Detached HEAD + branch exists** → keep (legitimate mid-rebase)
4. **Placeholder branch** → remove, warn (slot was freed by `erk land`)
5. **Actual == assigned** → keep
6. **Branch changed** → update assignment to actual branch

Track `removed_count` and `synced_count` separately. Save to disk if either > 0.

Warning format (matches existing pattern from `_validate_existing_assignment`):
```
⚠ Removing stale assignment for 'branch-name' in erk-slot-XX (reason)
```

### 4. Update the sole caller

**File:** `src/erk/cli/commands/slot/common.py:612`

```python
# Before:
sync_result = sync_pool_assignments(state, ctx.git, repo.pool_json_path)
# After:
sync_result = sync_pool_assignments(state, ctx.git, repo.pool_json_path, repo.root)
```

### 5. Update tests

**File:** `tests/unit/cli/commands/slot/test_common.py`

**Update 3 existing tests** to assert removal instead of preservation:
- `test_sync_skips_missing_worktree_path` → rename to `test_sync_removes_when_worktree_missing`, assert `removed_count == 1` and assignment removed
- `test_sync_skips_placeholder_branch` → rename to `test_sync_removes_on_placeholder_branch`, assert `removed_count == 1`
- `test_sync_skips_detached_head` → split into two:
  - `test_sync_preserves_on_detached_head_with_existing_branch` (branch in `branch_heads`)
  - `test_sync_removes_on_detached_head_with_deleted_branch` (branch not in `branch_heads`)

**Add ~3 new tests:**
- `test_sync_removes_when_branch_deleted_worktree_exists` — worktree on a different branch but assigned branch deleted
- `test_sync_saves_to_disk_on_removal` — verify pool.json updated on removals
- `test_sync_handles_mixed_removals_and_syncs` — multiple assignments with both outcomes

**Update all ~10 existing sync test calls** to pass `repo_root` as 4th arg (use `tmp_path / "repo"`).

**Existing utilities needed (no changes):**
- `FakeGit` already supports `branch_heads` dict → `tests/fakes/gateway/git.py:124`
- `FakeGitBranchOps.get_all_branch_heads()` → `tests/fakes/gateway/git_branch_ops.py:332`

## Verification

1. Run `pytest tests/unit/cli/commands/slot/test_common.py -x` — all sync tests pass
2. Run `erk slot repair --dry-run` on the actual pool — should report 0 repairable issues (sync would have already cleaned them)
3. Run full CI: `make fast-ci`
