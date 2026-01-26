# Checkout and Sync PRs

Review and iterate on existing PRs locally.

## Overview

Use this workflow when you need to:

- **Review teammate PRs**: Check out code locally to test or explore
- **Debug remote execution**: Investigate issues from agent-created PRs
- **Take over PRs**: Continue work started by others or remote agents
- **Address review comments**: Make changes in response to PR feedback

## Checking Out a PR

Use `erk pr checkout` (alias: `erk pr co`) to check out a PR into a new worktree:

```bash
# By PR number
erk pr co 123

# By GitHub URL
erk pr co https://github.com/owner/repo/pull/123

# See what would be created (no changes)
erk pr co 123 --dry-run
```

This command:

1. Creates a new worktree for the PR branch
2. Checks out the branch in that worktree
3. Sets up Graphite tracking if applicable

### Flags

| Flag        | Description                        |
| ----------- | ---------------------------------- |
| `--dry-run` | Show what would be done, don't act |
| `--restack` | Run `gt restack` after checkout    |

## Syncing with Remote

When remote changes have been pushed (e.g., by CI, remote agents, or teammates), sync your local branch:

```bash
# Sync using Graphite (recommended for gt-tracked branches)
erk pr sync --dangerous

# Git-only sync (without Graphite)
git fetch origin && git rebase origin/<branch>
```

**Warning**: The `--dangerous` flag is required because syncing can rewrite history. Use `/erk:sync-divergence` if you're unsure about the sync strategy.

### When Divergence Occurs

If your local branch has diverged from remote:

```bash
# Use the automated divergence resolver
/erk:sync-divergence
```

This command analyzes the divergence and chooses the appropriate sync strategy.

## Making Changes

Once checked out, iterate on the PR using standard workflows:

### Using Claude Code

```bash
# Address PR review comments
/erk:pr-address

# General changes with Claude
claude "make the requested changes"
```

### Manual Changes

```bash
# Edit files directly
vim src/my_file.py

# Commit changes
git add -p
git commit -m "Address review feedback"
```

## Submitting Updates

After making changes, push them to the PR:

```bash
# Using Graphite (recommended)
erk pr submit

# Or with force push if needed
gt submit --force --no-interactive
```

For quick iteration:

```bash
# Commit and submit in one step
/local:quick-submit
```

## Landing

When the PR is approved and CI passes:

```bash
# Land the PR (merge and cleanup)
erk land

# Land and move to the next branch in stack
erk land --up
```

The `erk land` command:

1. Merges the PR via GitHub
2. Deletes the feature branch
3. Removes the worktree (if in a linked worktree)
4. Checks out trunk or the next branch

## Common Scenarios

| Scenario                  | Command Sequence                                    |
| ------------------------- | --------------------------------------------------- |
| Review teammate's PR      | `erk pr co 123` then explore/test                   |
| Address my PR's comments  | `erk pr co 123` → `/erk:pr-address` → submit        |
| Take over remote agent PR | `erk pr co 123` → make changes → submit             |
| Debug CI failure          | `erk pr co 123` → run tests locally → fix → submit  |
| Sync after force push     | `/erk:sync-divergence` or `erk pr sync --dangerous` |

## See Also

- [Run Remote Execution](remote-execution.md) - When PRs come from remote agents
- [Resolve Merge Conflicts](conflict-resolution.md) - If sync causes conflicts
- [pr-sync-divergence](../learned/cli/commands/pr-sync-divergence.md) - Divergence resolution details
