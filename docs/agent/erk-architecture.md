---
title: Erk Architecture Patterns
read_when:
  - "understanding erk architecture"
  - "implementing dry-run patterns"
  - "regenerating context after os.chdir"
---

# Erk Architecture Patterns

This document describes the core architectural patterns specific to the erk codebase.

## Dry-Run via Dependency Injection

**This codebase uses dependency injection for dry-run mode, NOT boolean flags.**

**MUST**: Use DryRun wrappers for dry-run mode
**MUST NOT**: Pass dry_run flags through business logic functions
**SHOULD**: Keep dry-run UI logic at the CLI layer only

### Wrong Pattern

```python
# WRONG: Passing dry_run flag through business logic
def execute_plan(plan, git, dry_run=False):
    if not dry_run:
        git.add_worktree(...)
```

### Correct Pattern

```python
# CORRECT: Rely on injected integration implementation
def execute_plan(plan, git):
    # Always execute - behavior depends on git implementation
    git.add_worktree(...)  # DryRunGit does nothing, RealGit executes

# At the context creation level:
if dry_run:
    git = DryRunGit(real_git)  # or PrintingGit(DryRunGit(...))
else:
    git = real_git  # or PrintingGit(real_git)
```

### Rationale

- Keeps business logic pure and testable
- Dry-run behavior is determined by dependency injection
- No conditional logic scattered throughout the codebase
- Single responsibility: business logic doesn't know about UI modes

## Context Regeneration

**When to regenerate context:**

After filesystem mutations that invalidate `ctx.cwd`:

- After `os.chdir()` calls
- After worktree removal (if removed current directory)
- After switching repositories

### How to Regenerate

Use `regenerate_context()` from `erk.core.context`:

```python
from erk.core.context import regenerate_context

# After os.chdir()
os.chdir(new_directory)
ctx = regenerate_context(ctx, repo_root=repo.root)

# After worktree removal
if removed_current_worktree:
    os.chdir(safe_directory)
    ctx = regenerate_context(ctx, repo_root=repo.root)
```

### Why Regenerate

- `ctx.cwd` is captured once at CLI entry point
- After `os.chdir()`, `ctx.cwd` becomes stale
- Stale `ctx.cwd` causes `FileNotFoundError` in operations that use it
- Regeneration creates NEW context with fresh `cwd` and `trunk_branch`

## Subprocess Execution Wrappers

Erk uses a two-layer pattern for subprocess execution to provide consistent error handling:

- **Integration layer**: `run_subprocess_with_context()` - Raises RuntimeError for business logic
- **CLI layer**: `run_with_error_reporting()` - Prints user-friendly message and raises SystemExit

**Full guide**: See [subprocess-wrappers.md](subprocess-wrappers.md) for complete documentation and examples.

## Time Abstraction for Testing

**NEVER import `time` module directly. ALWAYS use `context.time` abstraction.**

**MUST**: Use `context.time.sleep()` instead of `time.sleep()`
**MUST**: Inject Time dependency through ErkContext
**SHOULD**: Use FakeTime in tests to avoid actual sleeping

### Wrong Pattern

```python
# WRONG: Direct time.sleep() import
import time

def retry_operation(attempt: int) -> None:
    delay = 2.0 ** attempt
    time.sleep(delay)  # Tests will actually sleep!
```

### Correct Pattern

```python
# CORRECT: Use context.time.sleep()
def retry_operation(context: ErkContext, attempt: int) -> None:
    delay = 2.0 ** attempt
    context.time.sleep(delay)  # Fast in tests with FakeTime

# At CLI entry point, RealTime is injected
# In tests, FakeTime is injected
```

### Implementations

**Production (RealTime)**:

```python
from erk_shared.integrations.time.real import RealTime

time = RealTime()
time.sleep(2.0)  # Actually sleeps for 2 seconds
```

**Testing (FakeTime)**:

```python
from erk_shared.integrations.time.fake import FakeTime

fake_time = FakeTime()
fake_time.sleep(2.0)  # Returns immediately, tracks call

# Assert sleep was called with expected duration
assert fake_time.sleep_calls == [2.0]
```

### Real-World Examples

**Retry with exponential backoff** (`src/erk/cli/commands/land_stack/retry.py:100`):

```python
def with_retry(context: ErkContext, func, max_attempts: int = 3):
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception as e:
            if attempt < max_attempts - 1:
                delay = base_delay * (backoff_factor ** attempt)
                context.time.sleep(delay)  # Fast in tests!
            else:
                raise
```

**GitHub API stabilization** (`src/erk/cli/commands/land_stack/execution.py:210`):

```python
# Wait for GitHub to recalculate merge status after base update
ctx.time.sleep(2.0)  # Instant in tests, real wait in production
```

### Testing Benefits

**Without Time abstraction**:

```python
def test_retry_logic():
    # This test takes 6+ seconds to run!
    retry_operation(max_attempts=3, delay=2.0)
    assert operation_succeeded
```

**With Time abstraction**:

```python
def test_retry_logic():
    fake_time = FakeTime()
    ctx = ErkContext.minimal(git=FakeGit(...), cwd=Path("<temp-dir>"))
    ctx = dataclasses.replace(ctx, time=fake_time)

    retry_operation(ctx, max_attempts=3, delay=2.0)

    # Test completes instantly!
    assert fake_time.sleep_calls == [2.0, 4.0, 8.0]
    assert operation_succeeded
```

### Interface

**ABC (erk_shared/integrations/time/abc.py)**:

```python
from abc import ABC, abstractmethod

class Time(ABC):
    """Abstract time operations for dependency injection."""

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        """Sleep for specified number of seconds.

        Args:
            seconds: Number of seconds to sleep
        """
        ...
```

### When to Use

Use `context.time.sleep()` for:

- Retry delays and exponential backoff
- API rate limiting delays
- Waiting for external system stabilization (GitHub API, CI systems)
- Polling intervals

### Migration Path

If you find code using `time.sleep()`:

1. **Add Time parameter**: Add `context: ErkContext` parameter (or just `time: Time`)
2. **Replace call**: Change `time.sleep(n)` to `context.time.sleep(n)`
3. **Update tests**: Use `FakeTime` and verify `sleep_calls`

### Rationale

- **Fast tests**: Tests complete instantly instead of waiting for actual sleep
- **Deterministic**: Test behavior is predictable and reproducible
- **Observable**: Track exact sleep durations called in tests
- **Dependency injection**: Follows erk's DI pattern for all integrations
- **Consistent**: Same pattern as Git, GitHub, Graphite abstractions

## Design Principles

These patterns reflect erk's core design principles:

1. **Dependency Injection over Configuration** - Behavior determined by what's injected, not flags
2. **Explicit Context Management** - Context must be regenerated when environment changes
3. **Layered Error Handling** - Different error handling at different architectural boundaries
4. **Testability First** - Patterns enable easy testing with fakes and mocks
