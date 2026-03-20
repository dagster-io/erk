---
title: erk pr diverge-fix Command
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
read_when:
  - "resolving branch divergence from remote"
  - "fixing gt submit 'Branch has been updated remotely' errors"
  - "reconciling local branch with remote tracking branch"
---

# erk pr diverge-fix Command

Fixes a diverged local branch with its remote tracking branch, handling rebase and conflicts using Claude.

## Usage

```bash
erk pr diverge-fix
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

| Flag              | Required | Description                                    |
| ----------------- | -------- | ---------------------------------------------- |
| `-d, --dangerous` | No       | Force dangerous mode (skip permission prompts) |
| `--safe`          | No       | Disable dangerous mode (permission prompts on) |

By default, dangerous mode is enabled via the `live_dangerously` config key (default: True).

## Configuration

To disable dangerous mode by default:

```bash
erk config set live_dangerously false
```

When `live_dangerously` is false, commands run in safe mode unless `--dangerous` is explicitly passed.

## How It Works

See `src/erk/cli/commands/pr/diverge_fix_cmd.py:62-92` for the implementation sequence.

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

- `erk pr resolve-conflicts` - Fix conflicts in an in-progress rebase (not divergence)
- `gt submit` - What you retry after diverge-fix succeeds
- `/erk:diverge-fix` - The slash command this wraps

## Reference Implementation

See `src/erk/cli/commands/pr/diverge_fix_cmd.py`.
