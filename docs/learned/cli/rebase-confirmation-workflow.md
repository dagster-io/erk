---
title: Rebase Confirmation Workflow
read_when:
  - "modifying the erk pr rebase command"
  - "adding conflict confirmation UI to CLI commands"
  - "understanding rebase convergence paths"
tripwires:
  - action: "launching Claude for conflict resolution without showing conflicted files first"
    warning: "Always show conflicted files and get user confirmation before launching Claude. See rebase-confirmation-workflow.md."
---

# Rebase Confirmation Workflow

The `erk pr rebase` command shows conflicted files and gets user confirmation before launching Claude for conflict resolution. This prevents users from being dropped into a Claude session without knowing what needs resolving.

## Three Convergence Paths

<!-- Source: src/erk/cli/commands/pr/rebase_cmd.py -->

All three entry paths converge at the same confirmation point:

### 1. Graphite Restack Path

When Graphite is enabled, uses `gt restack --no-interactive`. If restack succeeds (no conflicts), returns immediately. If conflicts remain, falls through to confirmation.

### 2. Git Rebase Path

When Graphite is not enabled and no rebase is in progress, requires `--target` flag. Runs `git rebase` onto target. If rebase succeeds, returns. If conflicts remain, falls through to confirmation.

### 3. In-Progress Rebase Path

Detects an existing rebase in progress via `is_rebase_in_progress()`. When a rebase is in progress, the Graphite tracking validation is **bypassed** — the branch may be in a detached HEAD state during rebase, making tracking checks invalid. The code at `rebase_cmd.py:97` checks `is_rebase_in_progress()` first and skips the `is_branch_tracked()` assertion. Displays "Rebase in progress" message and falls through to confirmation.

## Confirmation Pattern

After any path produces conflicts, the command:

1. Retrieves conflicted files via `ctx.git.status.get_conflicted_files(cwd)`
2. Displays each file with red bold styling
3. Prompts: `click.confirm("Launch Claude to resolve conflicts?", default=True)`
4. On decline, exits gracefully
5. On confirm, launches Claude via `executor.execute_interactive()` with `/erk:rebase` command

The `execute_interactive()` call uses `os.execvp()` — code after it never executes.

## Test Patterns

Four test cases cover the confirmation workflow:

- User confirms launch → Claude is invoked
- User declines launch → graceful exit
- No conflicted files → skips confirmation
- Graphite restack success → returns without confirmation

## Related Documentation

- [Prompt Executor Patterns](../architecture/prompt-executor-patterns.md) — `execute_interactive()` process replacement
- [Git and Graphite Quirks](../architecture/git-graphite-quirks.md) — Rebase edge cases
