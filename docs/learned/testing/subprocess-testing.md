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

## FakePromptExecutor Pattern

The `FakePromptExecutor` demonstrates the pattern for testing Claude CLI execution:

### Constructor Injection

All behavior is configured via constructor:

```python
# Basic success case
executor = FakePromptExecutor(available=True)

# Claude not installed
executor = FakePromptExecutor(available=False)

# Command failure
executor = FakePromptExecutor(command_should_fail=True)

# PR creation simulation
executor = FakePromptExecutor(
    simulated_pr_url="https://github.com/org/repo/pull/123",
    simulated_pr_number=123,
)

# Hook blocking (zero turns)
executor = FakePromptExecutor(simulated_zero_turns=True)
```

### Tracking Calls for Assertions

Read-only properties expose calls made:

```python
executor = FakePromptExecutor()
executor.execute_command(command="/erk:plan-implement", ...)

# Assert the call was made with expected parameters
assert len(executor.executed_commands) == 1
cmd, path, dangerous, verbose, model = executor.executed_commands[0]
assert cmd == "/erk:plan-implement"
```

### Streaming Events

The fake yields appropriate event types:

```python
executor = FakePromptExecutor(
    simulated_tool_events=["Read file.py", "Edit file.py"],
)

events = list(executor.execute_command_streaming(...))
tool_events = [e for e in events if isinstance(e, ToolEvent)]
assert len(tool_events) == 2
```

## FakeCIRunner Pattern

The `FakeCIRunner` demonstrates the pattern for testing CI check execution:

### Constructor Injection

Configure check failures via sets:

```python
# All checks pass
runner = FakeCIRunner.create_passing_all()

# Specific checks fail
runner = FakeCIRunner(
    failing_checks={"pytest", "ruff"},
    missing_commands=None,
)

# Simulate missing tools
runner = FakeCIRunner(
    failing_checks=None,
    missing_commands={"prettier"},
)
```

### Result Structure

`CICheckResult` has two fields:

- `passed`: Whether check succeeded
- `error_type`: `"command_not_found"`, `"command_failed"`, or None

### Tracking Calls for Assertions

```python
runner = FakeCIRunner.create_passing_all()
result = runner.run_check(name="pytest", cmd=["pytest"], cwd=Path("/repo"))

# Assert the call was made
assert len(runner.run_calls) == 1
assert runner.check_names_run == ["pytest"]
```

### Testing Failure Scenarios

```python
# Test command failure handling
runner = FakeCIRunner(failing_checks={"ruff"}, missing_commands=None)
result = runner.run_check(name="ruff", cmd=["ruff", "check"], cwd=Path("/repo"))

assert not result.passed
assert result.error_type == "command_failed"

# Test missing command handling
runner = FakeCIRunner(failing_checks=None, missing_commands={"prettier"})
result = runner.run_check(name="prettier", cmd=["prettier", "--check"], cwd=Path("/repo"))

assert not result.passed
assert result.error_type == "command_not_found"
```

## Gateway Testing Pattern

For general subprocess operations, the gateway pattern applies:

### Define the Interface

```python
class PromptExecutor(ABC):
    @abstractmethod
    def execute_command(self, command: str, ...) -> CommandResult: ...
```

### Real Implementation

```python
class ClaudePromptExecutor(PromptExecutor):
    def execute_command(self, command: str, ...) -> CommandResult:
        result = subprocess.run(["claude", command, ...])
        return CommandResult(success=result.returncode == 0, ...)
```

### Fake Implementation

```python
class FakePromptExecutor(PromptExecutor):
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
executor = FakePromptExecutor(
    simulated_process_error="Failed to start Claude CLI: Permission denied"
)

events = list(executor.execute_command_streaming(...))
assert any(isinstance(e, ProcessErrorEvent) for e in events)
```

### No Output

```python
executor = FakePromptExecutor(simulated_no_output=True)

events = list(executor.execute_command_streaming(...))
assert any(isinstance(e, NoOutputEvent) for e in events)
```

### Command Failure

```python
executor = FakePromptExecutor(command_should_fail=True)

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
- [FakePromptExecutor](../../../tests/fakes/fake_prompt_executor.py) - Reference implementation
- [Subprocess Wrappers](../architecture/subprocess-wrappers.md) - Wrapper function patterns
