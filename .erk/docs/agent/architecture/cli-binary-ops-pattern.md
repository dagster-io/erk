---
title: Ops Pattern for External CLI Binaries
read_when:
  - "wrapping external CLI binary"
  - "testing subprocess calls"
  - "creating fake for external tool"
---

# Ops Pattern for External CLI Binaries

When your code needs to invoke external CLI binaries (like `claude`, `gh`, `gt`), use the Ops pattern to enable fast, reliable testing.

## The Pattern

1. **ABC Interface** (`XxxOps`) - Defines the operations
2. **Real Implementation** (`RealXxxOps`) - Calls the actual binary via subprocess
3. **Fake Implementation** (`FakeXxxOps`) - In-memory for testing

## Example: ClaudeCliOps

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import subprocess

@dataclass(frozen=True)
class CommandExecutionResult:
    """Result of command execution."""
    returncode: int

class ClaudeCliOps(ABC):
    """Abstract interface for executing Claude CLI commands."""

    @abstractmethod
    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        """Execute a Claude Code slash command."""
        pass


class RealClaudeCliOps(ClaudeCliOps):
    """Real implementation using subprocess."""

    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        cmd = ["claude", "--print", f"/{command_name}"]
        process = subprocess.Popen(cmd, cwd=cwd, ...)
        returncode = process.wait()
        return CommandExecutionResult(returncode=returncode)


class FakeClaudeCliOps(ClaudeCliOps):
    """Fake implementation for testing."""

    def __init__(self) -> None:
        self._executions: list[tuple[str, Path, bool]] = []
        self._next_returncode: int = 0
        self._should_raise_file_not_found: bool = False

    def execute_command(
        self,
        command_name: str,
        cwd: Path,
        json_output: bool,
    ) -> CommandExecutionResult:
        self._executions.append((command_name, cwd, json_output))

        if self._should_raise_file_not_found:
            raise FileNotFoundError("claude CLI not found")

        return CommandExecutionResult(returncode=self._next_returncode)

    # Configuration methods for tests
    def set_next_returncode(self, returncode: int) -> None:
        self._next_returncode = returncode

    def set_file_not_found_error(self, should_raise: bool) -> None:
        self._should_raise_file_not_found = should_raise

    # Query methods for assertions
    @property
    def executions(self) -> list[tuple[str, Path, bool]]:
        return list(self._executions)
```

## Using in Business Logic

Inject the ops dependency:

```python
def execute_command_impl(
    command_name: str,
    json: bool,
    cli_ops: ClaudeCliOps,  # Dependency injection
) -> int:
    result = cli_ops.execute_command(command_name, Path.cwd(), json)
    return result.returncode
```

## Using in CLI Entry Points

CLI creates the real implementation:

```python
@click.command()
def execute(command_name: str, json: bool) -> None:
    cli_ops = RealClaudeCliOps()  # Real impl at CLI boundary
    exit_code = execute_command_impl(command_name, json, cli_ops)
    raise SystemExit(exit_code)
```

## Testing with Fakes

```python
def test_successful_execution(fake_cli_ops: FakeClaudeCliOps):
    fake_cli_ops.set_next_returncode(0)

    exit_code = execute_command_impl("test", False, fake_cli_ops)

    assert exit_code == 0
    assert fake_cli_ops.executions == [("test", Path.cwd(), False)]


def test_cli_not_found(fake_cli_ops: FakeClaudeCliOps):
    fake_cli_ops.set_file_not_found_error(True)

    with pytest.raises(FileNotFoundError):
        execute_command_impl("test", False, fake_cli_ops)
```

## Key Benefits

1. **Fast tests** - No subprocess startup, no network calls
2. **Deterministic** - Control exact responses
3. **Inspectable** - Assert on what was called
4. **Isolated** - No external dependencies

## Related

- [Subprocess Wrappers](subprocess-wrappers.md) - For internal subprocess calls
- [Erk Test Reference](../testing/testing.md) - Erk-specific fakes
