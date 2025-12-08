---
title: CLI-to-Slash-Command Delegation
read_when:
  - "creating CLI commands that delegate to slash commands"
  - "using ClaudeExecutor abstraction"
  - "testing commands with FakeClaudeExecutor"
---

# CLI-to-Slash-Command Delegation

Some erk CLI commands delegate to slash commands via the `ClaudeExecutor` abstraction, enabling bash-free Python orchestration with streaming output.

## ClaudeExecutor Abstraction

**Purpose**: Execute slash commands from Python without subprocess calls.

**Interface**:
```python
class ClaudeExecutor(ABC):
    @abstractmethod
    def execute_command(
        self,
        command: str,
        *,
        args: list[str] | None = None,
        cwd: Path | None = None,
    ) -> Generator[StreamEvent]:
        """Execute slash command and stream events."""
```

## StreamEvent Types

Events yielded during command execution:

```python
@dataclass
class OutputEvent:
    """Standard output from command."""
    text: str

@dataclass
class ErrorEvent:
    """Error output from command."""
    text: str

@dataclass
class CompletionEvent:
    """Command completed."""
    exit_code: int
```

## Argument Passing Pattern

Pass arguments as list of strings:

```python
ctx.claude_executor.execute_command(
    "/erk:pr-submit",
    args=["--description", user_description],
    cwd=Path.cwd(),
)
```

**Key principle**: Arguments are strings, not Click option objects.

## Existing Commands Using Pattern

### `erk pr submit`

**File**: `src/erk/cli/commands/pr/submit_cmd.py`

Delegates to `/gt:pr-submit` slash command:

```python
@click.command("submit")
@click.option("--description", help="PR description")
@click.pass_obj
def pr_submit(ctx: ErkContext, description: str | None) -> None:
    """Submit PR via slash command delegation."""
    args = []
    if description:
        args.extend(["--description", description])

    for event in ctx.claude_executor.execute_command(
        "/gt:pr-submit",
        args=args,
        cwd=Path.cwd(),
    ):
        if isinstance(event, OutputEvent):
            click.echo(event.text, nl=False)
        elif isinstance(event, ErrorEvent):
            click.echo(event.text, nl=False, err=True)
        elif isinstance(event, CompletionEvent):
            if event.exit_code != 0:
                raise click.ClickException("Command failed")
```

## FakeClaudeExecutor Testing

Test CLI commands using fake executor:

```python
from erk_shared.claude_executor.fake import FakeClaudeExecutor

def test_pr_submit_delegates_to_slash_command():
    """Test that pr submit delegates to slash command."""
    fake_executor = FakeClaudeExecutor(
        command_outputs={
            "/gt:pr-submit": [
                OutputEvent(text="Creating PR...\\n"),
                OutputEvent(text="PR #123 created\\n"),
                CompletionEvent(exit_code=0),
            ]
        }
    )

    ctx = ErkContext(
        claude_executor=fake_executor,
        # ... other dependencies
    )

    runner = CliRunner()
    result = runner.invoke(pr_submit, obj=ctx)

    assert result.exit_code == 0
    assert "PR #123 created" in result.output

    # Verify command was called
    assert len(fake_executor.executed_commands) == 1
    assert fake_executor.executed_commands[0][0] == "/gt:pr-submit"
```

## Benefits

- **No subprocess calls**: Python invokes slash command directly
- **Streaming output**: Events yielded as they occur
- **Testable**: FakeClaudeExecutor for unit tests
- **Type-safe**: StreamEvent discriminated union

## Related Documentation

- [Two-Phase Operations](../architecture/two-phase-operations.md) - Preflight → AI → Finalize
- [Testing](../testing/) - Testing patterns with fakes
