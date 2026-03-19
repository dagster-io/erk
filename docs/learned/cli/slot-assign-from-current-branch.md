---
title: Slot Assign --from-current-branch
read_when:
  - "modifying slot assign command behavior"
  - "adding --from-current-branch to other commands"
  - "understanding branch switching after slot operations"
tripwires:
  - action: "adding --from-current-branch without handling detached HEAD"
    warning: "When the target branch is checked out in another worktree, fall back to detached HEAD checkout. See slot-assign-from-current-branch.md."
---

# Slot Assign --from-current-branch

The `--from-current-branch` flag on `erk slot assign` assigns the current branch to a pool slot and switches the worktree to a different branch.

## Flag Definition

<!-- Source: src/erk/cli/commands/slot/assign_cmd.py -->

The `--from-current-branch` flag is a boolean `is_flag=True` option, mutually exclusive with the positional `BRANCH` argument. See the flag definition in `src/erk/cli/commands/slot/assign_cmd.py`.

## Target Branch Selection

After assigning the current branch to a slot, the command switches the worktree to a target branch:

1. **Prefer Graphite parent**: `ctx.branch_manager.get_parent_branch(repo.root, current_branch)`
2. **Fall back to trunk**: `ctx.git.branch.detect_trunk_branch(repo.root)`

## Detached HEAD Fallback

<!-- Source: src/erk/cli/commands/slot/assign_cmd.py, slot_assign (detached-HEAD fallback section) -->

If the target branch is already checked out in another worktree, a normal checkout would fail. See the detached-HEAD fallback in `slot_assign()` in `src/erk/cli/commands/slot/assign_cmd.py`: calls `checkout_detached()` when the target branch is in use elsewhere (checked via `is_branch_checked_out()`), otherwise `checkout_branch()`.

## Mirrors Pattern

This mirrors `erk wt create --from-current-branch`, which uses the same Graphite-parent → trunk fallback and detached HEAD handling.

## Skill Rename Convention

The `refac-` prefix convention for refactoring-category skills (e.g., `refac-cli-push-down`, `fdt-refactor-mock-to-fake`, `refac-module-to-subpackage`) was established in the same PR that added this flag.

## Related Documentation

- [Click Flag Patterns](../reference/cli-flag-patterns.md) — Mutual exclusivity and flag conventions
