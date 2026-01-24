---
title: Subprocess Testing Patterns
read_when:
  - "testing code that uses subprocess"
  - "creating fakes for process execution"
  - "avoiding subprocess mocks in tests"
---

# Subprocess Testing Patterns

This document describes patterns for testing code that executes subprocesses, emphasizing fake-driven testing over mocking.

## Core Principle: Fakes Over Mocks

**Never mock subprocess directly.** Instead, use the gateway abstraction pattern:

1. Define an ABC for the capability
2. Implement a Real class using subprocess
3. Implement a Fake class that simulates behavior in-memory
4. Inject the appropriate implementation

This provides:

- **Predictable tests** - No hidden state from subprocess mocks
- **Fast tests** - No actual process execution
- **Readable tests** - Test intent is clear from fake configuration
- **Realistic behavior** - Fakes can simulate edge cases

## FakeClaudeExecutor Pattern

The `FakeClaudeExecutor` demonstrates the pattern for testing Claude CLI execution:

### Constructor Injection

All behavior is configured via constructor:

```python
# Basic success case
executor = FakeClaudeExecutor(claude_available=True)

# Claude not installed
executor = FakeClaudeExecutor(claude_available=False)

# Command failure
executor = FakeClaudeExecutor(command_should_fail=True)

# PR creation simulation
executor = FakeClaudeExecutor(
    simulated_pr_url="https://github.com/org/repo/pull/123",
    simulated_pr_number=123,
)

# Hook blocking (zero turns)
executor = FakeClaudeExecutor(simulated_zero_turns=True)
```

### Tracking Calls for Assertions

Read-only properties expose calls made:

```python
executor = FakeClaudeExecutor()
executor.execute_command(command="/erk:plan-implement", ...)

# Assert the call was made with expected parameters
assert len(executor.executed_commands) == 1
cmd, path, dangerous, verbose, model = executor.executed_commands[0]
assert cmd == "/erk:plan-implement"
```

### Streaming Events

The fake yields appropriate event types:

```python
executor = FakeClaudeExecutor(
    simulated_tool_events=["Read file.py", "Edit file.py"],
)

events = list(executor.execute_command_streaming(...))
tool_events = [e for e in events if isinstance(e, ToolEvent)]
assert len(tool_events) == 2
```

## Gateway Testing Pattern

For general subprocess operations, the gateway pattern applies:

### Define the Interface

```python
class ClaudeExecutor(ABC):
    @abstractmethod
    def execute_command(self, command: str, ...) -> CommandResult: ...
```

### Real Implementation

```python
class RealClaudeExecutor(ClaudeExecutor):
    def execute_command(self, command: str, ...) -> CommandResult:
        result = subprocess.run(["claude", command, ...])
        return CommandResult(success=result.returncode == 0, ...)
```

### Fake Implementation

```python
class FakeClaudeExecutor(ClaudeExecutor):
    def __init__(self, *, command_should_fail: bool = False):
        self._command_should_fail = command_should_fail
        self._executed_commands: list[tuple] = []

    def execute_command(self, command: str, ...) -> CommandResult:
        self._executed_commands.append((command, ...))
        if self._command_should_fail:
            return CommandResult(success=False, error_message="...")
        return CommandResult(success=True, ...)
```

## Testing Error Scenarios

### Process Startup Failure

```python
executor = FakeClaudeExecutor(
    simulated_process_error="Failed to start Claude CLI: Permission denied"
)

events = list(executor.execute_command_streaming(...))
assert any(isinstance(e, ProcessErrorEvent) for e in events)
```

### No Output

```python
executor = FakeClaudeExecutor(simulated_no_output=True)

events = list(executor.execute_command_streaming(...))
assert any(isinstance(e, NoOutputEvent) for e in events)
```

### Command Failure

```python
executor = FakeClaudeExecutor(command_should_fail=True)

events = list(executor.execute_command_streaming(...))
assert any(isinstance(e, ErrorEvent) for e in events)
```

## Integration Test Considerations

When real subprocess execution is needed (integration tests):

1. Use `@pytest.mark.integration` markers
2. Ensure CI environment has required tools
3. Use real filesystem (tmpdir fixtures)
4. Accept longer test times

See `tests/integration/` for examples of integration tests that execute real subprocesses.

## Related Documentation

- [Erk Test Reference](testing.md) - Overall testing patterns
- [FakeClaudeExecutor](../../../tests/fakes/claude_executor.py) - Reference implementation
- [Subprocess Wrappers](../architecture/subprocess-wrappers.md) - Wrapper function patterns
