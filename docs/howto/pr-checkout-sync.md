# Checkout and Sync PRs

Review and iterate on existing PRs locally.

## Overview

When you need to work on a PR that already exists, use `erk pr co` to check it out and `erk pr sync` to sync with remote changes. This is useful when:

- Reviewing a teammate's PR
- Debugging a remotely-executed implementation
- Taking over a PR from another developer
- Continuing work on your own PR from a different machine

## Checking Out a PR

Use `erk pr co` with a PR number or URL:

```bash
erk pr co 123
erk pr co https://github.com/owner/repo/pull/123
```

This fetches the PR's branch, allocates a worktree if needed, and switches to it.

### Options

| Option       | Description                                          |
| ------------ | ---------------------------------------------------- |
| `--no-slot`  | Create a named worktree instead of using a slot      |
| `-f/--force` | Force checkout even if there are uncommitted changes |

## Syncing with Remote

After checking out a PR, sync it with the latest changes from its base branch:

```bash
erk pr sync
```

This fetches the base branch, rebases the PR branch onto it, and force pushes.

### Registering with Graphite

If you want to use Graphite stack commands (`gt submit`, `gt restack`) on a branch you didn't create, use the `--dangerous` flag:

```bash
erk pr sync --dangerous
```

This registers the branch with Graphite. It's called "dangerous" because it modifies Graphite's metadata for a branch someone else may be working on.

## Making Changes

Edit files as you normally would. Use Claude Code for assistance:

```bash
claude
```

To address PR review comments:

```
/erk:pr-address
```

This fetches unresolved review threads and makes the requested changes.

## Submitting Updates

Push your changes and update the PR:

```bash
erk pr submit
```

If the branch has diverged significantly (e.g., after a rebase), you may need to force push:

```bash
erk pr submit -f
```

## Landing

Once the PR is approved and CI passes:

```bash
erk land
```

This merges via GitHub, deletes the branch, and cleans up the worktree.

To navigate to a child branch after landing (useful for stacked PRs):

```bash
erk land --up
```

## Common Scenarios

| Scenario                   | Commands                                                            |
| -------------------------- | ------------------------------------------------------------------- |
| Review teammate's PR       | `erk pr co <num>` then review and comment on GitHub                 |
| Debug remote execution     | `erk pr co <num>` then `erk pr sync` then fix then `erk pr submit`  |
| Take over a PR             | `erk pr co <num>` then `erk pr sync --dangerous` then continue work |
| Continue your PR elsewhere | `erk pr co <num>` then `erk pr sync` then continue work             |

## See Also

- [Run Remote Execution](remote-execution.md) - When PRs come from remote agents
- [Resolve Merge Conflicts](conflict-resolution.md) - If sync causes conflicts
- [Navigate Branches and Worktrees](navigate-branches-worktrees.md) - More navigation options
