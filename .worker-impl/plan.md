# Extend TerminalGateway to Cover All TTY Detection

## Summary

Migrate remaining direct `sys.stdin.isatty()` and `os.isatty()` calls to use the TerminalGateway abstraction for testability.

## Files to Modify

### Gateway Extension
- `packages/erk-shared/src/erk_shared/gateway/terminal/abc.py` - Add new methods
- `packages/erk-shared/src/erk_shared/gateway/terminal/real.py` - Implement new methods
- `packages/erk-shared/src/erk_shared/gateway/terminal/fake.py` - Implement new methods
- `tests/unit/fakes/gateway/terminal/test_fake_terminal.py` - Add tests for new methods

### Migration Targets
- `src/erk/cli/cli.py` - Version banner pause
- `src/erk/hooks/decorators.py` - Hook stdin detection
- `src/erk/core/claude_executor.py` - TTY redirection

## Implementation Steps

### Step 1: Extend Terminal ABC

Add new methods to `Terminal` ABC:

```python
# abc.py
@abstractmethod
def is_stdout_tty(self) -> bool:
    """Check if stdout is connected to a TTY."""
    ...

@abstractmethod
def is_stderr_tty(self) -> bool:
    """Check if stderr is connected to a TTY."""
    ...
```

Implement in `RealTerminal`:
```python
def is_stdout_tty(self) -> bool:
    return os.isatty(1)

def is_stderr_tty(self) -> bool:
    return os.isatty(2)
```

Update `FakeTerminal` constructor and implementation:
```python
def __init__(self, *, is_interactive: bool, is_stdout_tty: bool | None = None, is_stderr_tty: bool | None = None) -> None:
    # Default stdout/stderr to match stdin if not specified
```

### Step 2: Migrate cli.py (Version Banner)

**Current code** (`src/erk/cli/cli.py:110`):
```python
if sys.stdin.isatty():
    click.pause(...)
```

**Approach**: Create a `RealTerminal()` instance locally since this runs before ErkContext exists.

```python
from erk_shared.gateway.terminal.real import RealTerminal

terminal = RealTerminal()
if terminal.is_stdin_interactive():
    click.pause(...)
```

This enables future testability if needed.

### Step 3: Migrate hooks/decorators.py

**Current code** (`src/erk/hooks/decorators.py:61`):
```python
def _read_stdin_once() -> str:
    if sys.stdin.isatty():
        return ""
    return sys.stdin.read()
```

**Approach**: Create `RealTerminal()` at module level or within the function.

```python
from erk_shared.gateway.terminal.real import RealTerminal

def _read_stdin_once() -> str:
    terminal = RealTerminal()
    if terminal.is_stdin_interactive():
        return ""
    return sys.stdin.read()
```

Hooks don't have ErkContext, so local instantiation is appropriate.

### Step 4: Migrate claude_executor.py

**Current code** (`src/erk/core/claude_executor.py:451`):
```python
if not (os.isatty(1) and os.isatty(2)):
    # redirect to /dev/tty
```

**Approach**: `ClaudeExecutor` class should receive `Terminal` via constructor (dependency injection).

1. Update `ClaudeExecutor.__init__` to accept `terminal: Terminal`
2. Change check to use `terminal.is_stdout_tty()` and `terminal.is_stderr_tty()`
3. Update all `ClaudeExecutor` instantiation sites to pass `ctx.terminal`

```python
if not (self._terminal.is_stdout_tty() and self._terminal.is_stderr_tty()):
    # redirect to /dev/tty
```

### Step 5: Add Tests

1. **Fake tests**: Verify `FakeTerminal` returns configured values for new methods
2. **Integration test**: Verify `RealTerminal` correctly detects stdout/stderr TTY state
3. **Command tests**: Any tests affected by the new patterns

## Considerations

- **No behavior change**: This is purely a refactor for testability
- **Backward compatibility**: FakeTerminal defaults stdout/stderr to match stdin if not specified
- **Gateway pattern compliance**: Follow existing 5-file pattern (abc, real, fake, + tests)

## Related Documentation

- `docs/learned/architecture/gateway-abc-implementation.md` - ABC implementation checklist
- `fake-driven-testing` skill - Testing patterns