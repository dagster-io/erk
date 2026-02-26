# Add tmux Session Persistence to Codespace Commands

## Context

Running `erk codespace run objective plan 7978` uses `os.execvp()` to SSH into a codespace. If the network drops, the remote process dies and all progress is lost. The fix: wrap remote commands in tmux sessions so users can reconnect after disconnects by re-running the same command.

**Key insight**: `tmux new-session -A -s <name> <command>` handles both cases:
- **First run**: creates a tmux session and runs the command inside it
- **Reconnect**: `-A` attaches to the existing session (command arg is ignored)

The bootstrap (git pull, uv sync, activate) runs OUTSIDE tmux, so on reconnect it's a fast no-op before reattaching.

## Changes

### 1. Add `build_codespace_tmux_command` to `src/erk/core/codespace_run.py`

Add a new function that composes with the existing `build_codespace_ssh_command`:

```python
import re

def _sanitize_tmux_session_name(name: str) -> str:
    sanitized = re.sub(r"[^a-z0-9-]", "-", name.lower())
    sanitized = re.sub(r"-+", "-", sanitized)
    return sanitized.strip("-")

def build_codespace_tmux_command(erk_command: str, *, session_name: str) -> str:
    safe_name = _sanitize_tmux_session_name(session_name)
    tmux_cmd = f"tmux new-session -A -s {safe_name} {erk_command}"
    return build_codespace_ssh_command(tmux_cmd)
```

Produces: `bash -l -c 'git pull && uv sync && source .venv/bin/activate && tmux new-session -A -s plan-7978 erk objective plan 7978'`

No quoting issues — no single quotes inside the outer wrapper, no special chars in session names after sanitization.

### 2. Update `src/erk/cli/commands/codespace/run/objective/plan_cmd.py`

Switch from `build_codespace_ssh_command` to `build_codespace_tmux_command`:

```python
from erk.core.codespace_run import build_codespace_tmux_command

# In run_plan():
remote_cmd = build_codespace_tmux_command(remote_erk_cmd, session_name=f"plan-{issue_ref}")
```

Session name `plan-{issue_ref}` is deterministic — re-running the same command reattaches. Sanitization handles URL-form issue refs (though numeric is typical).

### 3. Update `src/erk/cli/commands/codespace/connect_cmd.py`

Add tmux for Claude mode only (not `--shell`). Insert tmux between setup and claude command:

```python
# Non-shell path (line 66-69):
setup_commands = "git pull && uv sync && source .venv/bin/activate"
claude_command = "claude --dangerously-skip-permissions"
tmux_claude = f"tmux new-session -A -s claude {claude_command}"
remote_command = f"bash -l -c '{export_prefix}{setup_commands} && {tmux_claude}'"
```

`export_prefix` stays in the outer bash (before tmux), so env vars are inherited by the tmux session via normal env inheritance. `--shell` path is unchanged (debug escape hatch).

### 4. Tests

**`tests/unit/core/codespace/test_codespace_run.py`** — add tests for new function:
- `test_build_codespace_tmux_command_includes_bootstrap` — verify git pull, uv sync, activate present
- `test_build_codespace_tmux_command_wraps_in_tmux` — verify `tmux new-session -A -s` and command present
- `test_build_codespace_tmux_command_sanitizes_session_name` — verify `/` → `-` etc.
- `test_build_codespace_tmux_command_uses_login_shell` — verify `bash -l -c`

**`tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py`** — update existing happy-path test to also assert tmux is in the remote command

**`tests/unit/cli/commands/codespace/test_connect_cmd.py`** — update:
- Existing default-mode test: also assert `tmux new-session -A -s claude` in remote command
- Existing `--shell` test: also assert `tmux` NOT in remote command

## Files Modified

| File | Change |
|------|--------|
| `src/erk/core/codespace_run.py` | Add `build_codespace_tmux_command` + `_sanitize_tmux_session_name` |
| `src/erk/cli/commands/codespace/run/objective/plan_cmd.py` | Use `build_codespace_tmux_command` |
| `src/erk/cli/commands/codespace/connect_cmd.py` | Insert tmux in Claude mode |
| `tests/unit/core/codespace/test_codespace_run.py` | Add 4 tests for tmux builder |
| `tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py` | Update assertion |
| `tests/unit/cli/commands/codespace/test_connect_cmd.py` | Update 2 assertions |

## Verification

1. Run unit tests: `pytest tests/unit/core/codespace/test_codespace_run.py tests/unit/cli/commands/codespace/`
2. Run ty type checker on modified files
3. Manual smoke test: `erk codespace run objective plan <issue>`, disconnect WiFi, reconnect WiFi, re-run same command — should reattach to running session
