---
title: Branch Manager Decision Tree
read_when:
  - deciding between ctx.branch_manager and ctx.git.branch for branch creation
  - implementing branch operations in erk code
  - working with placeholder branches or worktree pool slots
tripwires:
  - action: "creating branches in erk code"
    warning: "Use the decision tree to determine whether to use ctx.branch_manager (with Graphite tracking) or ctx.git.branch (low-level git). Placeholder/ephemeral branches bypass branch_manager."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Branch Manager Decision Tree

## The Core Question

When creating branches in erk, choosing between `ctx.branch_manager` and `ctx.git.branch` comes down to one question: **Should this branch be tracked by Graphite?**

User-facing branches that will become PRs need Graphite tracking for stack metadata. Internal operational branches (placeholder branches for pool slots, temporary scaffolding) should bypass tracking to avoid polluting stack state.

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

**Why**: Bypassing BranchManager prevents Graphite from tracking branches that are frequently created/destroyed and never pushed. Placeholder branches (`__erk-slot-01-br-stub__`) exist only to satisfy git's multi-worktree constraint (a branch cannot be checked out in multiple worktrees). They are never part of PR workflows.

<!-- Source: src/erk/cli/commands/slot/common.py, get_placeholder_branch_name -->

See `get_placeholder_branch_name()` in `src/erk/cli/commands/slot/common.py` for the placeholder naming convention, and `execute_unassign()` in `src/erk/cli/commands/slot/unassign_cmd.py` for the create-or-get pattern before checking out placeholder branches.

### Examples

1. **Placeholder branches** (pool worktrees) — never pushed, never PRs, unique per slot
2. **Temporary operational branches** — internal scaffolding cleaned up after use

<!-- Source: src/erk/cli/commands/slot/init_pool_cmd.py, slot_init_pool -->
<!-- Source: src/erk/cli/commands/slot/unassign_cmd.py, execute_unassign -->

The `slot init-pool` command in `src/erk/cli/commands/slot/init_pool_cmd.py` creates placeholder branches via `ctx.git.branch.create_branch()`. The `slot unassign` command in `src/erk/cli/commands/slot/unassign_cmd.py` creates-or-gets placeholder branches before checking them out.

## Use ctx.branch_manager (Graphite-Tracked Branches)

**When**: The branch will become part of a stack, pushed to remote, or used for a PR.

**Why**: BranchManager abstracts over Graphite vs plain Git modes. In Graphite mode, it delegates to `GraphiteBranchOps` to run `gt track`. In Git mode, it creates plain branches without metadata. Commands use `ctx.branch_manager` so they work in both modes without conditional logic.

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py, setup_impl_from_issue -->

See `setup_impl_from_issue()` in `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` for the pattern: `branch_manager.create_branch()` followed by `branch_manager.checkout_branch()` to set up a plan implementation branch.

### Examples

1. **Plan implementation branches** — created by `setup-impl-from-issue`, will have PRs
2. **User-created feature branches** — `gt create feature/new-thing`, managed by Graphite
3. **Stacked branches** — depend on other branches, require Graphite metadata for upstack/downstack operations

## Multi-Worktree Constraint

Both APIs respect git's multi-worktree constraint: **a branch cannot be checked out in multiple worktrees simultaneously**.

This is why placeholder branches are unique per slot:

- `erk-slot-01` → `__erk-slot-01-br-stub__`
- `erk-slot-02` → `__erk-slot-02-br-stub__`

Each slot gets its own placeholder so unassigned slots can coexist without checkout conflicts.

## Critical Gotcha: Checkout After Create

`ctx.branch_manager.create_branch()` **restores the original branch** after creating and tracking the new branch (in Graphite mode). If you need to be on the new branch after creation, explicitly call `ctx.branch_manager.checkout_branch()`.

**Why this behavior**: `gt track` requires the branch to be checked out. `GraphiteBranchManager.create_branch()` saves the current branch, checks out the new branch to run `gt track`, then restores the original branch to avoid side effects on the caller's working directory.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py, GraphiteBranchManager.create_branch -->

See `GraphiteBranchManager.create_branch()` in `packages/erk-shared/src/erk_shared/gateway/branch_manager/graphite.py` for the full save/checkout/track/restore logic, and [Branch Manager Abstraction](branch-manager-abstraction.md) for deeper architectural context.

### Anti-Pattern

```python
# WRONG: Assumes you're on the new branch after create
ctx.branch_manager.create_branch(repo_root, branch_name, base_branch)
# You're still on the original branch here!

# RIGHT: Explicitly checkout after create
ctx.branch_manager.create_branch(repo_root, branch_name, base_branch)
ctx.branch_manager.checkout_branch(repo_root, branch_name)
# Now you're on the new branch
```

## Summary Table

| Operation             | Placeholder Branches                   | Feature Branches                       |
| --------------------- | -------------------------------------- | -------------------------------------- |
| **Create**            | `ctx.git.branch.create_branch()`       | `ctx.branch_manager.create_branch()`   |
| **Checkout**          | `ctx.branch_manager.checkout_branch()` | `ctx.branch_manager.checkout_branch()` |
| **Delete**            | `ctx.git.branch.delete_branch()`       | `ctx.branch_manager.delete_branch()`   |
| **Graphite tracking** | No                                     | Yes                                    |
| **Pushed to remote**  | No                                     | Yes                                    |
| **Used in PRs**       | No                                     | Yes                                    |

**Note**: Both placeholder and feature branches use `ctx.branch_manager.checkout_branch()` because checkout must respect Graphite mode for all branches (even if the branch itself isn't tracked).

## Related Documentation

- [Placeholder Branches](../erk/placeholder-branches.md) — Detailed placeholder branch lifecycle
- [Branch Manager Abstraction](branch-manager-abstraction.md) — BranchManager architecture and tripwires
