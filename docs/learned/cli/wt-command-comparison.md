---
title: Worktree Command Comparison
read_when:
  - "choosing between erk wt create, create-from, and checkout"
  - "setting up a worktree for an existing branch"
  - "understanding worktree slot allocation"
---

# Worktree Command Comparison

## Command Matrix

| Command                               | Branch State Required | Slot State Required   | Creates Branch? | Creates Slot? |
| ------------------------------------- | --------------------- | --------------------- | --------------- | ------------- |
| `erk wt create <name>`                | No branch exists      | Free slot available   | Yes (new)       | Yes           |
| `erk wt create-from <branch>`         | Branch must exist     | Free slot available   | No              | Yes           |
| `erk wt create --from-current-branch` | On a non-trunk branch | Free slot available   | No              | Yes           |
| `erk wt co <slot>`                    | N/A                   | Slot must be occupied | No              | No            |

## When to Use Each

| Scenario                                   | Command                               |
| ------------------------------------------ | ------------------------------------- |
| Starting new work from scratch             | `erk wt create <name>`                |
| Working on someone else's PR branch        | `erk wt create-from <branch>`         |
| Moving current branch into a worktree slot | `erk wt create --from-current-branch` |
| Switching to an already-allocated worktree | `erk wt co <slot>`                    |
| Pool full, need to displace oldest slot    | `erk wt create-from <branch> --force` |

## Key Differences

- **`create`** generates a new branch name from the provided name + timestamp suffix
- **`create-from`** takes an existing branch as-is, including remote branches (auto-fetched)
- **`create --from-current-branch`** is a convenience for "I'm already on the branch I want in a slot"
- **`co`** only navigates to an existing slot — no allocation or branch work

## Related Documentation

- [wt create-from](wt-create-from.md) — Detailed documentation for create-from
