---
title: Exec Script Testing Patterns
read_when:
  - "testing exec CLI commands"
  - "writing integration tests for scripts"
  - "debugging 'Context not initialized' errors in tests"
  - "debugging flaky tests in parallel execution"
tripwires:
  - action: "using monkeypatch.chdir() in exec script tests"
    warning: "Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors."
  - action: "testing code that reads from Path.home() or ~/.claude/ or ~/.erk/"
    warning: "Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory."
  - action: "using Path.home() directly in production code"
    warning: "Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness."
---

# Exec Script Testing Patterns

Testing patterns for CLI commands in `src/erk/cli/commands/exec/scripts/`.

## Required Pattern: Context Injection

All exec script tests MUST use `ErkContext.for_test()` for dependency injection:

```python
from click.testing import CliRunner
from erk_shared.context import ErkContext
from erk.cli.commands.exec.scripts.my_command import my_command

def test_my_command(tmp_path: Path) -> None:
    """Test using context injection."""
    runner = CliRunner()
    result = runner.invoke(
        my_command,
        ["--json"],
        obj=ErkContext.for_test(cwd=tmp_path),  # REQUIRED
    )
    assert result.exit_code == 0
```

## Anti-Pattern: monkeypatch.chdir()

Do NOT use `monkeypatch.chdir()` for exec script tests:

```python
# WRONG - Causes "Context not initialized" error
def test_my_command_wrong(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # This doesn't inject context!

    runner = CliRunner()
    result = runner.invoke(my_command, ["--json"])
    # FAILS: "Error: Context not initialized"
```

## Why Context Injection?

Exec scripts use `require_cwd(ctx)` and similar helpers that read from `ctx.obj`:

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)  # Reads from ctx.obj.cwd
```

When you use `monkeypatch.chdir()`:

- The process working directory changes
- But `ctx.obj` remains `None`
- `require_cwd(ctx)` fails with "Context not initialized"

When you use `obj=ErkContext.for_test(cwd=...)`:

- The context is properly injected
- `ctx.obj` contains the `ErkContext` instance
- `require_cwd(ctx)` returns the test path

## Sharing Context Across Multiple Invocations

When testing multiple commands in sequence, reuse the same context:

```python
def test_multiple_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    ctx = ErkContext.for_test(cwd=tmp_path)  # Create once

    # First command
    result1 = runner.invoke(command1, ["arg"], obj=ctx)
    assert result1.exit_code == 0

    # Second command (same context)
    result2 = runner.invoke(command2, ["arg"], obj=ctx)
    assert result2.exit_code == 0
```

## Available Context Helpers

From `erk_shared.context.helpers`:

| Helper                   | Returns        | Usage                     |
| ------------------------ | -------------- | ------------------------- |
| `require_cwd(ctx)`       | `Path`         | Current working directory |
| `require_repo_root(ctx)` | `Path`         | Repository root path      |
| `require_git(ctx)`       | `Git`          | Git operations            |
| `require_github(ctx)`    | `GitHub`       | GitHub operations         |
| `require_issues(ctx)`    | `GitHubIssues` | GitHub issues operations  |

## Test File Locations

- **Integration tests**: `tests/integration/cli/commands/exec/scripts/`
- **Unit tests**: `tests/unit/cli/commands/exec/scripts/`

## Related Documentation

- [CLI Testing Patterns](cli-testing.md) - General CLI testing patterns
- [Progress Schema Reference](../planning/progress-schema.md) - For testing progress commands
- Source: `src/erk/cli/commands/exec/scripts/AGENTS.md` - Exec script standards
