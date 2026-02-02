---
title: SSH Command Execution Patterns
read_when:
  - "implementing remote command execution via SSH"
  - "working with codespace connections"
  - "debugging remote setup commands"
---

# SSH Command Execution Patterns

Patterns for executing commands over SSH connections to GitHub Codespaces.

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

## Choosing Between run_ssh_command() and exec_ssh_interactive()

The `Codespace` ABC provides two methods for SSH execution with different behaviors and use cases.

### Decision Tree

**Is the output interactive? Does the user need real-time streaming?**

- ✅ **Yes** → Use `exec_ssh_interactive()`
  - Interactive TUI (Claude Code)
  - User needs to see output as it happens
  - Commands that require user input

- ❌ **No** → Use `run_ssh_command()`
  - Non-interactive commands (git, uv sync)
  - Commands where you need the exit code
  - Commands where you need to run code after completion

### Comparison Table

| Aspect                  | `run_ssh_command()`         | `exec_ssh_interactive()` |
| ----------------------- | --------------------------- | ------------------------ |
| **Return type**         | `int` (exit code)           | `NoReturn`               |
| **Process**             | Subprocess                  | Replaces current process |
| **TTY allocation**      | Optional                    | Required (`-t` flag)     |
| **Output behavior**     | Buffered, returns when done | Real-time streaming      |
| **Post-execution code** | ✅ Runs                     | ❌ Never runs            |
| **Use case**            | Setup, automation           | Interactive sessions     |

### Method Signatures

See the `Codespace` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` for the full method signatures.

### Example: Interactive Use Case

**Command:** `erk codespace run objective next-plan 42`

```python
# From: src/erk/cli/commands/codespace/run/objective/next_plan_cmd.py
def next_plan(ctx: ErkContext, issue_ref: str, codespace_name: str | None) -> None:
    codespace = require_codespace(ctx)

    # Build remote command
    remote_command = f"erk objective next-plan {issue_ref}"

    # Launch interactive Claude session
    codespace.exec_ssh_interactive(gh_name, remote_command)
    # THIS LINE NEVER RUNS - process was replaced
```

**Why `exec_ssh_interactive()`:**

- Claude Code requires real-time interaction
- User needs to see TUI as it updates
- No post-execution code needed

### Example: Non-Interactive Use Case

**Command:** `erk codespace setup` (hypothetical)

```python
def setup_codespace(ctx: ErkContext, codespace_name: str) -> None:
    codespace = require_codespace(ctx)

    # Run setup commands
    exit_code = codespace.run_ssh_command(gh_name, "git pull && uv sync")

    # Check if setup succeeded
    if exit_code != 0:
        raise click.ClickException("Setup failed")

    # Continue with additional setup
    user_output("✓ Codespace ready")
```

**Why `run_ssh_command()`:**

- Need to check exit code
- Need to run code after completion
- Output streaming not critical

### Tripwire: Using run_ssh_command for Interactive Processes

**Problem:** If you use `run_ssh_command()` to launch Claude Code or other interactive TUI apps, the command appears to hang.

**Root cause:** Without `-t` flag (TTY allocation), the remote process doesn't have a proper terminal and blocks waiting for input.

**Symptom:**

```bash
# Hangs forever, never returns
exit_code = codespace.run_ssh_command(gh_name, "claude")
```

**Solution:** Use `exec_ssh_interactive()` for any command that requires a TTY:

```bash
codespace.exec_ssh_interactive(gh_name, "claude")
```

### Testing Considerations

See [Testing Interactive/NoReturn Gateway Methods](../testing/exec-script-testing.md#testing-interactive-noreturn-gateway-methods) for how to test `exec_ssh_interactive()` calls.

## Reference Implementation

- `src/erk/cli/commands/codespace/connect_cmd.py` - Connection command
- `src/erk/core/codespace/` - Codespace registry (ABC, real, fake)
- `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` - Gateway ABC

## Related Topics

- [CLI Output Styling Guide](../cli/output-styling.md) - Using `err=True` for progress messages
- [Testing Interactive/NoReturn Gateway Methods](../testing/exec-script-testing.md#testing-interactive-noreturn-gateway-methods) - How to test exec_ssh_interactive
