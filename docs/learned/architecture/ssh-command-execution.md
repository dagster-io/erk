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

## Reference Implementation

- `src/erk/cli/commands/codespace/connect_cmd.py` - Connection command
- `src/erk/core/codespace/` - Codespace registry (ABC, real, fake)

## Related Topics

- [CLI Output Styling Guide](../cli/output-styling.md) - Using `err=True` for progress messages
