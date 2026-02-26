---
title: Codespace Tmux Session Persistence
read_when:
  - "working with codespace connect command"
  - "understanding tmux session management in remote codespaces"
  - "debugging session naming or TERM issues in remote environments"
tripwires:
  - action: "starting tmux inside a codespace without setting TERM=xterm-256color"
    warning: "Remote tmux requires TERM=xterm-256color. Without it, terminal rendering breaks silently."
  - action: "using random session names for tmux in codespaces"
    warning: "Use deterministic names for plan sessions (from plan ID) and TTY-derived names for interactive sessions. Random names prevent reconnection."
---

# Codespace Tmux Session Persistence

The codespace connect command uses tmux for persistent sessions in GitHub Codespaces. This document explains the bootstrap pattern, session naming strategy, and common pitfalls.

## Core Pattern: Bootstrap Outside, Session Inside

The connect command uses a two-phase execution model:

1. **Bootstrap phase** (outside tmux): SSH into codespace, set up environment, detect/create tmux session
2. **Session phase** (inside tmux): Attach to session, run implementation commands

This separation ensures the environment is properly configured before any tmux session is created.

## Session Naming Strategy

### Plan Sessions (Deterministic)

When connecting for a plan implementation, the session name is derived from the plan ID:

```
plan-{issue_number}
```

This enables reliable reconnection — if the SSH connection drops, reconnecting finds the existing session by name.

### Interactive Sessions (TTY-Derived)

For interactive connections without a plan context, the session name is derived from the TTY:

```
interactive-{tty_suffix}
```

This prevents session name collisions between multiple interactive connections.

## TERM Environment Variable

Remote tmux requires `TERM=xterm-256color` for correct terminal rendering. The connect command sets this explicitly before creating or attaching to a tmux session.

Without it:

- Colors may not render
- Unicode characters may display incorrectly
- Terminal width detection may fail

## CLI Flag Cascading

The `--session` flag implies `--tmux`:

```bash
erk codespace connect --session  # Automatically enables tmux
```

This prevents the common mistake of requesting a persistent session without enabling the tmux layer that makes persistence possible.

## Session Cleanup

Tmux sessions persist until explicitly killed or the codespace is stopped. The connect command does NOT automatically clean up old sessions.

## Source Code

- `src/erk/cli/commands/codespace/connect_cmd.py` — Main connect command
- `src/erk/cli/commands/codespace/codespace_run.py` — Remote execution helpers

## Related Documentation

- [Composable Remote Commands Pattern](../architecture/composable-remote-commands.md) — SSH command execution patterns
