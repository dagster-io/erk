# Worktrees

Git worktrees enable parallel development without branch switching.

## The Problem: Context Switching

Traditional git workflows force you to switch branches constantly. Working on a feature, need to fix a bug? Stash your work, switch branches, fix the bug, switch back, unstash. Each switch costs time and mental energy—you lose your place, your terminal history, your editor state.

Worse, you can only be "in" one branch at a time. Need to wait for CI while working on something else? You're juggling again.

## What Are Worktrees?

Git worktrees let you check out multiple branches simultaneously, each in its own directory. Think of it like browser tabs: instead of one tab loading different pages, you have multiple tabs open at once.

```
Traditional:                    With Worktrees:
┌──────────────┐               ┌──────────────┐  ┌──────────────┐
│    repo/     │               │  feature-a/  │  │  feature-b/  │
│ (one branch) │               │  (branch A)  │  │  (branch B)  │
└──────────────┘               └──────────────┘  └──────────────┘
```

Each worktree is a full working directory with its own checked-out files, but they share the same `.git` data. Changes in one worktree don't affect another until you merge.

## Why Erk Uses Worktrees

Worktrees are essential to the plan-oriented workflow for several reasons:

**Plan isolation**: Each plan gets its own worktree. You're implementing authentication in one worktree while an agent works on logging in another. No interference, no conflicts until you're ready.

**Context preservation**: Switch between worktrees and everything is as you left it—open files, terminal history, test results. No stashing, no mental reconstruction.

**Parallel development**: Multiple features progress simultaneously. Wait for CI in one worktree while coding in another. An agent can implement a plan in one worktree while you review code in another.

**Clean PR workflow**: When a PR merges, delete its worktree. Your other work continues undisturbed. No branch cleanup gymnastics.

## Worktree Structure

Erk organizes worktrees in a consistent hierarchy:

```
~/erks/                          # Erks root (configurable via ERKS_DIR)
└── my-project/                  # Erks dir for repository "my-project"
    ├── P123-auth-feature-0115/  # Worktree for plan #123
    ├── P124-fix-tests-0115/     # Worktree for plan #124
    └── P125-add-logging-0116/   # Worktree for plan #125
```

**Erks Root** (`~/erks/`): The top-level directory containing all worktrees. Configure with `ERKS_DIR` environment variable.

**Erks Dir** (`~/erks/<repo>/`): Per-repository directory. Groups all worktrees for one repository together.

**Worktree Path** (`~/erks/<repo>/<name>/`): Individual worktree directories. Each is a complete working directory.

**Naming Convention**: `P{issue}-{slug}-{timestamp}` links each worktree to its GitHub issue. The timestamp ensures uniqueness if you create multiple worktrees for the same plan.

### Root Worktree

The original clone location (wherever you ran `git clone`) is the _root worktree_. It's special—it exists outside the erks directory structure and can't be deleted via `erk wt delete`.

Most daily work happens in non-root worktrees. The root worktree often serves as a "home base" for starting new plans or checking overall repository state.

## Erk Worktrees vs Git Worktrees

A git worktree is just a directory with checked-out files. An erk worktree adds structure:

| Aspect      | Git Worktree | Erk Worktree                       |
| ----------- | ------------ | ---------------------------------- |
| Directory   | Any path     | Organized under `~/erks/`          |
| Branch      | Any branch   | Named to match plan issue          |
| Environment | None         | Python virtualenv (optional)       |
| Plan        | None         | Associated `.impl/` folder         |
| Cleanup     | Manual       | `erk wt delete` handles everything |

Erk provides "batteries included" worktree management—consistent naming, automatic cleanup, plan association, and integration with the broader workflow.

## Common Operations

Erk provides commands for worktree lifecycle management:

- **Create**: `erk wt create` - Creates a new worktree, sets up branch, creates virtual environment
- **List**: `erk wt list` - Shows all worktrees with status (branch, plan, etc.)
- **Switch**: `erk wt checkout` - Change to a different worktree (use with [shell integration](../tutorials/shell-integration.md))
- **Delete**: `erk wt delete` - Removes worktree, cleans up branch and virtual environment
- **Status**: `erk wt status` - Shows current worktree details

Detailed command usage is covered in reference documentation. The key insight is that worktrees aren't manual git operations—erk manages the full lifecycle.

## See Also

- [Shell Integration](../tutorials/shell-integration.md) - Enable fast worktree switching
- [The Workflow](the-workflow.md) - How worktrees fit into plan-oriented development
- [Why GitHub Issues](why-github-issues.md) - How plans connect to worktrees
