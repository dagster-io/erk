# Plan: Auto-sync trunk in `erk plan submit`

## Problem

`erk plan submit` fails when local trunk (master/main) has diverged from `origin/trunk`. This happens because Graphite requires the local branch to match the remote for stack tracking.

The underlying cause is often that the root worktree isn't on trunk, making it hard to keep trunk synced.

## Solution

Add trunk synchronization logic to `submit_cmd` that:
1. Validates root worktree is on trunk (if not, error with clear message)
2. Auto-syncs trunk with origin/trunk when safe (clean working tree, can fast-forward)
3. Fails with clear error if trunk has truly diverged (local commits not on remote)

## Implementation

### File: `src/erk/cli/commands/submit.py`

Add a new helper function and validation logic after repo context discovery (~line 750):

```python
def _ensure_trunk_synced(ctx: ErkContext, repo: RepoContext) -> None:
    """Ensure root worktree is on trunk and synced with remote.

    Validates:
    1. Root worktree has trunk checked out
    2. Root worktree is clean (no uncommitted changes)
    3. Local trunk matches or can fast-forward to origin/trunk

    Raises SystemExit(1) on validation failure with clear error message.
    """
    trunk = ctx.git.detect_trunk_branch(repo.root)

    # Find root worktree
    worktrees = ctx.git.list_worktrees(repo.root)
    root_worktree = next((wt for wt in worktrees if wt.is_root), None)
    if root_worktree is None:
        # Should not happen, but defensive
        return

    # Check 1: Root worktree must be on trunk
    if root_worktree.branch != trunk:
        user_output(
            click.style("Error: ", fg="red")
            + f"Root worktree is on '{root_worktree.branch}', not '{trunk}'.\n\n"
            f"erk plan submit requires the root worktree to have {trunk} checked out.\n"
            f"This ensures {trunk} can be kept in sync with origin/{trunk}.\n\n"
            f"To fix:\n"
            f"  cd {repo.root}\n"
            f"  git checkout {trunk}"
        )
        raise SystemExit(1)

    # Check 2: Root worktree must be clean
    if ctx.git.has_uncommitted_changes(repo.root):
        user_output(
            click.style("Error: ", fg="red")
            + f"Root worktree has uncommitted changes.\n\n"
            f"Please commit or stash changes before running erk plan submit."
        )
        raise SystemExit(1)

    # Check 3: Sync trunk with remote
    ctx.git.fetch_branch(repo.root, "origin", trunk)

    local_sha = ctx.git.get_branch_head(repo.root, trunk)
    remote_sha = ctx.git.get_branch_head(repo.root, f"origin/{trunk}")

    if local_sha == remote_sha:
        return  # Already synced

    # Check if we can fast-forward (local is ancestor of remote)
    # Use merge-base to determine relationship
    # If merge-base == local_sha, local is behind and can fast-forward
    merge_base = ctx.git.get_merge_base(repo.root, trunk, f"origin/{trunk}")

    if merge_base == local_sha:
        # Local is behind remote - safe to fast-forward
        user_output(f"Syncing {trunk} with origin/{trunk}...")
        ctx.git.pull_branch(repo.root, "origin", trunk, ff_only=True)
        user_output(click.style("✓", fg="green") + f" {trunk} synced with origin/{trunk}")
    elif merge_base == remote_sha:
        # Local is ahead of remote - user has local commits
        user_output(
            click.style("Error: ", fg="red")
            + f"Local {trunk} has commits not pushed to origin/{trunk}.\n\n"
            f"Please push your local commits before running erk plan submit:\n"
            f"  git push origin {trunk}"
        )
        raise SystemExit(1)
    else:
        # True divergence - both have unique commits
        user_output(
            click.style("Error: ", fg="red")
            + f"Local {trunk} has diverged from origin/{trunk}.\n\n"
            f"To fix, sync your local branch:\n"
            f"  git fetch origin && git reset --hard origin/{trunk}\n\n"
            f"Warning: This will discard any local commits on {trunk}."
        )
        raise SystemExit(1)
```

**Integration point** in `submit_cmd` (after line 749):
```python
    repo = discover_repo_context(ctx, ctx.cwd)

    # Ensure trunk is synced before any operations
    _ensure_trunk_synced(ctx, repo)

    # Save current state...
```

### Required Git ABC additions

Need to add one method to the Git gateway:

**`get_merge_base(repo_root, ref1, ref2) -> str | None`**
- Returns the merge base commit SHA between two refs
- Implementation: `git merge-base ref1 ref2`
- Returns None if refs have no common ancestor

Files to modify:
- `packages/erk-shared/src/erk_shared/git/abc.py` - Add abstract method
- `packages/erk-shared/src/erk_shared/git/real.py` - Add real implementation
- `packages/erk-shared/src/erk_shared/git/fake.py` - Add fake implementation
- `packages/erk-shared/src/erk_shared/git/dry_run.py` - Delegate to wrapped
- `packages/erk-shared/src/erk_shared/git/printing.py` - Delegate to wrapped (read-only)

**Existing method to use:**
- `pull_branch(repo_root, remote, branch, ff_only=True)` - Already exists, does fast-forward pull

## Verification

1. **Unit tests** for `_ensure_trunk_synced`:
   - Root worktree not on trunk → error
   - Root worktree has uncommitted changes → error
   - Local trunk behind remote → auto-syncs
   - Local trunk ahead of remote → error with push instructions
   - Local trunk diverged → error with reset instructions
   - Local trunk already synced → passes silently

2. **Integration test**: Run `erk plan submit` after intentionally desyncing local master

3. **Manual verification**:
   - Checkout a non-trunk branch in root worktree, run `erk plan submit` → should error
   - Make root worktree dirty, run `erk plan submit` → should error
   - Be on trunk but behind origin, run `erk plan submit` → should auto-sync and proceed