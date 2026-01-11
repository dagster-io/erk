# Graphite Integration

An optional enhancement that enables stacked PR workflows when using erk.

## Do You Need This?

**Only if you already use Graphite.** This tutorial assumes you're familiar with [Graphite](https://graphite.dev) and understand stacking concepts (`gt create`, `gt submit`, upstack/downstack).

If you're new to stacked PRs, visit [graphite.dev](https://graphite.dev) first.

**Value prop:** When Graphite is detected, erk uses `gt` under the hood for branch creation and PR submission. Your existing Graphite workflow gets enhanced with plan-driven implementation.

## Setup

### Verify Graphite is Installed

```bash
gt --version
```

If not installed, see [graphite.dev/docs/getting-started](https://graphite.dev/docs/getting-started).

### No Additional Configuration Needed

`erk` auto-detects Graphite. If `gt` is on your PATH, erk uses it automatically.

To verify Graphite is installed and detected:

```bash
erk doctor
```

Look for "Graphite CLI installed" in the output.

## How `erk` Uses Graphite

When Graphite is enabled, erk's core workflow commands use `gt` under the hood.

### Branch Creation

```bash
erk implement 123
```

Under the hood, this runs `gt create` to create a stacked branch. The parent branch is tracked automatically based on your current location.

| Without Graphite                 | With Graphite                     |
| -------------------------------- | --------------------------------- |
| `git checkout -b feature-branch` | `gt create feature-branch`        |
| Parent: trunk only               | Parent: current branch (stacking) |

### PR Submission

```bash
erk pr submit
```

Under the hood, this runs:

1. `gt squash` - Consolidate commits into a clean history
2. `gt restack` - Rebase the stack if needed
3. `gt submit` - Push and create/update PRs for the stack

This ensures your entire stack stays synchronized.

### Landing PRs

```bash
erk land
```

When landing a stacked PR:

1. Merges the PR on GitHub
2. Cleans up the local branch and worktree
3. Restacks child branches automatically

Child branches in the stack are rebased onto the new trunk state.

#### Navigating After Landing

By default, `erk land` returns you to the root worktree. When working in a stack, use `--up` to navigate to the next child branch instead:

```bash
erk land --up
```

This lands the current PR and moves you to the child worktree, allowing you to continue working up the stack.

## Stacking Plans

`erk`'s plan-driven workflow naturally supports stacking. When you implement a second plan while in a feature worktree, it stacks on top.

**Example workflow:**

```bash
# In root worktree, implement first plan
erk implement 100
# Creates worktree-100 stacked on master

# While in worktree-100, implement a dependent plan
erk implement 101
# Creates worktree-101 stacked on the branch from plan 100
```

The stack structure:

```
master
└── feature-from-plan-100
    └── feature-from-plan-101
```

Submit the entire stack with `erk pr submit` from any branch in the stack.

## Stack Navigation

Navigate between branches in your stack just like regular git branching—erk handles the worktree switching automatically as you move up and down.

### Move Up the Stack

```bash
erk up
```

Moves to the child branch (away from trunk). `erk` switches you to the corresponding worktree.

### Move Down the Stack

```bash
erk down
```

Moves to the parent branch (toward trunk). `erk` switches you to the corresponding worktree.

### View the Stack

```bash
erk stack list
```

Shows your stack structure with current position:

```
master
└── feature-auth ← you are here
    └── feature-api
```

## Next Steps

- [Shell Integration](shell-integration.md) - Seamless `cd` when navigating worktrees
- [The Workflow](../topics/the-workflow.md) - Full plan-implement-ship cycle
