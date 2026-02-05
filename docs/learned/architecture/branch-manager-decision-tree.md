---
title: Branch Manager Decision Tree
read_when:
  - deciding between ctx.branch_manager and ctx.git.branch, creating branches in erk code, implementing branch operations
tripwires:
  - action: "creating branches in erk code"
    warning: "Use the decision tree to determine whether to use ctx.branch_manager (with Graphite tracking) or ctx.git.branch (low-level git). Placeholder/ephemeral branches bypass branch_manager."
last_audited: "2026-02-05 14:15 PT"
audit_result: edited
---

# Branch Manager Decision Tree

When creating or managing branches in erk, choosing between `ctx.branch_manager` and `ctx.git.branch` depends on whether the branch should be tracked by Graphite.

## Decision Tree

```
Are you creating a branch?
├─ Is this a placeholder/ephemeral branch?
│  ├─ YES → Use ctx.git.branch (skip Graphite tracking)
│  │        Examples:
│  │        - __erk-slot-XX-br-stub__ (pool worktree placeholders)
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

See `init_pool_cmd.py` and `unassign_cmd.py` in `src/erk/cli/commands/slot/` for working examples of `ctx.git.branch.create_branch()`.

### Examples

1. **Placeholder branches** (pool worktrees)
   - `__erk-slot-01-br-stub__`, `__erk-slot-02-br-stub__`, etc.
   - Created via `get_placeholder_branch_name()` in `src/erk/cli/commands/slot/common.py`
   - Never pushed, never part of PR workflow

2. **Temporary operational branches**
   - Internal branches used for erk operations
   - Cleaned up after use
   - Not visible to user

## Use ctx.branch_manager (Graphite-Tracked Branches)

**When**: The branch will become part of a stack, pushed to remote, or used for a PR.

See `setup_impl_from_issue.py` in `src/erk/cli/commands/exec/` for a working example of `ctx.branch_manager.create_branch()` followed by `checkout_branch()`.

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

- `erk-slot-01` → `__erk-slot-01-br-stub__`
- `erk-slot-02` → `__erk-slot-02-br-stub__`

### Checkout After Create

**CRITICAL**: `ctx.branch_manager.create_branch()` **restores the original branch** after creating and tracking the new branch (in Graphite mode). If you need to be on the new branch after creation, explicitly call `ctx.branch_manager.checkout_branch()`.

```python
# WRONG: Assumes you're on the new branch after create
ctx.branch_manager.create_branch(repo_root, branch_name, base_branch)
# You're still on the original branch here!

# RIGHT: Explicitly checkout after create
ctx.branch_manager.create_branch(repo_root, branch_name, base_branch)
ctx.branch_manager.checkout_branch(repo_root, branch_name)
# Now you're on the new branch
```

**Source**: See [Branch Manager Abstraction](branch-manager-abstraction.md) tripwire.

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
