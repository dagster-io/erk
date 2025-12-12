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
packages/erk-kits/src/erk_kits/data/kits/<kit-name>/scripts/<kit-name>/<script_name>.py
```

Example: `packages/erk-kits/src/erk_kits/data/kits/erk/scripts/erk/get_closing_text.py`

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

import click

from erk_shared.context.helpers import require_cwd, require_git, require_repo_root


@click.command(name="command-name")
@click.pass_context
def command_name(ctx: click.Context) -> None:
    """Click command docstring."""
    # Get dependencies from context for testability
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    # Implementation using injected dependencies
    branch = git.get_current_branch(cwd)
    click.echo(f"On branch: {branch}")
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

Create tests in: `packages/erk-kits/tests/unit/kits/<kit-name>/test_<script_name>.py`

Use CliRunner with `DotAgentContext.for_test()` for fake-driven testing (Layer 4):

```python
from pathlib import Path

from click.testing import CliRunner

from erk_kits.context import DotAgentContext
from erk_kits.data.kits.<kit>.scripts.<kit>.<script_name> import command_name
from erk_shared.git.fake import FakeGit


def test_command_name(tmp_path: Path) -> None:
    # Arrange: Create fake dependencies
    fake_git = FakeGit()
    fake_git.set_current_branch("feature-branch")

    # Create test context with injected fakes
    ctx = DotAgentContext.for_test(
        git=fake_git,
        cwd=tmp_path,
        repo_root=tmp_path,
    )

    # Act: Invoke command with test context via obj parameter
    runner = CliRunner()
    result = runner.invoke(command_name, obj=ctx)

    # Assert
    assert result.exit_code == 0
    assert "feature-branch" in result.output
```

**Why this pattern?**

- Uses in-memory fakes (no subprocess calls, fast tests)
- Full control over dependencies via `DotAgentContext.for_test()`
- No monkeypatching needed for paths - inject `cwd` directly
- Follows Layer 4 testing strategy (business logic over fakes)

## Common Patterns

### Reading from .impl/ folder

```python
from erk_shared.context.helpers import require_cwd
from erk_shared.impl_folder import read_issue_reference

# Use require_cwd(ctx) instead of Path.cwd() for testability
cwd = require_cwd(ctx)
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
