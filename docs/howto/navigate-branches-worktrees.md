# Navigate Branches and Worktrees

Switch between branches and navigate stacks with shell integration.

## Overview

Navigation commands let you move between branches and worktrees without manually `cd`-ing to directories. They automatically create worktrees when needed, so you can focus on the code rather than filesystem management.

**Prerequisite**: [Shell integration](../tutorials/shell-integration.md) enables these commands to change your current directory. Without it, commands spawn subshells instead.

## Navigate by Branch Name

`erk br co` (alias for `erk branch checkout`) is the most common navigation command. Give it a branch name and it switches you to that branch's worktree:

```bash
erk br co feature/user-auth
```

This command handles several scenarios automatically:

- **Branch has a worktree**: Switches to it
- **Branch exists but has no worktree**: Creates one, then switches
- **Branch only exists on remote**: Creates a tracking branch and worktree
- **Multiple worktrees have the branch**: Prompts you to choose

Use this when you know the branch name and want to work on it.

## Navigate by Worktree Name

`erk wt co` (alias for `erk wt checkout`) navigates by worktree name rather than branch name:

```bash
erk wt co P123-auth-feature-0115
```

This is useful when:

- You see a worktree name in `erk wt list` output
- Multiple worktrees contain the same branch (avoids the prompt)
- You want to return to the root repository: `erk wt co root`

The special keyword `root` always takes you to the original clone location.

## Checkout a PR

`erk pr co` checks out a pull request by number or URL:

```bash
erk pr co 123
erk pr co https://github.com/owner/repo/pull/123
```

This fetches the PR's branch, creates a worktree if needed, and switches to it. Use this when reviewing or iterating on someone else's PR.

## Navigate Stacks

When using [Graphite](../tutorials/graphite-integration.md) for stacked PRs, `erk up` and `erk down` move through the stack:

```bash
erk up      # Move toward leaves (away from trunk)
erk down    # Move toward trunk (toward parent)
```

Stack terminology:

- **Up** = toward children/leaves (away from main)
- **Down** = toward parent (toward main)

```
main
 └── feature-base (erk down from here)
      └── feature-part-1 (current)
           └── feature-part-2 (erk up goes here)
```

After landing a PR, use `--delete-current` to clean up:

```bash
erk up --delete-current    # Land, then move up and delete current worktree
```

Both commands auto-create worktrees for stack branches that don't have them yet.

## Choosing the Right Command

| Scenario                  | Command                |
| ------------------------- | ---------------------- |
| Know the branch name      | `erk br co <branch>`   |
| Know the worktree name    | `erk wt co <worktree>` |
| Return to root repository | `erk wt co root`       |
| Review a PR               | `erk pr co <number>`   |
| Move up the stack         | `erk up`               |
| Move down the stack       | `erk down`             |
| Land PR and navigate up   | `erk pr land --up`     |

## See Also

- [Worktrees](../topics/worktrees.md) - How worktrees work and why erk uses them
- [Shell Integration](../tutorials/shell-integration.md) - Enable directory-changing navigation
