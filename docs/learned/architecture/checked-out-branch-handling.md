---
title: Checked-Out Branch Handling Pattern
read_when:
  - "committing files to a branch that may be checked out in a worktree"
  - "using git plumbing to update branches without checkout"
  - "working with dispatch or incremental-dispatch branch operations"
tripwires:
  - action: "committing files to a branch that may be checked out in a worktree"
    warning: "git branch -f fails on checked-out branches. Use is_branch_checked_out() to detect, then update_local_ref() instead of create_branch(). Sync working tree with 'git checkout HEAD --'. See checked-out-branch-handling.md."
---

# Checked-Out Branch Handling Pattern

When committing files to a branch via git plumbing (without checking it out), the branch may already be checked out in another worktree. `git branch -f` fails on checked-out branches, but `update-ref` works.

## The Problem

`git branch -f <branch> <target>` fails with "cannot force update the current branch" when the branch is checked out. This affects dispatch workflows that commit `.erk/impl-context/` files to a branch without checking it out.

## Detection

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py, is_branch_checked_out -->

Call `is_branch_checked_out(repo_root, branch_name)` on the git worktree gateway. Returns `Path | None` — the worktree path if checked out, `None` otherwise.

## Pattern

The pattern has three steps: fetch the remote branch, detect if checked out, then either force-create or update-ref:

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, _dispatch_planned_pr_plan -->
<!-- Source: src/erk/cli/commands/exec/scripts/incremental_dispatch.py, incremental_dispatch -->

1. Fetch the branch from origin
2. Check if the branch is checked out via `is_branch_checked_out()`
3. If **not** checked out: use `create_branch()` with `force=True`
4. If checked out: get the remote SHA and use `update_local_ref()` instead

See `_dispatch_planned_pr_plan()` in `src/erk/cli/commands/pr/dispatch_cmd.py` for the reference implementation.

## Working Tree Sync

After committing files via plumbing to a checked-out branch, the working tree is stale. Sync by running `git checkout HEAD -- <paths>` in the checked-out worktree directory. This materializes the committed files without changing branches.

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, _dispatch_planned_pr_plan -->

See the working tree sync step in `_dispatch_planned_pr_plan()` in `src/erk/cli/commands/pr/dispatch_cmd.py`.

## Implementations

Two files use this identical pattern:

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, _dispatch_planned_pr_plan -->
<!-- Source: src/erk/cli/commands/exec/scripts/incremental_dispatch.py, incremental_dispatch -->

1. **`src/erk/cli/commands/pr/dispatch_cmd.py`** — `_dispatch_planned_pr_plan()`
2. **`src/erk/cli/commands/exec/scripts/incremental_dispatch.py`** — `incremental_dispatch()`

Both follow the same sequence: fetch, detect checkout, branch-or-update-ref, commit files, sync working tree.

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) — `run_subprocess_with_context` used for the git checkout sync
