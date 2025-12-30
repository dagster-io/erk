---
title: erk-dev Testing Patterns
category_description: erk-dev package testing patterns, release process
read_when:
  - "writing tests for erk-dev commands"
  - "getting context injection errors in erk-dev tests"
  - "testing ErkDevContext-based commands"
---

# erk-dev Testing Patterns

## Context Injection Pattern

erk-dev commands use `ErkDevContext` for dependency injection, which differs from the main erk package's `ErkContext`.

### Correct Pattern

Always invoke commands via the CLI group with context injection:

```python
from click.testing import CliRunner
from erk_dev.cli import cli
from erk_dev.context import ErkDevContext
from erk_shared.git.fake import FakeGit

def test_my_command(tmp_path: Path) -> None:
    fake_git = FakeGit()
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            cli,  # Use CLI group, not individual command
            ["my-command", "--flag"],
            obj=ErkDevContext(git=fake_git),  # Inject context
        )
    assert result.exit_code == 0
```

### Anti-Pattern

Do NOT invoke commands directly without context:

```python
# WRONG - No context injection
from erk_dev.commands.my_command.command import my_command_command
result = runner.invoke(my_command_command, ["--flag"])
# Results in: AttributeError: 'NoneType' object has no attribute 'git'
```

### Why This Matters

- `@click.pass_context` expects `ctx.obj` to be set
- The CLI group (`cli`) is responsible for context initialization
- Direct command invocation bypasses context setup
