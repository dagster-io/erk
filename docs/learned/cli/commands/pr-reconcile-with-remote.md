---
title: erk pr reconcile-with-remote Command
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
read_when:
  - "resolving branch divergence from remote"
  - "fixing gt submit 'Branch has been updated remotely' errors"
  - "reconciling local branch with remote tracking branch"
---

# erk pr reconcile-with-remote Command

Reconciles a diverged local branch with its remote tracking branch, handling rebase and conflicts using Claude.

## Usage

```bash
erk pr reconcile-with-remote --dangerous
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

See `src/erk/cli/commands/pr/reconcile_with_remote_cmd.py:62-92` for the implementation sequence.

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
- `gt submit` - What you retry after reconcile-with-remote succeeds
- `/erk:reconcile-with-remote` - The slash command this wraps

## Reference Implementation

See `src/erk/cli/commands/pr/reconcile_with_remote_cmd.py`.
