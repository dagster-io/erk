---
title: SSH Command Execution Patterns
read_when:
  - "implementing remote command execution via SSH"
  - "working with codespace connections"
  - "debugging remote setup commands"
last_audited: "2026-02-03"
audit_result: edited
---

# SSH Command Execution Patterns

Patterns for executing commands over SSH connections to GitHub Codespaces.

## Setup vs Shell Modes

### Full Setup Mode (default)

Runs complete environment setup before launching Claude:

```bash
bash -l -c 'git pull && uv sync && source .venv/bin/activate && claude --dangerously-skip-permissions'
```

### Shell Mode (`--shell`)

Minimal connection for quick debugging:

```bash
bash -l
```

## SSH Single-Argument Warning

The entire remote command must be a single argument. SSH concatenates command arguments with spaces without preserving grouping.

Key flags:

- `-t`: Force pseudo-terminal (required for Claude's interactive TUI)
- `-c`: Specify codespace name
- `bash -l -c`: Login shell to ensure PATH includes `~/.claude/local/`

## Choosing Between run_ssh_command() and exec_ssh_interactive()

### Decision Tree

**Is the output interactive? Does the user need real-time streaming?**

- **Yes** → Use `exec_ssh_interactive()` (interactive TUI, user input)
- **No** → Use `run_ssh_command()` (non-interactive, need exit code, need post-execution code)

### Comparison Table

| Aspect                  | `run_ssh_command()`         | `exec_ssh_interactive()` |
| ----------------------- | --------------------------- | ------------------------ |
| **Return type**         | `int` (exit code)           | `NoReturn`               |
| **Process**             | Subprocess                  | Replaces current process |
| **TTY allocation**      | Optional                    | Required (`-t` flag)     |
| **Output behavior**     | Buffered, returns when done | Real-time streaming      |
| **Post-execution code** | Runs                        | Never runs               |
| **Use case**            | Setup, automation           | Interactive sessions     |

### Tripwire: Using run_ssh_command for Interactive Processes

**Problem:** If you use `run_ssh_command()` to launch Claude Code or other interactive TUI apps, the command appears to hang.

**Root cause:** Without `-t` flag (TTY allocation), the remote process doesn't have a proper terminal and blocks waiting for input.

**Solution:** Use `exec_ssh_interactive()` for any command that requires a TTY.

## Reference Implementation

- `src/erk/cli/commands/codespace/connect_cmd.py` - Connection command
- `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py` - Gateway ABC

## Related Topics

- [CLI Output Styling Guide](../cli/output-styling.md) - Using `err=True` for progress messages
- [Testing Interactive/NoReturn Gateway Methods](../testing/exec-script-testing.md#testing-interactive-noreturn-gateway-methods)
