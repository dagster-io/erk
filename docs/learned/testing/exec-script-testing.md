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

## Testing Validation Edge Cases

When testing exec scripts that validate input parameters, follow this pattern to isolate validation logic:

### Setup: Satisfy Prerequisites

Create minimal fixtures to pass earlier checks, isolating the validation under test:

```python
@pytest.fixture
def impl_folder(tmp_path: Path) -> Path:
    """Create minimal .impl folder with issue.json for validation tests."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "issue.json").write_text('{"number": 123}')
    return impl_dir
```

### Test Pattern: Validation Edge Cases

Test all validation boundaries (None, empty, whitespace):

```python
def test_started_fails_without_session_id(impl_folder: Path) -> None:
    """Test missing session ID parameter."""
    result = runner.invoke(
        cli, ["exec", "impl-signal", "started"],
        obj=ErkContext.for_test(cwd=impl_folder.parent)
    )
    assert result.exit_code == 0  # Graceful degradation
    data = json.loads(result.output)
    assert data["success"] is False
    assert data["error_type"] == "session-id-required"

def test_started_fails_with_empty_session_id(impl_folder: Path) -> None:
    """Test empty string session ID."""
    result = runner.invoke(
        cli, ["exec", "impl-signal", "started", "--session-id", ""],
        obj=ErkContext.for_test(cwd=impl_folder.parent)
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False

def test_started_fails_with_whitespace_session_id(impl_folder: Path) -> None:
    """Test whitespace-only session ID."""
    result = runner.invoke(
        cli, ["exec", "impl-signal", "started", "--session-id", "   "],
        obj=ErkContext.for_test(cwd=impl_folder.parent)
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is False
```

### Key Assertions

1. **Exit code 0**: Exec scripts use graceful degradation (see [exec-command-patterns.md](exec-command-patterns.md))
2. **JSON response**: Parse output and check `success` field
3. **Error type**: Verify specific `error_type` for targeted error handling
4. **Message content**: Optionally verify human-readable message for debugging

## Test File Locations

- **Integration tests**: `tests/integration/cli/commands/exec/scripts/`
- **Unit tests**: `tests/unit/cli/commands/exec/scripts/`

**Reference implementation**: See `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` for complete validation testing patterns.

## Pattern: Parameterizing Path.home() for Testability

When functions need home directory paths (for `~/.claude/`, `~/.ssh/`, etc.), use this pattern to maintain testability.

### The Problem

```python
# BAD - Not testable, triggers tripwire
def build_docker_run_args(worktree_path: Path) -> list[str]:
    claude_dir = Path.home() / ".claude"  # Hardcoded!
    ...
```

### The Solution

Make `home_dir` a **required parameter** with no default/fallback:

```python
# GOOD - Testable function
def build_docker_run_args(
    *,
    worktree_path: Path,
    image_name: str,
    interactive: bool,
    home_dir: Path,  # Required, no fallback
) -> list[str]:
    claude_dir = home_dir / ".claude"
    ssh_dir = home_dir / ".ssh"
    ...
```

### CLI Boundary

Call `Path.home()` only in CLI-layer functions that can't be unit tested anyway (e.g., functions using `os.execvp` or subprocess):

```python
# CLI-layer function - acceptable to use Path.home() here
def execute_docker_interactive(...) -> None:
    docker_args = build_docker_run_args(
        worktree_path=worktree_path,
        image_name=image_name,
        interactive=True,
        home_dir=Path.home(),  # At CLI boundary
    )
    os.execvp("docker", docker_args)  # Can't unit test anyway
```

### Testing

Tests pass `tmp_path` for the home directory:

```python
def test_build_docker_run_args_mounts_claude_dir(tmp_path: Path) -> None:
    # Create fake home structure
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    args = build_docker_run_args(
        worktree_path=Path("/path/to/worktree"),
        image_name="erk-local:latest",
        interactive=True,
        home_dir=tmp_path,  # Test with tmp_path
    )

    # Verify mount includes fake home path
    assert any(str(claude_dir) in arg for arg in args)
```

### Why No Default?

Using `home_dir: Path | None = None` with fallback `Path.home()` still triggers the tripwire because the fallback executes in the function body. Making the parameter required:

1. Forces CLI code to explicitly provide `Path.home()`
2. Makes the testability boundary clear
3. Prevents accidental use of real home in tests

**Source example**: `src/erk/cli/commands/docker_executor.py:build_docker_run_args()`

## Related Documentation

- [CLI Testing Patterns](cli-testing.md) - General CLI testing patterns
- [Progress Schema Reference](../planning/progress-schema.md) - For testing progress commands
- Source: `src/erk/cli/commands/exec/scripts/AGENTS.md` - Exec script standards
