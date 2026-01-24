# Automatic Merge Conflict Resolution

Handle merge conflicts with AI assistance.

## Overview

Merge conflicts occur when two branches modify the same lines of code. In erk workflows, you'll encounter conflicts during:

- **PR sync** (`erk pr sync`): Syncing your branch with upstream changes
- **Stack rebase** (`gt restack`): Restacking branches after landing a PR
- **Remote rebase**: When GitHub Actions rebases your PR

Erk provides two resolution paths: **local** (resolve in your worktree with Claude) and **remote** (trigger a GitHub Actions workflow).

## Local Resolution

The primary workflow for resolving conflicts locally. Use this when you're in the worktree and want immediate resolution.

### When to Use

- You're already checked out in the branch's worktree
- You want to review the resolution before pushing
- The conflicts require domain knowledge you can provide interactively

### Commands

**CLI command** (outside a Claude session):

```bash
erk pr fix-conflicts --dangerous
```

**Slash command** (inside a Claude Code session):

```
/erk:fix-conflicts
```

Both invoke Claude to resolve conflicts. The `--dangerous` flag acknowledges that Claude will run with elevated permissions.

### How It Works

Claude will:

1. Run `git status` to identify conflicted files
2. Read each conflicted file and understand the conflict markers
3. Resolve conflicts by choosing the appropriate changes
4. Stage the resolved files with `git add`
5. Continue the rebase with `git rebase --continue`
6. Repeat if the rebase reveals more conflicts

### Semantic Conflicts

Sometimes both sides of a conflict are semantically correct but Claude needs guidance on which behavior to preserve. In these cases, Claude will ask for clarification before proceeding.

For example, if both branches renamed the same function differently, Claude will ask which name you prefer.

### After Resolution

Once conflicts are resolved and the rebase completes, push your changes:

- **With Graphite**: `gt submit` or `gt ss`
- **Without Graphite**: `git push --force-with-lease`

## Handling "Branch Updated Remotely" Errors

When `gt submit` fails with "Branch X has been updated remotely", this indicates branch **divergence** - not a merge conflict (yet). Your local branch and the remote branch have both advanced independently.

This commonly happens when:

- CI/autofix added commits to your branch
- You amended a commit locally after pushing
- Another tool or workflow pushed to your branch

### Divergence vs Conflicts

| Situation          | What It Means                             | Command to Use           |
| ------------------ | ----------------------------------------- | ------------------------ |
| Branch diverged    | Local and remote both have new commits    | `erk pr sync-divergence` |
| Rebase in progress | Conflict markers in files during a rebase | `erk pr fix-conflicts`   |

### Sync Divergence Command

**CLI command** (outside a Claude session):

```bash
erk pr sync-divergence --dangerous
```

**Slash command** (inside a Claude Code session):

```
/erk:sync-divergence
```

### How It Works

Claude will:

1. Fetch remote state with `git fetch origin`
2. Analyze divergence (commits on each side)
3. If remote has commits you don't have: fast-forward merge
4. If both sides have commits: rebase your local commits on top of remote
5. If rebase causes conflicts: resolve them automatically
6. Push the synchronized branch

### After Sync

Once synced, retry your original operation:

- **With Graphite**: `gt submit` or `gt ss`
- **Without Graphite**: `git push --force-with-lease`

## Remote Resolution

Resolve conflicts without checking out the branch locally. A GitHub Actions workflow handles the rebase and conflict resolution.

### When to Use

- You don't want to switch to the branch's worktree
- The branch is from a remote execution that you'd prefer to keep separate
- You want a clean squash before resolving conflicts

### Command

```bash
erk pr fix-conflicts-remote
```

Or for a specific PR without being on the branch:

```bash
erk pr fix-conflicts-remote 123
```

### What Happens

The workflow:

1. **Squashes** all commits on the branch (unless `--no-squash`)
2. **Rebases** onto the PR's base branch
3. **Uses Claude** to resolve any merge conflicts
4. **Force pushes** the rebased branch

### Options

| Option        | Description                                       |
| ------------- | ------------------------------------------------- |
| `--no-squash` | Skip squashing commits before rebase              |
| `--model`     | Specify Claude model (default: claude-sonnet-4-5) |

### Examples

```bash
# Basic usage - squash and rebase current branch's PR
erk pr fix-conflicts-remote

# Trigger rebase for a specific PR (without checking out)
erk pr fix-conflicts-remote 123

# Rebase without squashing
erk pr fix-conflicts-remote --no-squash

# Use a specific model
erk pr fix-conflicts-remote --model claude-sonnet-4-5
```

### Requirements

- Either be on a branch with an open PR, or provide a PR number
- GitHub Actions secrets must be configured (`ERK_QUEUE_GH_PAT`, Claude credentials)

## Understanding Stack Conflicts

When using Graphite for stacked PRs, conflicts can propagate through the stack.

### How Stack Conflicts Occur

```
master (updated)
└── feature-base (needs rebase)
    └── feature-part-1 (needs rebase after parent)
        └── feature-part-2 (needs rebase after parent)
```

When `master` advances, each branch in the stack may need rebasing. Conflicts resolved in `feature-base` may reveal new conflicts in `feature-part-1`, and so on.

### Restack Workflow

After landing a PR in a stack:

1. `gt restack` attempts to rebase remaining branches
2. If conflicts occur, resolve them with `/erk:fix-conflicts`
3. After resolution, `gt restack` continues automatically
4. Repeat until the entire stack is rebased

### Navigation During Conflicts

Use stack navigation to move between branches:

```bash
erk up      # Move toward leaves (away from trunk)
erk down    # Move toward trunk (toward parent)
```

See [Navigate Branches and Worktrees](navigate-branches-worktrees.md) for details.

## Manual Resolution (Fallback)

When AI resolution doesn't produce the desired result, fall back to standard git workflow:

1. **Check status**: `git status` shows conflicted files
2. **Edit files**: Open each conflicted file and resolve the `<<<<<<<`, `=======`, `>>>>>>>` markers manually
3. **Stage**: `git add <resolved-files>`
4. **Continue**: `git rebase --continue`
5. **Repeat**: If more conflicts appear, repeat the process
6. **Push**: `git push --force-with-lease` or `gt submit`

## Best Practices

**Sync frequently.** The longer your branch diverges from trunk, the more likely conflicts become. Run `erk pr sync --dangerous` regularly to stay up to date.

**Prefer smaller, focused PRs.** Large PRs touching many files are more likely to conflict. Break work into smaller, independent changes when possible.

**Review resolution before pushing.** After AI-powered conflict resolution, review the changes with `git diff` to ensure the resolution makes sense. The AI might not understand the full context of your changes.

**Use `--force-with-lease`.** When pushing rebased branches, `--force-with-lease` is safer than `--force`. It fails if someone else has pushed to the branch, preventing you from overwriting their work.

## See Also

- [Graphite Integration](../tutorials/graphite-integration.md) - Understanding stacks
- [Navigate Branches and Worktrees](navigate-branches-worktrees.md) - Moving between branches
- [Use the Local Workflow](local-workflow.md) - Standard development cycle
- [Worktrees](../topics/worktrees.md) - How worktrees enable parallel work
