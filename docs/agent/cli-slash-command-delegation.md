# CLI to Slash Command Delegation

## Overview

This pattern describes how erk CLI commands delegate work to Claude slash commands via the `ClaudeExecutor` abstraction. This enables CLI commands to leverage Claude's reasoning capabilities while maintaining testability through dependency injection.

**Related pattern**: [Command-Agent Delegation](command-agent-delegation.md) covers slash command → agent delegation (the layer below this pattern).

## When to Use This Pattern

Use CLI-to-slash-command delegation when:

- **CLI command is a thin wrapper** around an AI-driven workflow
- **User feedback needs streaming** (progress indicators, tool summaries)
- **Work requires Claude's reasoning** (code analysis, conflict resolution)
- **Multiple slash commands** need orchestration in sequence

**Examples of commands using this pattern:**

| CLI Command           | Slash Command(s)                                   | Purpose                      |
| --------------------- | -------------------------------------------------- | ---------------------------- |
| `erk pr submit`       | `/gt:pr-submit`                                    | AI-generated commit + PR     |
| `erk pr auto-restack` | `/erk:auto-restack`                                | Conflict resolution          |
| `erk implement`       | `/erk:plan-implement`, `/fast-ci`, `/gt:pr-submit` | Full implementation workflow |

## Architecture

### ClaudeExecutor Abstraction

The `ClaudeExecutor` ABC (`src/erk/core/claude_executor.py`) provides:

```python
class ClaudeExecutor(ABC):
    @abstractmethod
    def is_claude_available(self) -> bool:
        """Check if Claude CLI is installed and available in PATH."""
        ...

    @abstractmethod
    def execute_command_streaming(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
        debug: bool = False,
    ) -> Iterator[StreamEvent]:
        """Execute slash command and yield events in real-time."""
        ...

    def execute_command(
        self,
        command: str,
        worktree_path: Path,
        dangerous: bool,
        verbose: bool = False,
    ) -> CommandResult:
        """Non-streaming convenience wrapper (collects all events)."""
        ...

    @abstractmethod
    def execute_interactive(self, worktree_path: Path, dangerous: bool) -> None:
        """Replace current process with Claude CLI (for interactive mode)."""
        ...
```

### Three Implementations

| Implementation       | Purpose                                      |
| -------------------- | -------------------------------------------- |
| `RealClaudeExecutor` | Production: subprocess calls to `claude` CLI |
| `FakeClaudeExecutor` | Testing: in-memory tracking, no subprocess   |

### StreamEvent Types

Events emitted during streaming execution:

| Event Type       | Content                         | Usage                                   |
| ---------------- | ------------------------------- | --------------------------------------- |
| `text`           | Claude's output text            | Display to user                         |
| `tool`           | Tool use summary                | Show progress (e.g., "Editing file...") |
| `spinner_update` | Progress indicator text         | Update spinner/status                   |
| `pr_url`         | Pull request URL                | Extract for final display               |
| `pr_number`      | Pull request number (as string) | Extract PR metadata                     |
| `pr_title`       | Pull request title              | Extract PR metadata                     |
| `issue_number`   | Linked GitHub issue number      | Extract for linking                     |
| `error`          | Error message                   | Handle failure                          |

## Implementation Guide

### Step 1: Create CLI Command

```python
# src/erk/cli/commands/pr/my_command.py
from pathlib import Path

import click

from erk.core.context import ErkContext


@click.command("my-command")
@click.pass_obj
def my_command(ctx: ErkContext) -> None:
    """Brief description of what the command does."""
    executor = ctx.claude_executor

    # 1. Check Claude availability
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\n\nInstall from: https://claude.com/download"
        )

    click.echo(click.style("🚀 Starting operation via Claude...", bold=True))
    click.echo("")

    worktree_path = Path.cwd()

    # 2. Stream events and handle them
    for event in executor.execute_command_streaming(
        command="/my:slash-command",
        worktree_path=worktree_path,
        dangerous=False,  # True if command modifies git state
    ):
        if event.event_type == "text":
            click.echo(event.content)
        elif event.event_type == "tool":
            click.echo(click.style(f"   ⚙️  {event.content}", fg="cyan", dim=True))
        elif event.event_type == "error":
            click.echo(click.style(f"   ❌ {event.content}", fg="red"))
            raise click.ClickException(event.content)

    click.echo("\n✅ Operation complete!")
```

### Step 2: Create Corresponding Slash Command

The slash command contains the actual logic. See [command-agent-delegation.md](command-agent-delegation.md) for patterns on structuring slash commands.

### Step 3: Handle Event Types

Common event handling patterns:

```python
# Track state from events
pr_url: str | None = None
error_message: str | None = None
success = True
last_spinner: str | None = None

for event in executor.execute_command_streaming(...):
    if event.event_type == "text":
        click.echo(event.content)
    elif event.event_type == "tool":
        click.echo(click.style(f"   ⚙️  {event.content}", fg="cyan", dim=True))
    elif event.event_type == "spinner_update":
        # Deduplicate spinner updates
        if event.content != last_spinner:
            click.echo(click.style(f"   ⏳ {event.content}", dim=True))
            last_spinner = event.content
    elif event.event_type == "pr_url":
        pr_url = event.content
    elif event.event_type == "error":
        error_message = event.content
        success = False

# Handle final state
if pr_url:
    styled_url = click.style(pr_url, fg="cyan", underline=True)
    clickable_url = f"\033]8;;{pr_url}\033\\{styled_url}\033]8;;\033\\"
    click.echo(f"\n✅ {clickable_url}")

if not success:
    raise click.ClickException(error_message or "Command failed")
```

## Passing Arguments to Slash Commands

Slash commands receive arguments via simple string concatenation:

```python
# Basic command
command = "/erk:auto-restack"

# With flags
if no_squash:
    command = "/erk:auto-restack --no-squash"

# With positional arguments
command = f"/gt:pr-submit {description}"

for event in executor.execute_command_streaming(
    command=command,
    worktree_path=worktree_path,
    dangerous=True,
):
    # Handle events...
```

The slash command is responsible for parsing its own arguments using standard markdown argument parsing conventions.

## Executing Multiple Commands

For workflows requiring multiple slash commands in sequence:

```python
def _build_command_sequence(submit: bool) -> list[str]:
    """Build list of slash commands to execute."""
    commands = ["/erk:plan-implement"]
    if submit:
        commands.extend(["/fast-ci", "/gt:pr-submit"])
    return commands


# Execute sequentially, stopping on first failure
for cmd in commands:
    result = executor.execute_command(cmd, worktree_path, dangerous, verbose)
    all_results.append(result)
    if not result.success:
        break
```

## Testing with FakeClaudeExecutor

The `FakeClaudeExecutor` (`tests/fakes/claude_executor.py`) enables testing without subprocess calls:

```python
from tests.fakes.claude_executor import FakeClaudeExecutor


def test_my_command_executes_slash_command(tmp_path: Path) -> None:
    """Test that CLI command delegates to correct slash command."""
    # Arrange
    executor = FakeClaudeExecutor(claude_available=True)
    ctx = build_context(claude_executor=executor)

    # Act
    runner = CliRunner()
    result = runner.invoke(my_command, obj=ctx)

    # Assert
    assert result.exit_code == 0
    assert len(executor.executed_commands) == 1

    command, worktree_path, dangerous, verbose = executor.executed_commands[0]
    assert command == "/my:slash-command"
    assert dangerous is False


def test_my_command_handles_failure() -> None:
    """Test error handling when slash command fails."""
    executor = FakeClaudeExecutor(
        claude_available=True,
        command_should_fail=True,
    )
    ctx = build_context(claude_executor=executor)

    runner = CliRunner()
    result = runner.invoke(my_command, obj=ctx)

    assert result.exit_code != 0


def test_my_command_checks_claude_availability() -> None:
    """Test error when Claude CLI is not available."""
    executor = FakeClaudeExecutor(claude_available=False)
    ctx = build_context(claude_executor=executor)

    runner = CliRunner()
    result = runner.invoke(my_command, obj=ctx)

    assert result.exit_code != 0
    assert "Claude CLI not found" in result.output
```

### FakeClaudeExecutor Constructor Options

| Parameter                | Type          | Purpose                          |
| ------------------------ | ------------- | -------------------------------- |
| `claude_available`       | `bool`        | Simulate Claude CLI availability |
| `command_should_fail`    | `bool`        | Simulate command failure         |
| `simulated_pr_url`       | `str \| None` | PR URL to emit in events         |
| `simulated_pr_number`    | `int \| None` | PR number to emit                |
| `simulated_pr_title`     | `str \| None` | PR title to emit                 |
| `simulated_issue_number` | `int \| None` | Linked issue number to emit      |
| `simulated_tool_events`  | `list[str]`   | Tool event contents to emit      |

### Assertion Properties

| Property            | Type                                 | Purpose                             |
| ------------------- | ------------------------------------ | ----------------------------------- |
| `executed_commands` | `list[tuple[str, Path, bool, bool]]` | (command, path, dangerous, verbose) |
| `interactive_calls` | `list[tuple[Path, bool]]`            | (worktree_path, dangerous)          |

## Execution Modes

CLI commands using this pattern often support multiple execution modes:

### Interactive Mode (Default)

Uses `execute_interactive()` to replace the current process with Claude CLI:

```python
def _execute_interactive_mode(
    worktree_path: Path, dangerous: bool, executor: ClaudeExecutor
) -> None:
    """Execute in interactive mode (never returns in production)."""
    executor.execute_interactive(worktree_path, dangerous)
```

### Non-Interactive Mode

Uses streaming execution with programmatic event handling:

```python
# With --no-interactive flag
for event in executor.execute_command_streaming(command, worktree_path, dangerous):
    # Handle events programmatically
```

### Script Mode

Outputs shell commands for manual execution:

```python
# With --script flag
def _build_claude_args(slash_command: str, dangerous: bool) -> list[str]:
    args = ["claude", "--permission-mode", "acceptEdits"]
    if dangerous:
        args.append("--dangerously-skip-permissions")
    args.append(slash_command)
    return args
```

## Best Practices

### Do

- Always check `is_claude_available()` before executing commands
- Use streaming (`execute_command_streaming`) for user-facing commands
- Deduplicate spinner updates to avoid visual noise
- Extract and display PR metadata from events
- Test with `FakeClaudeExecutor` - no mock.patch needed

### Don't

- Don't call Claude CLI directly via subprocess - use the abstraction
- Don't ignore error events - always handle them
- Don't hardcode paths - use `Path.cwd()` or context-provided paths
- Don't skip the availability check - users need clear error messages

## Related Documentation

- **[Command-Agent Delegation](command-agent-delegation.md)** - Slash commands delegating to agents (the layer below)
- **[erk-architecture.md](erk-architecture.md)** - Overall architecture patterns
- **[subprocess-wrappers.md](subprocess-wrappers.md)** - Two-layer wrapper pattern
