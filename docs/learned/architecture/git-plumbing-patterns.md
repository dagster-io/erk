---
title: Git Plumbing Patterns
read_when:
  - "modifying plan_save.py branch commit behavior"
  - "understanding git plumbing patterns in erk"
  - "working with commit_files_to_branch"
  - "eliminating git checkouts"
  - "plumbing operations"
  - "dispatch without checkout"
tripwires:
  - action: "checking out a branch in plan_save to commit files"
    warning: "Plan save uses git plumbing (commit_files_to_branch) to commit without checkout. Do NOT add checkout_branch calls. See git-plumbing-patterns.md."
  - action: "adding new git operations that require checking out a branch"
    warning: "When adding new git operations, prefer plumbing (update-ref, commit-tree) over checkout-based workflows. See git-plumbing-patterns.md."
---

# Git Plumbing Patterns

Erk uses git plumbing commands to perform branch operations without checking out branches. This eliminates race conditions in multi-session environments and avoids side effects on the working tree.

## When to Use Which Pattern

| Pattern                     | Purpose                                        | Example                                                                                   |
| --------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `update_local_ref()`        | Advance a local branch pointer to match remote | `ensure_trunk_synced()` in dispatch_helpers.py                                            |
| `commit_files_to_branch()`  | Create a commit on a branch without checkout   | `_save_as_planned_pr()` in plan_save.py, `_dispatch_planned_pr_plan()` in dispatch_cmd.py |
| `create_branch(force=True)` | Sync local branch to match remote exactly      | Fetch + force-create to reset local to remote state                                       |

## Pattern 1: update_local_ref

Advances a local branch ref to point at a new commit without modifying HEAD or the working tree.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py, update_local_ref -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py, update_local_ref -->

**Gateway**: `git.branch.update_local_ref(repo_root, branch, target_sha)`

**Underlying command**: `git update-ref refs/heads/{branch} {target_sha}`

**Usage in dispatch_helpers.py** (`ensure_trunk_synced()`, lines 26-82):

1. Fetches the remote branch to get latest state
2. Compares local and remote SHAs via merge-base analysis
3. If local is behind remote and branch is NOT checked out, calls `update_local_ref()` to fast-forward
4. Falls back to requiring a clean worktree if the branch IS currently checked out

**Key constraint**: Only safe when the target branch is not checked out in any worktree. The function checks `get_current_branch()` before calling `update_local_ref()`.

## Pattern 2: commit_files_to_branch

Creates a commit directly on a branch using a temporary index file, without modifying HEAD, the working tree, or the real index.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/commit_ops/abc.py, commit_files_to_branch -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py, commit_files_to_branch -->

**Gateway**: `git.commit.commit_files_to_branch(cwd, branch=..., files=..., message=...)`

**How it works** (in `RealGitCommitOps.commit_files_to_branch()`, lines 71-141):

1. Resolves the branch's current HEAD to get the parent SHA
2. Creates a temporary index file (`GIT_INDEX_FILE` env var)
3. Reads the parent tree into the temp index via `git read-tree`
4. For each file: hashes content with `git hash-object -w --stdin`, adds to index via `git update-index --add --cacheinfo`
5. Writes a tree object from the temp index via `git write-tree`
6. Creates a commit object via `git commit-tree` with the parent
7. Updates the branch ref via `git update-ref`
8. Cleans up the temporary index in a `finally` block

**Usage in plan_save.py** (`_save_as_planned_pr()`):

- Commits plan files to the plan branch without switching HEAD
- Race-condition-free for multi-session worktrees

**Usage in dispatch_cmd.py** (`_dispatch_planned_pr_plan()`, lines 218-245):

- Builds impl-context files in-memory via `build_impl_context_files()`
- Commits them directly to the implementation branch
- Entire dispatch operates without any checkout: fetch → create_branch(force) → commit_files_to_branch → push

## Pattern 3: Fetch + Force-Create (No-Checkout Sync)

Syncs a local branch to match the remote state by fetching and force-creating.

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, _dispatch_planned_pr_plan -->

See `_dispatch_planned_pr_plan()` in `src/erk/cli/commands/pr/dispatch_cmd.py` for the fetch + force-create sequence: it calls `fetch_branch()` followed by `create_branch(force=True)` to reset the local branch to match the remote.

**Usage in dispatch_cmd.py** (`_dispatch_planned_pr_plan()`):

- Ensures local branch matches remote before committing new files
- Combined with `commit_files_to_branch()` for a fully checkout-free dispatch workflow

## Evolution

- PR #7491: Removed checkout from plan save (commit without switching branches)
- PR #7494: Re-added checkout with try/finally for the plan file commit step
- PR #7783: Replaced checkout with git plumbing to eliminate race conditions
- PR #8582: Eliminated master checkout from plan-save and dispatch using `update_local_ref`
- PR #8578: Converted dispatch to use `commit_files_to_branch` instead of checkout-based commit

## Testing

Tests in `tests/unit/cli/commands/exec/scripts/test_plan_save.py` verify that plan save does not check out the plan branch and that plan files are committed directly to the branch via the plumbing approach.

## Related Topics

- [Planned PR Backend](../planning/planned-pr-backend.md) - Backend that uses this pattern
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - Gateway pattern for git operations
