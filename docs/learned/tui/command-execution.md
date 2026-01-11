---
title: Command Execution Strategies
read_when:
  - "executing commands in TUI"
  - "choosing between sync and streaming execution"
  - "implementing command runners"
tripwires:
  - action: "using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL"
    warning: "Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls."
---

# Command Execution Strategies

This guide covers the different strategies for executing commands in erk and when to use each approach.

## Two Strategies

### 1. Streaming Subprocess (Preferred)

**Pattern:** Execute command in subprocess, stream output back to UI in real-time

**Characteristics:**

- Real-time output visibility
- Non-blocking UI
- Requires repository context (`repo_root`)
- Uses background thread for I/O
- Cross-thread communication with `app.call_from_thread()`

**Use when:**

- User needs to see command progress
- Long-running commands (>1 second)
- Interactive TUI context

### 2. Executor Pattern (Legacy)

**Pattern:** Synchronous execution through CommandExecutor protocol

**Characteristics:**

- Blocks until command completes
- No progress visibility
- Simpler implementation
- No repository context needed
- Used in tests and script mode

**Use when:**

- Testing (FakeCommandExecutor)
- Script/non-interactive mode
- Command completes quickly (<100ms)

## Capability Marker Pattern

The code uses `repo_root` as a capability marker to determine execution strategy:

```python
class PlanDetailScreen(Screen):
    def __init__(self, row: PlanRowData, repo_root: str | None = None):
        super().__init__()
        self._row = row
        self._repo_root = repo_root  # Capability marker

    async def execute_command(self, cmd_id: str) -> None:
        if self._repo_root:
            # Streaming subprocess execution
            await self._execute_streaming(cmd_id)
        else:
            # No execution - notify user
            self.notify("Cannot execute: no repository context")
```

## Implementation Example

### Streaming Execution

```python
import subprocess
import threading
from typing import Iterator

def execute_streaming(
    command: list[str],
    cwd: str,
    on_output: Callable[[str], None]
) -> int:
    """Execute command with streaming output.

    Args:
        command: Command and arguments
        cwd: Working directory
        on_output: Callback for each line of output

    Returns:
        Exit code
    """
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,  # CRITICAL: Prevents deadlock if child prompts
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    for line in process.stdout:
        on_output(line.rstrip())

    return process.wait()
```

### Executor Pattern

```python
from abc import ABC, abstractmethod

class CommandExecutor(ABC):
    @abstractmethod
    def execute(self, command: list[str]) -> CommandResult:
        """Execute command synchronously."""
        ...

class RealCommandExecutor(CommandExecutor):
    def execute(self, command: list[str]) -> CommandResult:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True
        )
        return CommandResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr
        )

class FakeCommandExecutor(CommandExecutor):
    def __init__(self, *, responses: dict[str, CommandResult]):
        self._responses = responses

    def execute(self, command: list[str]) -> CommandResult:
        key = " ".join(command)
        return self._responses.get(key, CommandResult(exit_code=1))
```

## Decision Matrix

| Context              | Strategy             | Reason                       |
| -------------------- | -------------------- | ---------------------------- |
| TUI with `repo_root` | Streaming subprocess | User needs progress feedback |
| TUI without context  | Disabled/notify      | Cannot execute safely        |
| Unit tests           | FakeCommandExecutor  | Fast, deterministic          |
| Script mode          | Executor pattern     | Simpler, no UI               |
| Quick commands       | Executor pattern     | No need for streaming        |

## Common Pitfalls

### stdin Inheritance Deadlock

When executing subprocesses from a TUI, child processes inherit stdin from the parent. If the child attempts to prompt for user input (e.g., `click.confirm()` for confirmation dialogs), a deadlock occurs:

1. TUI manages terminal input via Textual event loop
2. Child process tries to read from inherited stdin (same TTY)
3. Neither can proceed → permanent hang

**Prevention:** Always pass `stdin=subprocess.DEVNULL` when spawning subprocesses from TUI code:

```python
process = subprocess.Popen(
    command,
    cwd=cwd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.DEVNULL,  # CRITICAL: Prevents deadlock
    text=True,
    bufsize=1,
)
```

**Note:** This means child processes cannot prompt for input. If a command requires user confirmation, the TUI must handle this before executing (e.g., show confirmation dialog in TUI first, then run command with `--force` or `--yes` flag).

## Related Documentation

- [TUI Streaming Output Patterns](streaming-output.md)
- [Textual Async Best Practices](textual-async.md)
