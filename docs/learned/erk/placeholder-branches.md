---
title: Placeholder Branches
read_when:
  - working with worktree pool slots, implementing slot commands, deciding when to use ctx.git.branch vs ctx.branch_manager
last_audited: "2025-02-05 12:45 PT"
audit_result: edited
---

# Placeholder Branches

Placeholder branches are ephemeral branches that serve as temporary occupants for pool worktrees when no real work is assigned. They represent an architectural exception where **Graphite tracking is wrong** and low-level git operations should be used instead.

## What Are Placeholder Branches?

Placeholder branches are named `__erk-slot-XX-br-stub__` (e.g., `__erk-slot-01-br-stub__`, `__erk-slot-02-br-stub__`) and serve a single purpose:

**Keep pool worktrees in a valid state when no work is assigned.**

### Key Characteristics

| Property                | Value                   | Why                                                |
| ----------------------- | ----------------------- | -------------------------------------------------- |
| **Lifetime**            | Ephemeral               | Created/destroyed as slots are initialized/removed |
| **Tracking**            | None (local-only)       | Graphite tracking would pollute stack metadata     |
| **Branch point**        | Trunk (master)          | Always based on trunk, never on feature branches   |
| **Worktree constraint** | One worktree per branch | Git prevents checkout in multiple worktrees        |

## When to Use Low-Level Git API vs BranchManager

Placeholder branches bypass `ctx.branch_manager` and use `ctx.git.branch` directly:

```python
# WRONG: Using branch_manager for placeholder branches
ctx.branch_manager.create_branch(
    path=repo.root,
    branch_name=placeholder_branch,
    base_branch=trunk
)
# This would tell Graphite to track the branch (wrong behavior)

# RIGHT: Using low-level git API for placeholder branches
create_result = ctx.git.branch.create_branch(
    repo.root, placeholder_branch, trunk, force=False
)
# This creates a local branch without Graphite metadata
```

**Source**: `unassign_cmd.py:76-82`, `init_pool_cmd.py:108`

## Why Graphite Tracking Is Wrong

Placeholder branches should never be tracked by Graphite because:

1. **They're not real work** — No PRs will be created from placeholder branches
2. **They pollute stack state** — Graphite would consider them part of the stack hierarchy
3. **They're disposable** — Created and destroyed frequently as pool slots are reassigned
4. **They're local-only** — Never pushed to remote, never part of PR workflow

## Placeholder Branch Lifecycle

### Creation (Pool Initialization)

When initializing pool slots with `erk slot init-pool`:

```python
# 1. Get placeholder branch name
placeholder_branch = get_placeholder_branch_name(slot_name)

# 2. Create branch from trunk (bypassing BranchManager)
trunk = ctx.git.branch.detect_trunk_branch(repo.root)
ctx.git.branch.create_branch(repo.root, placeholder_branch, trunk, force=False)

# 3. Create worktree and checkout placeholder branch
worktree_path.mkdir(parents=True, exist_ok=True)
ctx.git.worktree.create_worktree(repo.root, worktree_path, placeholder_branch)
```

### Usage (Slot Unassign)

When unassigning work from a slot:

```python
# 1. Get or create placeholder branch (if it doesn't exist yet)
placeholder_branch = get_placeholder_branch_name(slot_name)
if placeholder_branch not in local_branches:
    ctx.git.branch.create_branch(repo.root, placeholder_branch, trunk, force=False)

# 2. Checkout placeholder branch in the worktree
ctx.branch_manager.checkout_branch(worktree_path, placeholder_branch)
# Note: checkout uses branch_manager, but creation does not
```

### Cleanup (Slot Removal)

When removing a pool slot:

```python
# 1. Remove worktree
ctx.git.worktree.remove_worktree(repo.root, worktree_path, force=True)

# 2. Delete placeholder branch (bypassing BranchManager)
ctx.git.branch.delete_branch(repo.root, placeholder_branch, force=True)
```

## Multi-Worktree Constraint

Git prevents the same branch from being checked out in multiple worktrees simultaneously. This is why each pool slot needs its own placeholder branch:

```bash
# This fails if __erk-slot-01-br-stub__ is already checked out in another worktree:
git -C .erk/worktrees/erk-slot-02 checkout __erk-slot-01-br-stub__
# Error: '__erk-slot-01-br-stub__' is already checked out at '.erk/worktrees/erk-slot-01'
```

Therefore:

- `erk-slot-01` uses `__erk-slot-01-br-stub__`
- `erk-slot-02` uses `__erk-slot-02-br-stub__`
- Each slot has a unique placeholder branch

## Decision Tree: When to Bypass BranchManager

```
Is this a placeholder branch?
├─ YES → Use ctx.git.branch (skip Graphite tracking)
│         Examples: __erk-slot-XX-br-stub__, temp branches for pool operations
└─ NO → Use ctx.branch_manager (Graphite tracking required)
          Examples: feature branches, plan branches, user-created branches
```

## Related Documentation

- [Branch Manager Decision Tree](../architecture/branch-manager-decision-tree.md) — Complete decision framework
- [Branch Manager Abstraction](../architecture/branch-manager-abstraction.md) — BranchManager architecture
