# Plan: Create TerminalGateway for Testable TTY Detection

## Problem

The codebase has 8+ files with direct `sys.stdin.isatty()` calls that are difficult to test. Currently, tests must use `unittest.mock.patch()` to mock these calls, which is fragile and violates the fake-driven testing architecture.

Example of current anti-pattern:
```python
with patch("erk.cli.commands.land_cmd._is_interactive_terminal", return_value=True):
    result = runner.invoke(cli, ["land", "123", "--script"], ...)
```

## Solution

Create a `Terminal` gateway following the established ABC pattern, allowing TTY detection to be injected via `ErkContext` like other gateways (Git, GitHub, Graphite, etc.).

## Files Using TTY Detection (Migration Targets)

| File | Call Sites | Purpose |
|------|------------|---------|
| `src/erk/cli/commands/land_cmd.py` | 3 | Unresolved comments prompt |
| `src/erk/cli/commands/slot/assign_cmd.py` | 1 | Pool-full prompt |
| `src/erk/cli/commands/branch/create_cmd.py` | 1 | Pool-full prompt |
| `src/erk/cli/commands/plan/start_cmd.py` | 1 | Pool-full prompt |
| `src/erk/cli/commands/implement.py` | 1 | Pool-full prompt |
| `src/erk/cli/commands/plan/create_cmd.py` | 1 | Stdin input detection |
| `src/erk/cli/cli.py` | 1 | Version banner pause |
| `src/erk/hooks/decorators.py` | 1 | Hook stdin reading |

## Implementation

### Phase 1: Create Terminal Gateway

**Create `packages/erk-shared/src/erk_shared/gateway/terminal/`**

1. **`abc.py`** - Abstract interface
```python
from abc import ABC, abstractmethod

class Terminal(ABC):
    @abstractmethod
    def is_stdin_interactive(self) -> bool:
        """Check if stdin is connected to an interactive terminal (TTY)."""
        ...
```

2. **`real.py`** - Production implementation
```python
import sys
from erk_shared.gateway.terminal.abc import Terminal

class RealTerminal(Terminal):
    def is_stdin_interactive(self) -> bool:
        return sys.stdin.isatty()
```

3. **`fake.py`** - Test implementation
```python
from erk_shared.gateway.terminal.abc import Terminal

class FakeTerminal(Terminal):
    def __init__(self, *, is_interactive: bool) -> None:
        self._is_interactive = is_interactive

    def is_stdin_interactive(self) -> bool:
        return self._is_interactive
```

4. **`__init__.py`** - Exports
```python
from erk_shared.gateway.terminal.abc import Terminal as Terminal
from erk_shared.gateway.terminal.fake import FakeTerminal as FakeTerminal
from erk_shared.gateway.terminal.real import RealTerminal as RealTerminal
```

### Phase 2: Integrate into ErkContext

1. **Update `packages/erk-shared/src/erk_shared/context/context.py`**
   - Add `terminal: Terminal` field to `ErkContext` dataclass

2. **Update `src/erk/core/context.py`**
   - Import `RealTerminal`
   - Create `RealTerminal()` in `create_context()`
   - Pass to `ErkContext` constructor

3. **Update test helpers**
   - `context_for_test()` - Add optional `terminal` parameter, default to `FakeTerminal(is_interactive=True)`
   - `minimal_context()` - Include default `FakeTerminal`

### Phase 3: Migrate Call Sites

For each file, replace `sys.stdin.isatty()` with `ctx.terminal.is_stdin_interactive()`:

1. **`land_cmd.py`** - Remove `_is_interactive_terminal()` helper, use `ctx.terminal.is_stdin_interactive()`
2. **`slot/assign_cmd.py`** - Replace direct call
3. **`branch/create_cmd.py`** - Replace direct call
4. **`plan/start_cmd.py`** - Replace direct call
5. **`implement.py`** - Replace direct call
6. **`plan/create_cmd.py`** - Replace direct call
7. **`cli.py`** - Replace direct call
8. **`hooks/decorators.py`** - Replace direct call

### Phase 4: Update Tests

1. **Remove mock patches** - Replace `patch("...._is_interactive_terminal", ...)` with `FakeTerminal` injection
2. **Update test context construction** - Use `env.build_context(terminal=FakeTerminal(is_interactive=True))`

## Files to Create

- `packages/erk-shared/src/erk_shared/gateway/terminal/__init__.py`
- `packages/erk-shared/src/erk_shared/gateway/terminal/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/terminal/real.py`
- `packages/erk-shared/src/erk_shared/gateway/terminal/fake.py`

## Files to Modify

- `packages/erk-shared/src/erk_shared/context/context.py` - Add terminal field
- `src/erk/core/context.py` - Create and inject RealTerminal
- `tests/test_utils/env_helpers.py` - Add terminal to build_context
- 8 command files listed above - Migrate to use ctx.terminal
- `tests/commands/land/test_unresolved_comments.py` - Remove patch, use FakeTerminal

## Success Criteria

- All `sys.stdin.isatty()` calls replaced with `ctx.terminal.is_stdin_interactive()`
- No `unittest.mock.patch` for TTY detection in tests
- All existing tests pass
- CI passes (ty, ruff, pytest)