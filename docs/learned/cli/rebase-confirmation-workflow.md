---
title: Resolve Conflicts Workflow
read_when:
  - "modifying the erk pr resolve-conflicts command"
  - "adding conflict confirmation UI to CLI commands"
  - "understanding how erk handles merge conflict resolution"
tripwires:
  - action: "launching Claude for conflict resolution without showing conflicted files first"
    warning: "Always show conflicted files and get user confirmation before launching Claude. See rebase-confirmation-workflow.md."
  - action: "initiating a rebase inside erk pr resolve-conflicts"
    warning: "erk pr resolve-conflicts does NOT initiate rebases. It requires an active rebase already in progress. Users start the rebase themselves (git rebase, gt restack), then call this command."
---

# Resolve Conflicts Workflow

The `erk pr resolve-conflicts` command resolves merge conflicts from an **already in-progress rebase**. It does not initiate a rebase.

## Source

`src/erk/cli/commands/pr/resolve_conflicts_cmd.py`

## Scope

This command requires a rebase already in progress. If no rebase is detected, it exits with an error:

```
No rebase in progress. Start a rebase first with 'git rebase <branch>',
'gt restack', etc., then run this command when conflicts arise.
```

Users initiate the rebase themselves using standard tools:

```bash
git rebase main        # hits conflicts
erk pr resolve-conflicts

gt restack --no-interactive   # hits conflicts
erk pr resolve-conflicts
```

The command is deliberately scoped to conflict resolution only — it does not call `gt restack` or `git rebase` internally.

## Confirmation Pattern

After detecting a rebase in progress, the command:

1. Checks `ctx.git.rebase.is_rebase_in_progress(cwd)`
2. Retrieves conflicted files via `ctx.git.status.get_conflicted_files(cwd)`
3. Displays each conflicted file with red bold styling
4. Prompts: `click.confirm("Launch Claude to resolve conflicts?", default=True)`
5. On decline, exits with message to run the command again when ready
6. On confirm, launches Claude via `executor.execute_interactive()` with `/erk:pr-resolve-conflicts` command

The `execute_interactive()` call uses `os.execvp()` — code after it never executes.

## Options

- `--dangerous` / `--safe`: Override the `live_dangerously` config setting for Claude permission mode

## Slash Command

Claude is launched with `/erk:pr-resolve-conflicts` (not `/erk:rebase` — that was the old command).

## Related Documentation

- [Prompt Executor Patterns](../architecture/prompt-executor-patterns.md) — `execute_interactive()` process replacement
- [Git and Graphite Quirks](../architecture/git-graphite-quirks.md) — Rebase edge cases
