# Plan: TTY-based tmux session naming for codespace connect

## Context

`erk codespace connect` uses `tmux new-session -A -s claude` — a single hardcoded session name. This means all terminals share one remote Claude session. The user wants to run multiple concurrent Claude sessions from different terminals, with automatic reconnection from the same terminal, and zero bookkeeping.

## Approach

Derive the tmux session name from the local terminal's TTY device path. Each terminal tab/window gets a unique, stable TTY (e.g., `/dev/ttys003` on macOS, `/dev/pts/3` on Linux). This gives us:

- **Same terminal reconnects** → same TTY → same tmux session → reattaches
- **Different terminals** → different TTYs → different tmux sessions → concurrent Claude instances
- **Zero bookkeeping** — fully deterministic from the environment

## Changes

### `src/erk/cli/commands/codespace/connect_cmd.py`

**1. Add `--session` option** for manual override:

```python
@click.option("--session", "session_name", default=None, help="tmux session name (default: derived from local TTY).")
```

**2. Add TTY-based session name helper:**

```python
def _tty_session_name() -> str:
    try:
        tty_path = os.ttyname(0)  # e.g., /dev/ttys003 or /dev/pts/3
        suffix = tty_path.removeprefix("/dev/").replace("/", "-")
        return f"claude-{suffix}"
    except OSError:
        return "claude"
```

**3. Add user-facing logging** so the user sees what's happening:

```python
session = session_name if session_name is not None else _tty_session_name()
click.echo(f"Connecting to codespace '{codespace.name}' (tmux session: {session})...", err=True)
```

This replaces the current `click.echo(f"Connecting to codespace '{codespace.name}'...", err=True)` line.

**4. Update the tmux command** to use the resolved session name instead of hardcoded `claude`.

Add `import os` at top of file.

### `tests/unit/cli/commands/codespace/test_connect_cmd.py`

Add tests for `_tty_session_name`:
- macOS-style TTY (`/dev/ttys003`) → `claude-ttys003`
- Linux-style TTY (`/dev/pts/3`) → `claude-pts-3`
- Non-TTY (OSError) → `claude` fallback

## Verification

1. Run existing connect_cmd tests via devrun
2. Run new unit tests for `_tty_session_name`
3. Manual: open two terminals, confirm different session names in the log output
