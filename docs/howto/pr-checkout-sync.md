# Checkout and Sync PRs

Review and iterate on existing PRs locally.

## Overview

Checking out an existing PR is useful when:

- **Reviewing a teammate's PR** - Run the code locally, test it, leave comments
- **Debugging remote execution results** - A remote agent created a PR but CI failed
- **Taking over an abandoned PR** - Continue work someone else started
- **Continuing from a different machine** - Resume work on a PR you created elsewhere

Erk provides commands to checkout PRs into worktrees, sync them with their base branch, and submit updates.

## Checking Out a PR

Use `erk pr co` to checkout a PR into a worktree:

```bash
# By PR number
erk pr co 123

# By GitHub URL
erk pr co https://github.com/owner/repo/pull/123
```

This creates a new worktree with the PR's branch checked out and assigns it to a slot in your worktree pool.

### Options

| Flag          | Description                                 |
| ------------- | ------------------------------------------- |
| `--no-slot`   | Create worktree without slot assignment     |
| `-f, --force` | Auto-unassign oldest branch if pool is full |

If your worktree pool is full, use `-f` to automatically unassign the oldest branch:

```bash
erk pr co 123 -f
```

## Syncing with Remote

After checking out a PR, sync it with the latest changes from the base branch using `erk pr sync`.

### Git-Only Mode (Default)

The default mode works without Graphite. It fetches the base branch, rebases onto it, and force pushes:

```bash
erk pr sync
```

Use this mode when:

- Your team doesn't use Graphite
- You just need to incorporate upstream changes
- You're doing a one-off review

### Graphite Mode

To register the PR with Graphite for stack management, use the `--dangerous` flag:

```bash
erk pr sync --dangerous
```

This enables standard `gt` commands (`gt submit`, `gt restack`, etc.) on the branch.

Use Graphite mode when:

- Taking over a PR for ongoing development
- Building a stack on top of the PR
- You want full Graphite integration

**Note:** The `--dangerous` flag is required because Graphite sync invokes Claude with `--dangerously-skip-permissions`.

### Requirements

- Must be on a branch (not detached HEAD)
- PR must exist and be OPEN
- PR cannot be from a fork (cross-repo PRs cannot be tracked)

## Making Changes

After checkout and sync, iterate normally:

1. **Edit files** directly or with your editor
2. **Use Claude Code** for AI-assisted changes: `claude`
3. **Address review comments** using: `/erk:pr-address`

The `/erk:pr-address` command fetches unresolved review comments and helps address them systematically.

## Submitting Updates

After making changes, submit with:

```bash
erk pr submit
```

This pushes your changes and updates the PR. If the branch has diverged from remote, use force:

```bash
erk pr submit -f
```

### Options

| Flag            | Description                                   |
| --------------- | --------------------------------------------- |
| `-f, --force`   | Force push when branch has diverged           |
| `--no-graphite` | Skip Graphite enhancement (use git + gh only) |
| `--debug`       | Show diagnostic output                        |

## Landing

When the PR is approved and ready to merge:

```bash
erk land
```

This merges the PR, deletes the remote branch, and cleans up the local worktree.

### Options

| Flag          | Description                                                                 |
| ------------- | --------------------------------------------------------------------------- |
| `--up`        | Navigate to child branch instead of trunk after landing (requires Graphite) |
| `-f, --force` | Skip confirmation prompts                                                   |
| `--no-delete` | Preserve local branch and slot assignment                                   |
| `--dry-run`   | Preview without executing                                                   |

To land and continue working on a stacked PR:

```bash
erk land --up
```

## Common Scenarios

| Scenario                       | Commands                                                                   |
| ------------------------------ | -------------------------------------------------------------------------- |
| Review teammate's PR           | `erk pr co <num>` then review and comment                                  |
| Debug remote execution failure | `erk pr co <num>` then `erk pr sync` then fix then `erk pr submit`         |
| Take over abandoned PR         | `erk pr co <num>` then `erk pr sync --dangerous` then continue development |
| Quick fix on PR                | `erk pr co <num>` then edit then `erk pr submit -f`                        |
| Land and continue stack        | `erk land --up`                                                            |

## See Also

- [Run Remote Execution](remote-execution.md) - When PRs come from remote agents
- [Resolve Merge Conflicts](conflict-resolution.md) - If sync causes conflicts
- [pr-sync-divergence](../learned/cli/commands/pr-sync-divergence.md) - Divergence resolution details
