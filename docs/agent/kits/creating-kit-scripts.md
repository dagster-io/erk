---
title: Creating Kit Scripts
read_when:
  - "creating kit scripts"
  - "adding Python CLI commands to kits"
  - "testing kit script commands"
---

# Creating Kit Scripts

Kit scripts are Python Click commands that extend erk's functionality through the kit system.

## File Structure

Kit scripts live in the kit's scripts directory:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/scripts/<kit-name>/<script_name>.py
```

Example: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/scripts/erk/get_closing_text.py`

## Script Template

```python
#!/usr/bin/env python3
"""Brief description of what the script does.

Usage:
    erk kit exec <kit> <command-name>

Output:
    Describe the output format

Exit Codes:
    0: Success
    1: Error (if applicable)
"""

from pathlib import Path

import click


@click.command(name="command-name")
def command_name() -> None:
    """Click command docstring."""
    # Implementation
    click.echo("output")
```

## Registration in kit.yaml

Add the script to the kit's `kit.yaml` under the `scripts:` section:

```yaml
scripts:
  - name: command-name
    path: scripts/<kit-name>/script_name.py
    description: Brief description for help text
```

**Naming convention:** Command names use kebab-case (`get-closing-text`), function names use snake_case (`get_closing_text`). The loader converts hyphens to underscores automatically.

## Testing Pattern

Create tests in: `packages/dot-agent-kit/tests/unit/kits/<kit-name>/test_<script_name>.py`

Use CliRunner for testing Click commands:

```python
from pathlib import Path

from click.testing import CliRunner

from dot_agent_kit.data.kits.<kit>.scripts.<kit>.<script_name> import command_name


def test_command_name(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(command_name)
    assert result.exit_code == 0
```

## Common Patterns

### Reading from .impl/ folder

```python
from erk_shared.impl_folder import read_issue_reference

cwd = Path.cwd()
impl_dir = cwd / ".impl"
if impl_dir.exists():
    issue_ref = read_issue_reference(impl_dir)
```

### JSON output for machine parsing

```python
import json
click.echo(json.dumps({"success": True, "data": result}))
```

### Error handling with exit codes

```python
if error_condition:
    click.echo("Error: description", err=True)
    raise SystemExit(1)
```

## Related Documentation

- **[cli-command-development.md](cli-command-development.md)** - Complete kit CLI command development guide
- **[cli-commands.md](cli-commands.md)** - Python/LLM boundary patterns
- **[dependency-injection.md](dependency-injection.md)** - Using DotAgentContext in commands
