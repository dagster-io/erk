# Fix: `update_local_ref` corrupts index when branch is checked out

## Context

After `erk land` (run via `/erk:land` automation), the root worktree ends up with staged changes that would **reverse** the just-landed commit. For example, after landing PR #8825 (which adds `module-to-subpackage/SKILL.md`), `git status` shows that file as deleted.

**Root cause chain:**

1. `/erk:land` runs `erk land <PR_NUMBER> --force` from the root worktree
2. The PR's branch lives in a slot worktree, so `is_current_branch=False`
3. Since `is_current_branch=False`, `_navigate_or_exit` skips the pull — local master ref stays at the old commit, but the index is clean (matches old master)
4. Later, `erk pr dispatch` calls `ensure_trunk_synced()` which detects local master is behind origin/master
5. `ensure_trunk_synced` calls `update_local_ref()` which runs `git update-ref refs/heads/master <new_sha>` — this advances the branch pointer **without updating the index or working tree**
6. Now HEAD points to the new commit but index/working tree reflect the old commit → dirty index with reverse changes

**The bug is in `ensure_trunk_synced`** (`dispatch_helpers.py:61`). It uses `update_local_ref` even when trunk is checked out in a worktree. The `_check_trunk_worktree_clean` guard only verifies no uncommitted changes exist — it doesn't prevent the ref-only update from desynchronizing HEAD from the index.

## Fix

**File:** `src/erk/cli/commands/pr/dispatch_helpers.py`

Change `ensure_trunk_synced` so that when trunk IS checked out in a worktree, it uses `git pull --ff-only` (which properly updates HEAD + index + working tree) instead of `update_local_ref` (which only updates the ref).

```python
def ensure_trunk_synced(ctx: ErkContext, repo: RepoContext) -> None:
    trunk = ctx.git.branch.detect_trunk_branch(repo.root)
    ctx.git.remote.fetch_branch(repo.root, "origin", trunk)

    local_sha = ctx.git.branch.get_branch_head(repo.root, trunk)
    remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{trunk}")

    if remote_sha is None:
        # ... existing error handling ...

    if local_sha == remote_sha:
        return  # Already synced

    merge_base = ctx.git.analysis.get_merge_base(repo.root, trunk, f"origin/{trunk}")

    if merge_base == local_sha:
        # Local is behind remote - safe to fast-forward
        trunk_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, trunk)

        if trunk_worktree is not None:
            # Trunk is checked out — must use pull to update index + working tree
            _check_trunk_worktree_clean(ctx, repo, trunk=trunk)
            user_output(f"Syncing {trunk} with origin/{trunk}...")
            ctx.git.remote.pull_branch(trunk_worktree, "origin", trunk, ff_only=True)
        else:
            # Trunk not checked out — safe to update ref directly
            user_output(f"Syncing {trunk} with origin/{trunk}...")
            ctx.git.branch.update_local_ref(repo.root, trunk, remote_sha)

        user_output(click.style("✓", fg="green") + f" {trunk} synced with origin/{trunk}")
    elif merge_base == remote_sha:
        # ... existing error handling ...
    else:
        # ... existing error handling ...
```

Key change: `find_worktree_for_branch` is already used in `_check_trunk_worktree_clean` — we reuse that pattern to branch the logic. When checked out, use `pull_branch` with `cwd=trunk_worktree` (not `repo.root`, since they may differ). When not checked out, keep the existing `update_local_ref` path.

**Test:** `tests/unit/cli/commands/pr/test_dispatch_helpers.py` (or wherever `ensure_trunk_synced` is tested)

Add a test case: trunk checked out in root worktree, local behind remote → verify index is updated (not just the ref). The existing `_check_trunk_worktree_clean` test infrastructure should provide patterns.

## Verification

1. Run existing tests for dispatch_helpers
2. Manual test: land a PR from a slot worktree, then run `erk pr dispatch` — verify root worktree's `git status` is clean
