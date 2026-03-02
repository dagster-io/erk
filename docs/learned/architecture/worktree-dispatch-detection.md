---
title: Worktree Detection in Dispatch
read_when:
  - "modifying dispatch command logic"
  - "working with worktree branch detection"
tripwires:
  - action: "assuming plan branch is always in root worktree"
    warning: "Branch may already be checked out in a slot worktree. Use find_worktree_for_branch() to detect."
---

# Worktree Detection in Dispatch

## Problem

`erk pr dispatch` needs to check out a plan branch, commit `.erk/impl-context/`, and push. Previously it assumed the branch could always be checked out in the root worktree, but the branch may already be checked out in a slot worktree (e.g., from a prior `erk implement`).

## Solution

LBYL pattern using `find_worktree_for_branch()` to detect if the branch is already in a worktree before attempting checkout:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py, find_worktree_for_branch -->

See `find_worktree_for_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py` for the ABC method. The pattern is: call `find_worktree_for_branch(repo_root, branch_name)`, then branch on `None` (needs checkout) vs a `Path` (already checked out). This LBYL pattern is used in `checkout_helpers.py`, `checkout_cmd.py`, `dispatch_helpers.py`, and `land_cmd.py`.

## Key Details

- `work_dir` variable: toggles between root and existing worktree for all subsequent git operations (pull, commit, push)
- Graphite `retrack` uses `repo.root` (repo-global operation) while git ops use `work_dir`
- Conditional branch restoration: only restores to original branch if `checked_out_in_root` was True

## Gateway

`find_worktree_for_branch()` is defined in the git worktree gateway:

- ABC: `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py`
- Real: `packages/erk-shared/src/erk_shared/gateway/git/worktree/real.py`
- Fake: `packages/erk-shared/src/erk_shared/gateway/git/worktree/fake.py`

Returns `Path | None` -- the worktree path if the branch is checked out, or None.
