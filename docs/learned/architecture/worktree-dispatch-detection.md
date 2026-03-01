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

```python
existing_worktree = ctx.git.worktree.find_worktree_for_branch(repo.root, branch_name)
if existing_worktree is not None:
    work_dir = existing_worktree
    checked_out_in_root = False
else:
    ctx.branch_manager.checkout_branch(repo.root, branch_name)
    work_dir = repo.root
    checked_out_in_root = True
```

**Source:** `src/erk/cli/commands/pr/dispatch_cmd.py:229-247`

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
