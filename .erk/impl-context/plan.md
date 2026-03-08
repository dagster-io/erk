# Fix: `update_local_ref` desyncs checked-out worktrees

## Context

When automation code (dispatch, incremental-dispatch, checkout) uses `update_local_ref` on a branch that's checked out in a worktree, it moves the branch pointer via `git update-ref` without updating the index or working tree. This leaves the worktree in a confusing state: `git status` shows phantom modifications, `git diff` is empty, and HEAD no longer matches the working tree.

The `update_local_ref` docstring already documents this limitation ("safe to use when the branch is NOT currently checked out"). The callers aren't respecting the contract.

The correct pattern already exists in `ensure_trunk_synced` (`dispatch_helpers.py:60-68`): use `pull_branch` when checked out, `update_local_ref` when not.

## Fix

### Extract a helper: `sync_branch_to_sha`

Add to `dispatch_helpers.py` (already has `ensure_trunk_synced` as precedent):

```python
def sync_branch_to_sha(
    ctx: ErkContext, repo_root: Path, branch: str, target_sha: str
) -> None:
    """Move a local branch to target_sha, safely handling checked-out branches.

    When the branch is NOT checked out, uses update_local_ref (fast ref update).
    When the branch IS checked out, uses 'git reset --hard' in the worktree
    to atomically sync ref + index + working tree. Refuses if the worktree
    has uncommitted changes.
    """
    checked_out_path = ctx.git.worktree.is_branch_checked_out(repo_root, branch)
    if checked_out_path is None:
        ctx.git.branch.update_local_ref(repo_root, branch, target_sha)
        return

    local_sha = ctx.git.branch.get_branch_head(repo_root, branch)
    if local_sha == target_sha:
        return

    if ctx.git.status.has_uncommitted_changes(checked_out_path):
        user_output(
            click.style("Error: ", fg="red")
            + f"Branch '{branch}' is checked out at {checked_out_path} with "
            f"uncommitted changes.\n\n"
            f"Please commit or stash changes before proceeding."
        )
        raise SystemExit(1)

    # Atomically sync ref + index + working tree
    run_subprocess_with_context(
        cmd=["git", "reset", "--hard", target_sha],
        operation_context=f"sync checked-out branch '{branch}' to {target_sha[:8]}",
        cwd=checked_out_path,
    )
```

### Update call sites

**1. `src/erk/cli/commands/pr/dispatch_cmd.py:231-237`** (primary bug)

```python
# Before:
checked_out_path = ctx.git.worktree.is_branch_checked_out(repo.root, branch_name)
if checked_out_path is None:
    ctx.git.branch.create_branch(repo.root, branch_name, f"origin/{branch_name}", force=True)
else:
    remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{branch_name}")
    if remote_sha is not None:
        ctx.git.branch.update_local_ref(repo.root, branch_name, remote_sha)

# After:
checked_out_path = ctx.git.worktree.is_branch_checked_out(repo.root, branch_name)
if checked_out_path is None:
    ctx.git.branch.create_branch(repo.root, branch_name, f"origin/{branch_name}", force=True)
else:
    remote_sha = ctx.git.branch.get_branch_head(repo.root, f"origin/{branch_name}")
    if remote_sha is not None:
        sync_branch_to_sha(ctx, repo.root, branch_name, remote_sha)
```

**2. `src/erk/cli/commands/exec/scripts/incremental_dispatch.py:105-111`** (same bug)

Same pattern — replace `update_local_ref` with `sync_branch_to_sha`.

**3. `src/erk/cli/commands/branch/checkout_cmd.py:388`** (parent branch sync)

Replace `update_local_ref` with `sync_branch_to_sha`. Parent branch (e.g., master) may be checked out in root worktree.

**4. `src/erk/cli/commands/pr/checkout_cmd.py:274`** (parent branch sync)

Same as #3.

### Remove redundant partial sync from dispatch_cmd.py

Lines 257-267 (`git checkout HEAD -- <impl_context_paths>`) can be **kept as-is** — after `sync_branch_to_sha` properly syncs the worktree, `commit_files_to_branch` still desyncs the impl-context files specifically, and this existing code handles that delta correctly.

### Tests

- Update `tests/commands/pr/test_dispatch.py` — verify `sync_branch_to_sha` is called instead of raw `update_local_ref` for the checked-out case
- Add test for dirty worktree rejection
- Update `tests/unit/cli/commands/exec/scripts/test_incremental_dispatch.py` — same pattern

## Files to modify

1. `src/erk/cli/commands/pr/dispatch_helpers.py` — add `sync_branch_to_sha`
2. `src/erk/cli/commands/pr/dispatch_cmd.py` — use new helper
3. `src/erk/cli/commands/exec/scripts/incremental_dispatch.py` — use new helper
4. `src/erk/cli/commands/branch/checkout_cmd.py` — use new helper
5. `src/erk/cli/commands/pr/checkout_cmd.py` — use new helper
6. `tests/commands/pr/test_dispatch.py` — update test
7. `tests/unit/cli/commands/exec/scripts/test_incremental_dispatch.py` — update test

## Verification

1. Run existing tests via devrun to confirm no regressions
2. Manually test: dispatch a plan to a branch that's checked out in a worktree, verify working tree stays clean
3. Verify dirty worktree is properly rejected with clear error message
