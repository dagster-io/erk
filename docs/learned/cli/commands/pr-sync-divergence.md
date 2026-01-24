---
title: erk pr sync-divergence Command
read_when:
  - "resolving branch divergence from remote"
  - "fixing gt submit 'Branch has been updated remotely' errors"
  - "syncing local branch with remote tracking branch"
---

# erk pr sync-divergence Command

Syncs a diverged local branch with its remote tracking branch, handling rebase and conflicts using Claude.

## Usage

```bash
erk pr sync-divergence --dangerous
```

## When to Use

This command resolves the common scenario when `gt submit` fails with:

```
Branch has been updated remotely. Pull the latest changes and try again.
```

This happens when:

- Remote branch was updated (force-pushed, rebased, or amended)
- Local and remote have diverged since last sync
- CI workflow pushed changes that conflict with local work

## Flags

| Flag              | Required | Description                                   |
| ----------------- | -------- | --------------------------------------------- |
| `-d, --dangerous` | Yes\*    | Acknowledge Claude runs with skip-permissions |

\*Required by default. Can be disabled via config.

## Configuration

To disable the `--dangerous` flag requirement:

```bash
erk config set fix_conflicts_require_dangerous_flag false
```

This is useful for workflows where you've accepted the risk of Claude executing commands.

## How It Works

1. **Fetch remote state** - Gets latest remote tracking branch
2. **Analyze divergence** - Determines ahead/behind counts
3. **Invoke Claude** - Runs `/erk:sync-divergence` slash command
4. **Rebase if needed** - Claude handles rebase and conflict resolution
5. **Report result** - Success or error with actionable guidance

## Output Patterns

The command uses streaming output to show Claude's progress in real-time:

- Fetching remote state...
- Branch status (ahead/behind counts)
- Claude's analysis and actions
- Final success/failure message

## Error Conditions

| Error                             | Cause                                   |
| --------------------------------- | --------------------------------------- |
| "Not on a branch (detached HEAD)" | Run `git checkout <branch>` first       |
| "No remote tracking branch"       | Branch not pushed or tracking not set   |
| "Semantic decision requires..."   | Conflicts need human judgment           |
| "Claude CLI is required"          | Install Claude from claude.com/download |

## Relationship to Other Commands

- `erk pr fix-conflicts` - Fix conflicts in merge state (not divergence)
- `gt submit` - What you retry after sync-divergence succeeds
- `/erk:sync-divergence` - The slash command this wraps

## Reference Implementation

See `src/erk/cli/commands/pr/sync_divergence_cmd.py`.
