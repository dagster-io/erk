---
title: Branch Manager Decision Tree
read_when:
  - deciding between ctx.branch_manager and ctx.git.branch, creating branches in erk code, implementing branch operations
tripwires:
  - action: "creating branches in erk code"
    warning: "Use the decision tree to determine whether to use ctx.branch_manager (with Graphite tracking) or ctx.git.branch (low-level git). Placeholder/ephemeral branches bypass branch_manager."
---

# Branch Manager Decision Tree

When creating or managing branches in erk, choosing between `ctx.branch_manager` and `ctx.git.branch` depends on whether the branch should be tracked by Graphite.

## Decision Tree

```
Are you creating a branch?
├─ Is this a placeholder/ephemeral branch?
│  ├─ YES → Use ctx.git.branch (skip Graphite tracking)
│  │        Examples:
│  │        - placeholder/slot-* (pool worktree placeholders)
│  │        - Temporary branches for internal operations
│  │
│  └─ NO → Is this a user-facing feature branch?
│           ├─ YES → Use ctx.branch_manager (Graphite tracking required)
│           │        Examples:
│           │        - Plan implementation branches
│           │        - Feature branches created by user
│           │        - Stacked branches for PRs
│           │
│           └─ NO → Are you unsure?
│                    └─ Default to ctx.branch_manager
│                       (Most erk operations involve tracked branches)
```

## Use ctx.git.branch (Low-Level Git API)

**When**: The branch is ephemeral, local-only, or should never be part of a stack.

### Pattern

```python
# Create a local-only branch without Graphite metadata
result = ctx.git.branch.create_branch(
    repo.root,
    branch_name="placeholder/slot-1",
    base_branch="master",
    force=False
)

if isinstance(result, BranchAlreadyExists):
    # Handle error
    ...
```

### Examples

1. **Placeholder branches** (pool worktrees)
   - `placeholder/slot-1`, `placeholder/slot-2`, etc.
   - Created in `init_pool_cmd.py:108` and `unassign_cmd.py:76-82`
   - Never pushed, never part of PR workflow

2. **Temporary operational branches**
   - Internal branches used for erk operations
   - Cleaned up after use
   - Not visible to user

## Use ctx.branch_manager (Graphite-Tracked Branches)

**When**: The branch will become part of a stack, pushed to remote, or used for a PR.

### Pattern

```python
# Create a tracked branch with Graphite metadata
result = ctx.branch_manager.create_branch(
    path=repo.root,
    branch_name="feature/my-work",
    base_branch="master"
)

# IMPORTANT: create_branch() restores the original branch after tracking
# If you need to be on the new branch, explicitly check it out:
ctx.branch_manager.checkout_branch(repo.root, "feature/my-work")
```

### Examples

1. **Plan implementation branches**
   - Created by `setup-impl-from-issue` for plan work
   - Will have PRs created from them
   - Part of stack workflow

2. **User-created feature branches**
   - `gt create feature/new-thing`
   - Managed by Graphite's stack tracking
   - Pushed to remote for collaboration

3. **Stacked branches**
   - Branches that depend on other branches
   - Require Graphite metadata for upstack/downstack operations

## Multi-Worktree Implications

Both APIs respect git's multi-worktree constraint:

**Rule**: A branch cannot be checked out in multiple worktrees simultaneously.

This is why placeholder branches are unique per slot:

- `slot-1` → `placeholder/slot-1`
- `slot-2` → `placeholder/slot-2`

### Checkout After Create

**CRITICAL**: `ctx.branch_manager.create_branch()` **restores the original branch** after creating and tracking the new branch.

If you need to be on the new branch after creation:

```python
# WRONG: Assumes you're on the new branch after create
ctx.branch_manager.create_branch(path, branch_name, base_branch)
# You're still on the original branch here!

# RIGHT: Explicitly checkout after create
ctx.branch_manager.create_branch(path, branch_name, base_branch)
ctx.branch_manager.checkout_branch(path, branch_name)
# Now you're on the new branch
```

**Source**: See [Branch Manager Abstraction](branch-manager-abstraction.md) tripwire.

## Code Examples by Scenario

### Scenario 1: Initialize Pool Slot

```python
# Creating placeholder branch (bypass branch_manager)
placeholder_branch = get_placeholder_branch_name(slot_name)
trunk = ctx.git.branch.detect_trunk_branch(repo.root)

create_result = ctx.git.branch.create_branch(
    repo.root, placeholder_branch, trunk, force=False
)
```

**Why**: Placeholder branches are ephemeral and local-only.

### Scenario 2: Setup Plan Implementation

```python
# Creating feature branch for plan work (use branch_manager)
result = ctx.branch_manager.create_branch(
    path=repo.root,
    branch_name=f"impl/{plan_slug}",
    base_branch=current_branch
)

# Explicitly checkout to start work on the new branch
ctx.branch_manager.checkout_branch(repo.root, f"impl/{plan_slug}")
```

**Why**: Plan branches will have PRs and need Graphite tracking.

### Scenario 3: Unassign Slot (Switch to Placeholder)

```python
# Get or create placeholder (bypass branch_manager for create)
if placeholder_branch not in local_branches:
    ctx.git.branch.create_branch(repo.root, placeholder_branch, trunk, force=False)

# Checkout placeholder (use branch_manager for checkout)
ctx.branch_manager.checkout_branch(worktree_path, placeholder_branch)
```

**Why**: Creation bypasses tracking, but checkout uses branch_manager for consistency.

## Summary Table

| Operation             | Placeholder Branches                   | Feature Branches                       |
| --------------------- | -------------------------------------- | -------------------------------------- |
| **Create**            | `ctx.git.branch.create_branch()`       | `ctx.branch_manager.create_branch()`   |
| **Checkout**          | `ctx.branch_manager.checkout_branch()` | `ctx.branch_manager.checkout_branch()` |
| **Delete**            | `ctx.git.branch.delete_branch()`       | `ctx.branch_manager.delete_branch()`   |
| **Graphite tracking** | No                                     | Yes                                    |
| **Pushed to remote**  | No                                     | Yes                                    |
| **Used in PRs**       | No                                     | Yes                                    |

## Related Documentation

- [Placeholder Branches](../erk/placeholder-branches.md) — Detailed placeholder branch lifecycle
- [Branch Manager Abstraction](branch-manager-abstraction.md) — BranchManager architecture and tripwires
- [Worktree Pool Operations](../erk/worktree-pool.md) — How pool slots work
