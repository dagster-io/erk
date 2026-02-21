---
title: erk wt create-from
read_when:
  - "setting up a local worktree for an existing branch"
  - "working with a PR branch that needs a worktree slot"
  - "understanding the difference between erk wt create and erk wt create-from"
---

# erk wt create-from

`erk wt create-from <branch>` allocates a worktree pool slot to an **already-existing** branch.

## Purpose

Use `wt create-from` when you have an existing branch (e.g., from a remote PR, a colleague's branch, or a branch you created outside of erk's worktree pool) and want to set up a local worktree for it.

## Decision Tree

| Scenario                                     | Command                               |
| -------------------------------------------- | ------------------------------------- |
| Start new work (no branch yet)               | `erk wt create <name>`                |
| Set up worktree for existing branch          | `erk wt create-from <branch>`         |
| Pool is full and you need to displace a slot | `erk wt create-from <branch> --force` |

## Behavior

1. **Validates branch is not trunk** — trunk always lives in the root worktree
2. **Auto-fetches remote branches** — if `<branch>` exists on `origin` but not locally, it creates a local tracking branch automatically
3. **Allocates a pool slot** — runs slot allocation, which includes artifact cleanup if a slot is reused
4. **Generates activation scripts** — same as `erk wt create`; use `source <(erk wt create-from <branch> --script)` to navigate to the new worktree

## Force Flag

`--force` (or `-f`) auto-unassigns the oldest occupied slot when the pool is full, then uses that slot for the new branch.

## Code Location

`src/erk/cli/commands/wt/create_from_cmd.py`

## Related Commands

- `erk wt create` — creates a new branch AND a worktree slot
- `erk wt co` — checks out an existing worktree slot by name or number
