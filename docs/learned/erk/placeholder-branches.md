---
title: Placeholder Branches
read_when:
  - working with worktree pool slots or slot commands
  - understanding why placeholder branches bypass BranchManager
  - debugging slot cleanup during erk land
tripwires:
  - action: "creating a placeholder branch with ctx.branch_manager.create_branch()"
    warning: "Placeholder branches must bypass BranchManager. Use ctx.git.branch.create_branch() to avoid Graphite tracking. See branch-manager-decision-tree.md for the full decision framework."
  - action: "deleting a placeholder branch with ctx.branch_manager.delete_branch()"
    warning: "Placeholder branch deletion must also bypass BranchManager. Use ctx.git.branch.delete_branch() directly."
last_audited: "2026-02-08"
audit_result: edited
---

# Placeholder Branches

Placeholder branches exist to satisfy a git constraint: every worktree must have a branch checked out. When a pool slot has no real work assigned, it needs a branch to occupy it. Placeholder branches fill this role without polluting Graphite's stack metadata.

## Why They Exist

Git prevents a worktree from existing without a checked-out branch, and it also prevents the same branch from being checked out in multiple worktrees simultaneously. These two constraints together force a design where each pool slot has its own dedicated placeholder branch (`__erk-slot-XX-br-stub__`). Without unique-per-slot placeholders, unassigned slots would conflict with each other.

## The Create/Checkout Asymmetry

The most important cross-cutting pattern in placeholder branch handling is the asymmetry between **creation** and **checkout**:

| Operation    | API                                    | Why                                                     |
| ------------ | -------------------------------------- | ------------------------------------------------------- |
| **Create**   | `ctx.git.branch.create_branch()`       | Must bypass Graphite — placeholders are not real work   |
| **Checkout** | `ctx.branch_manager.checkout_branch()` | Checkout must respect Graphite mode for all branches    |
| **Delete**   | `ctx.git.branch.delete_branch()`       | Must bypass Graphite — no tracking metadata to clean up |

This asymmetry catches people because creation and deletion bypass `branch_manager` while checkout goes through it. The reason: `checkout_branch()` handles Graphite-mode-specific behavior that affects _any_ branch being checked out (not just tracked ones), while `create_branch()` and `delete_branch()` on `branch_manager` would incorrectly add/remove Graphite tracking metadata.

<!-- Source: src/erk/cli/commands/slot/unassign_cmd.py, execute_unassign -->
<!-- Source: src/erk/cli/commands/slot/init_pool_cmd.py, slot_init_pool -->

See `execute_unassign()` in `src/erk/cli/commands/slot/unassign_cmd.py` for the create-then-checkout pattern, and `slot_init_pool()` in `src/erk/cli/commands/slot/init_pool_cmd.py` for bulk creation during pool initialization.

## Create-or-Get Pattern

Placeholder branches use a lazy creation pattern: check if the branch already exists before creating it. This is necessary because placeholder branches persist across multiple assign/unassign cycles — `slot init-pool` creates them once, and subsequent `slot unassign` operations reuse them rather than recreating. A "create every time" approach would fail when the branch already exists from a prior cycle, since `create_branch()` with `force=False` returns `BranchAlreadyExists`.

<!-- Source: src/erk/cli/commands/slot/unassign_cmd.py, execute_unassign -->

See `execute_unassign()` in `src/erk/cli/commands/slot/unassign_cmd.py` for the `if placeholder_branch not in local_branches` guard before `create_branch()`.

## Cross-Cutting Touchpoints

Placeholder branches are not isolated to slot commands. Several other systems need to recognize and handle them:

- **Submit** detects placeholder branches to determine the base branch for new PRs. When running `erk submit` from a slot on a placeholder branch, the submit logic falls back to trunk as the base branch (since placeholder branches are local-only and have no remote tracking). See `submit_cmd()` in `src/erk/cli/commands/submit.py`.
- **Worktree list** filters out placeholder branches by default so users only see slots with meaningful work assigned. The `--all` flag overrides this to show empty slots. See `_list_worktrees()` in `src/erk/cli/commands/wt/list_cmd.py`.
- **Land cleanup** uses `get_placeholder_branch_name()` to checkout a placeholder before deleting the landed feature branch. This happens even for slots with no pool assignment (the `SLOT_UNASSIGNED` cleanup path), handling cases where someone checked out a branch in a slot without using erk's assignment system. See `_cleanup_slot_without_assignment()` in `src/erk/cli/commands/land_cmd.py`.

<!-- Source: src/erk/cli/commands/submit.py, submit_cmd -->
<!-- Source: src/erk/cli/commands/wt/list_cmd.py, _list_worktrees -->
<!-- Source: src/erk/cli/commands/land_cmd.py, _cleanup_slot_without_assignment -->
<!-- Source: src/erk/cli/commands/slot/common.py, is_placeholder_branch -->

## Why Not Detached HEAD?

An alternative design would use detached HEAD instead of placeholder branches. This was rejected because:

1. **Git UI confusion** — detached HEAD triggers warnings in many tools and confuses agents working in the worktree
2. **Branch-based lookups break** — code that calls `get_current_branch()` returns `None` in detached HEAD, requiring null handling throughout the codebase
3. **Placeholder branches are cheap** — local-only, no remote operations, negligible overhead

## Related Documentation

- [Branch Manager Decision Tree](../architecture/branch-manager-decision-tree.md) — Complete decision framework for `ctx.branch_manager` vs `ctx.git.branch`
- [Branch Manager Abstraction](../architecture/branch-manager-abstraction.md) — BranchManager architecture
