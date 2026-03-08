---
title: Git Plumbing Patterns
read_when:
  - "modifying plan_save.py branch commit behavior"
  - "understanding git plumbing patterns in erk"
  - "working with commit_files_to_branch"
  - "eliminating git checkouts"
  - "dispatch without checkout"
tripwires:
  - action: "checking out a branch in plan_save to commit files"
    warning: "Plan save uses git plumbing (commit_files_to_branch) to commit without checkout. Do NOT add checkout_branch calls. See git-plumbing-patterns.md."
  - action: "adding new git operations that require a branch checkout"
    warning: "When adding new git operations, prefer plumbing (update-ref, commit-tree) over checkout-based workflows. See git-plumbing-patterns.md."
  - action: "using update_local_ref on a branch that might be checked out"
    warning: "Use find_worktree_for_branch first. If checked out, use git pull --ff-only instead (updates ref + index + working tree). Ref-only updates on checked-out branches cause index desynchronization."
---

# Git Plumbing Patterns

Erk uses git plumbing commands to manipulate branches without checkout. This avoids race conditions in multi-session worktrees and eliminates the need to restore branch state after operations.

## When to Use Which Pattern

| Pattern                     | Use When                                               | Gateway Method                        | Example                           |
| --------------------------- | ------------------------------------------------------ | ------------------------------------- | --------------------------------- |
| `update_local_ref`          | Advancing a local branch pointer to match a remote SHA | `git.branch.update_local_ref()`       | Syncing trunk without checkout    |
| `commit_files_to_branch`    | Creating a commit on a branch from in-memory files     | `git.commit.commit_files_to_branch()` | Plan save, dispatch impl-context  |
| `create_branch(force=True)` | Resetting a local branch to match a remote ref         | `git.branch.create_branch()`          | Syncing dispatch branch to origin |

## Pattern 1: `commit_files_to_branch` (Create Commit Without Checkout)

### How It Works

The `commit_files_to_branch` method on `GitCommitOps` uses a temporary index file to create a commit without modifying the working tree, HEAD, or the real index:

1. Creates a temporary index file
2. Hashes file contents into the temporary index
3. Writes a tree object from the temporary index
4. Creates a commit object pointing to the tree
5. Updates the branch ref to point to the new commit

This is race-condition-free because no branch checkout occurs.

### Implementation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py, commit_files_to_branch -->

See `RealGitCommitOps.commit_files_to_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py` for the full implementation.

### Usage in Plan Save

<!-- Source: src/erk/cli/commands/exec/scripts/plan_save.py, _save_as_planned_pr -->

`_save_as_planned_pr()` in `src/erk/cli/commands/exec/scripts/plan_save.py` uses this pattern:

- Creates plan branch from current branch via `branch_manager.create_branch()`
- Commits plan files directly to the branch using git plumbing (no checkout)
- Pushes to origin with upstream tracking
- **Never checks out the plan branch** -- HEAD and working tree remain untouched
- **Calls `retrack_branch()` after `commit_files_to_branch()`** to prevent Graphite SHA tracking divergence (the branch ref advanced past what `create_branch()` originally tracked). See `plan_save.py:257-260`. Cross-reference: `docs/learned/architecture/git-graphite-quirks.md`

### Usage in Dispatch

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, _dispatch_planned_pr_plan -->

`_dispatch_planned_pr_plan()` in `src/erk/cli/commands/pr/dispatch_cmd.py` (lines 182-351) uses this pattern to commit impl-context files to a branch without checkout:

1. Fetches and syncs the target branch to match remote
2. Builds impl-context files in-memory via `build_impl_context_files()`
3. Commits files directly to the branch via `commit_files_to_branch()`
4. Pushes to remote
5. Triggers GitHub Actions workflow dispatch

### Usage in Incremental Dispatch

<!-- Source: src/erk/cli/commands/exec/scripts/incremental_dispatch.py -->

Incremental dispatch uses the same plumbing pattern with an additional Graphite retrack step. After committing files to a branch via `commit_files_to_branch()`, the branch ref advances but Graphite's tracked SHA becomes stale. The fix:

1. Sync local branch ref to remote via `fetch_branch()` + conditional `create_branch(force=True)` or `update_local_ref()`
2. Commit impl-context files via `commit_files_to_branch()`
3. Call `branch_manager.retrack_branch()` to update Graphite's tracking SHA
4. If branch is currently checked out, write files to disk to keep working tree consistent

## Pattern 2: `update_local_ref` (Advance Branch Pointer)

### How It Works

`update_local_ref()` uses `git update-ref` to move a local branch pointer to a new commit SHA without checking out the branch.

### Checked-Out Branch Handling

When the target branch is currently checked out in a worktree, `update_local_ref` is used instead of `create_branch(force=True)` because git refuses to force-update a checked-out branch. The incremental dispatch script uses an LBYL check:

<!-- Source: src/erk/cli/commands/exec/scripts/incremental_dispatch.py, incremental_dispatch (branch sync section) -->

See the branch sync section of `incremental_dispatch()` in `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`. It calls `git.worktree.is_branch_checked_out()` first — if the branch is not checked out anywhere, it uses `create_branch(force=True)` to reset the ref. If the branch is checked out, it falls back to `update_local_ref()` with the remote SHA.

After a plumbing commit to a checked-out branch, the index may contain stale staged changes. Reset with `git checkout HEAD --` on the committed files to sync the index.

<!-- Source: src/erk/cli/commands/exec/scripts/incremental_dispatch.py, incremental_dispatch (index sync section) -->

See the index sync section of `incremental_dispatch()` in `src/erk/cli/commands/exec/scripts/incremental_dispatch.py`. After committing, if the branch is checked out it runs `git checkout HEAD --` on the committed `impl_context_paths` via `run_subprocess_with_context()` to bring the index back in sync.

### Implementation

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py:282-294 -->

See `update_local_ref()` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py` (lines 282-294).

### Usage in Trunk Sync

<!-- Source: src/erk/cli/commands/pr/dispatch_helpers.py, ensure_trunk_synced -->

`ensure_trunk_synced()` in `src/erk/cli/commands/pr/dispatch_helpers.py` (lines 26-88) uses this pattern to sync the local trunk branch to match remote without a checkout:

1. Fetches the remote branch
2. Compares local and remote SHAs
3. Checks merge-base to determine sync direction
4. **Conditional sync based on checkout state**: Uses `find_worktree_for_branch()` to check if trunk is currently checked out. If checked out, uses `pull_branch(ff_only=True)` to update ref + index + working tree. If not checked out, uses `update_local_ref()` for ref-only update.
5. Error on diverged or ahead states (user has unpushed commits)

The LBYL check with `find_worktree_for_branch()` prevents index desynchronization: a ref-only update on a checked-out branch leaves the index pointing at the old tree, causing staged reverse changes when the user next runs `git status`.

## Evolution

- PR #7491 removed checkout (plan committed without switching branches)
- PR #7494 re-added checkout with try/finally for the plan file commit step
- PR #7783 replaced checkout with git plumbing to eliminate race conditions
- PR #8578 applied `commit_files_to_branch` pattern to dispatch workflow
- PR #8582 applied `update_local_ref` pattern to trunk sync in dispatch helpers
- PR #8789 added checked-out branch handling and index sync to incremental dispatch

## Testing

Tests in `tests/unit/cli/commands/exec/scripts/test_plan_save.py` verify that plan save does not check out the plan branch and that plan files are committed directly to the branch via the plumbing approach.

## Related Topics

- [Planned PR Backend](../planning/planned-pr-backend.md) - Backend that uses these patterns
