# Worktrees

Git worktrees enable parallel agent execution without filesystem conflicts.

## The Problem: Parallel Agents Need Separate Filesystems

As you become proficient with agentic engineering and model capabilities increase, you can work on tasks of increasing complexity and size. Larger tasks mean higher latency—agents take longer to complete their work. At that point, you want multiple agents working in parallel.

But here's the problem: if two agents work in parallel on the same branch, they're writing to the same location in the filesystem. That doesn't work. They'll overwrite each other's changes, create conflicts mid-execution, and generally make a mess.

Worktrees are the solution. Git can manage multiple working copies of the same repository, each checked out to a different branch in a different directory. This lets you run many agents in parallel, each in its own worktree, without interference.

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

**Parallel agent execution**: The primary use case. Launch multiple agents implementing different plans simultaneously. Each agent has its own worktree, its own branch, its own filesystem. No conflicts, no coordination overhead.

**Plan isolation**: Each plan gets its own worktree. One agent implements authentication while another works on logging. They can't interfere with each other until you're ready to merge.

**Organized structure**: Worktrees live in a predictable hierarchy (`~/.erk/repos/<repo>/worktrees/<worktree>/`), making them easy to find and manage. Each is tied to a specific plan via naming convention.

**Context preservation**: For human work, switching between worktrees preserves your state—open files, terminal history, test results. No stashing required.

## Worktree Structure

Erk organizes worktrees in a consistent hierarchy:

```
~/.erk/repos/                              # Erk repos root
└── my-project/                            # Repo directory
    └── worktrees/                         # Worktrees container
        ├── P123-auth-feature-0115/        # Worktree for plan #123
        ├── P124-fix-tests-0115/           # Worktree for plan #124
        └── P125-add-logging-0116/         # Worktree for plan #125
```

**Erk Root** (`~/.erk/`): Erk's configuration and data directory.

**Repos Dir** (`~/.erk/repos/<repo>/`): Per-repository directory containing worktrees and other repo-specific data.

**Worktrees Dir** (`~/.erk/repos/<repo>/worktrees/`): Container for all worktrees for this repository.

**Naming Convention**: `P{issue}-{slug}-{timestamp}` links each worktree to its GitHub issue. The timestamp ensures uniqueness if you create multiple worktrees for the same plan.

### Root Worktree

The original clone location (wherever you ran `git clone`) is the _root worktree_. It's special—it exists outside the erks directory structure and can't be deleted via `erk wt delete`.

Most daily work happens in non-root worktrees. The root worktree often serves as a "home base" for starting new plans or checking overall repository state.

## Erk Worktrees vs Git Worktrees

Git's built-in `git worktree` command is barebones—it creates a directory and checks out a branch. Everything else is manual. Erk provides substantially more:

| Aspect           | Git Worktree          | Erk Worktree                           |
| ---------------- | --------------------- | -------------------------------------- |
| Directory        | Any path (you choose) | Organized under `~/.erk/repos/`        |
| Navigation       | Manual `cd`           | Shell integration switches directories |
| Environment      | None                  | Runs scripts on switch (e.g., uv sync) |
| Plan association | None                  | Linked to GitHub issue via `.impl/`    |

**Shell integration is key.** With vanilla git worktrees, you manually `cd` between directories and devise your own storage scheme. With erk's [shell integration](../tutorials/shell-integration.md), `erk wt checkout` changes your shell's working directory automatically. You can also configure scripts to run on each switch—for example, syncing a Python virtual environment with `uv sync` whenever you navigate to a worktree.

Note that `erk implement` automatically navigates to a new worktree when starting implementation. The shell integration makes this seamless.

## Common Operations

Erk provides commands for worktree lifecycle management:

- **Create**: `erk wt create` - Creates a new worktree with branch and optional virtual environment
- **List**: `erk wt list` - Shows all worktrees with status (branch, plan, etc.)
- **Switch**: `erk wt checkout` or `erk br co` - Navigate to a worktree (requires [shell integration](../tutorials/shell-integration.md)). Since erk manages the mapping between branches and worktrees, checking out a branch automatically switches to its associated worktree.
- **Delete**: `erk wt delete` - Removes worktree and cleans up branch
- **Status**: `erk wt status` - Shows current worktree details

To get the full benefit of worktrees, [set up shell integration](../tutorials/shell-integration.md). Without it, navigation commands can't change your shell's working directory.

## Slots: Reusing Worktrees in Large Codebases

In large codebases or monorepos, creating a new worktree can take substantial time—git must copy the entire working directory. For repositories with many files, this overhead becomes painful.

Erk solves this with the **slots system**. Instead of creating and destroying worktrees, you allocate a fixed number of worktree "slots" upfront. Erk then manages bookkeeping to assign and unassign branches from these slots.

Conceptually, each plan still gets its own worktree. Physically, the worktrees are reused. When you start implementing a new plan, erk finds an available slot, checks out your branch there, and you're ready to go—without waiting for a fresh copy of the entire repository.

Slots are enabled by default and used automatically by `erk implement`. You can still create standalone worktrees with `erk wt create` for advanced use cases, but most users never need to.

Slot commands:

- `erk slot init-pool` - Initialize pool with a fixed number of worktree slots
- `erk slot list` - List all slots with their current assignment status
- `erk slot assign` - Assign an existing branch to an available slot
- `erk slot unassign` - Remove a branch assignment, freeing the slot
- `erk slot repair` - Clean up stale assignments from pool state

## Why Worktrees Instead of Multiple Clones?

You might wonder: why not just clone the repository multiple times? Worktrees are fundamentally better for several reasons.

**Unified git state.** All worktrees share the same `.git` directory—branches, tags, reflog, remote configuration, everything. Create a branch in one worktree and it's immediately visible in all others. Make a commit and it's in the shared database, accessible everywhere. Run `git fetch` once and all worktrees see the updated refs. With separate clones, each has its own isolated git state. You'd need to fetch in each one, set them up as remotes of each other, or constantly push/pull between them.

**Shared object store.** The `.git/objects` directory contains your entire repository history—all commits, all file contents. Worktrees share this; clones duplicate it. For a repository with substantial history, this difference is massive. One user reported their repo takes 1GB as a clone but only 150MB as a worktree, because only the working directory files are duplicated, not the history.

**Local creation.** Creating a worktree doesn't require network transfer. The objects already exist locally; git just checks out the working directory files. Creating another clone means downloading everything again.

The bottom line: worktrees give you isolated working directories with shared git infrastructure. Clones give you completely isolated repositories. For parallel development in the same codebase, worktrees are the right abstraction.

## See Also

- [Shell Integration](../tutorials/shell-integration.md) - Enable fast worktree switching
- [The Workflow](the-workflow.md) - How worktrees fit into plan-oriented development
- [Why GitHub Issues](why-github-issues.md) - How plans connect to worktrees
