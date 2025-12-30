---
title: Kit CLI Command Development
read_when:
  - "adding new kit CLI commands"
  - "creating kit commands from scratch"
  - "understanding kit command file structure"
---

# Kit CLI Command Development

This guide explains how to add new CLI commands to the erk kit.

## File Structure

Kit CLI commands live in the kit package:

```
packages/erk-kits/src/erk_kits/data/kits/erk/
├── kit.yaml                           # Command registration
└── kit_cli_commands/erk/
    └── your_command.py                # Implementation
```

## Step 1: Create the Command File

Create a Python file in `kit_cli_commands/erk/` with this pattern:

```python
"""Short description of what the command does.

Usage:
    erk exec your-command [options]

Exit Codes:
    0: Success
    1: Error
"""

import json
from pathlib import Path

import click


@click.command(name="your-command")
@click.argument("arg_name")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
def your_command(arg_name: str, output_json: bool) -> None:
    """Brief docstring for --help."""
    # Use Path.cwd() for worktree-scoped operations
    worktree_path = Path.cwd()

    # Implement logic...
    result = do_something(worktree_path, arg_name)

    if output_json:
        click.echo(json.dumps({"success": True, "result": result}))
    else:
        click.echo(f"Result: {result}")
```

## Step 2: Register in kit.yaml

Add entry to `kit_cli_commands:` section:

```yaml
kit_cli_commands:
  # ... existing commands
  - name: your-command
    path: kit_cli_commands/erk/your_command.py
    description: Short description for help text
```

## Invocation

Commands are invoked via:

```bash
erk exec your-command arg_value --json
```

## Key Patterns

1. **Worktree-scoped**: Use `Path.cwd()` for operations relative to current worktree
2. **JSON output**: Always provide `--json` flag for machine-readable output
3. **Exit codes**: Return 0 for success, 1 for errors
4. **Error handling**: Use `click.echo(..., err=True)` for errors, then `raise SystemExit(1)`

## Example Commands

Reference these existing commands for patterns:

- `check_impl.py` - Validation with dry-run mode
- `mark_step.py` - File mutation with JSON output
- `list_sessions.py` - Discovery with filtering options

## Related Documentation

- **[cli-commands.md](cli-commands.md)** — Python/LLM boundary patterns for kit commands
- **[code-architecture.md](code-architecture.md)** — Kit code organization
- **[dependency-injection.md](dependency-injection.md)** — Using DotAgentContext in commands
