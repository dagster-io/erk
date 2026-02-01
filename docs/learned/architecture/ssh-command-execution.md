---
title: SSH Command Execution Patterns
read_when:
  - "implementing remote command execution via SSH"
  - "working with codespace connections"
  - "debugging remote setup commands"
  - "choosing between run_ssh_command and exec_ssh_interactive"
---

# SSH Command Execution Patterns

Patterns for executing commands over SSH connections to GitHub Codespaces.

## Method Selection: Interactive vs Non-Interactive

The `Codespace` ABC provides two methods for executing remote commands. **Choosing the wrong method can cause output buffering issues or test failures.**

### Decision Framework

| Use `exec_ssh_interactive()` when:          | Use `run_ssh_command()` when:                 |
| ------------------------------------------- | --------------------------------------------- |
| Command needs real-time terminal streaming  | Command is non-interactive (setup, config)    |
| User interaction required (TUI, prompts)    | Exit code handling is required                |
| Long-running sessions (Claude, vim)         | Output buffering is acceptable                |
| TTY allocation is critical                  | Post-execution logic is needed                |
| Example: `erk codespace run objective next` | Example: Remote git operations, configuration |

### exec_ssh_interactive(): Process Replacement

**Type signature:** `-> NoReturn`

Uses `os.execvp()` to replace the current Python process with the SSH session. No Python code runs after this call.

```python
# Direct terminal streaming with TTY
codespace.exec_ssh_interactive(
    gh_name="my-codespace",
    remote_command="bash -l -c 'claude --dangerously-skip-permissions'"
)
# NO CODE AFTER THIS LINE EXECUTES
```

**Implementation details:**

- Uses `-t` flag for pseudo-terminal allocation
- Process replacement via `os.execvp()`
- Direct stdin/stdout/stderr pass-through
- No exit code available (process replaced)

**When to use:**

- Interactive Claude sessions (`erk codespace run objective next-plan`)
- Any command requiring real-time user input/output
- Long-running processes where buffering would cause "hanging" appearance

### run_ssh_command(): Exit Code Return

**Type signature:** `-> int`

Uses `subprocess.run()` to execute command and return the exit code. Suitable for non-interactive commands.

```python
# Buffered execution with exit code
exit_code = codespace.run_ssh_command(
    gh_name="my-codespace",
    remote_command="git pull"
)
if exit_code != 0:
    click.echo("git pull failed", err=True)
    sys.exit(exit_code)
```

**Implementation details:**

- No `-t` flag (no TTY allocation)
- Returns exit code for error handling
- Output may be buffered
- Subprocess waits for completion

**When to use:**

- Remote setup commands (git pull, uv sync)
- Configuration operations
- Commands where exit code matters for flow control

## Setup vs Shell Modes

### Full Setup Mode (default)

Runs complete environment setup before launching Claude:

```bash
bash -l -c 'git pull && uv sync && source .venv/bin/activate && claude --dangerously-skip-permissions'
```

- `git pull` - Sync latest code
- `uv sync` - Install/update dependencies
- `source .venv/bin/activate` - Activate virtualenv
- `claude --dangerously-skip-permissions` - Launch Claude (codespace isolation provides safety)

### Shell Mode (`--shell`)

Minimal connection for quick debugging:

```bash
bash -l
```

- Uses login shell (`bash -l`) to ensure PATH is set up
- No setup commands executed
- For manual work or quick debugging

## SSH Command Structure

IMPORTANT: The entire remote command must be a single argument. SSH concatenates command arguments with spaces without preserving grouping.

```python
# Interactive pattern (with -t flag)
os.execvp(
    "gh",
    [
        "gh", "codespace", "ssh",
        "-c", codespace.gh_name,  # Codespace name
        "--",
        "-t",  # Force pseudo-terminal allocation (required for interactive TUI)
        remote_command,  # Single string: "bash -l -c '...'"
    ],
)
```

Key flags:

- `-t`: Force pseudo-terminal (required for Claude's interactive TUI)
- `-c`: Specify codespace name
- `bash -l -c`: Login shell to ensure PATH includes `~/.claude/local/`

## Common Pitfalls

### Using run_ssh_command() for Interactive Sessions

**Symptom:** Remote Claude session appears to hang after bootstrap. Output doesn't stream until process completes.

**Root cause:** `run_ssh_command()` lacks TTY allocation (`-t` flag). Output is buffered by SSH/subprocess.

**Fix:** Use `exec_ssh_interactive()` for any command requiring real-time terminal control.

**Historical example:** Issue #6514 - `erk codespace run objective next-plan` appeared to hang. Fixed by switching from `run_ssh_command()` to `exec_ssh_interactive()` (PR #6515).

### Adding Logic After exec_ssh_interactive()

**Symptom:** Code after `exec_ssh_interactive()` never executes. Exit code handling or completion messages don't work.

**Root cause:** `os.execvp()` replaces the process. The Python interpreter is gone.

**Fix:** Remove any post-execution code. Handle cleanup before the call, or accept that process termination is immediate.

## Reference Implementation

- `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` - Abstract interface
- `packages/erk-shared/src/erk_shared/gateway/codespace/real.py` - Production implementation
- `packages/erk-shared/src/erk_shared/gateway/codespace/fake.py` - Test fake
- `src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py` - Interactive example

## Related Topics

- [CLI Output Styling Guide](../cli/output-styling.md) - Using `err=True` for progress messages
- [Exec Script Testing Patterns](../testing/exec-script-testing.md) - Testing interactive methods
- [Composable Remote Commands](composable-remote-commands.md) - Remote command composition patterns
