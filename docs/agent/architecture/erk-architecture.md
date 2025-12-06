---
title: Erk Architecture Patterns
read_when:
  - "understanding erk architecture"
  - "implementing dry-run patterns"
  - "regenerating context after os.chdir"
tripwires:
  - action: "passing dry_run boolean flags through function parameters"
    warning: "Use dependency injection with DryRunGit/DryRunGitHub wrappers instead of boolean flags."
  - action: "calling os.chdir() in erk code"
    warning: "After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError."
  - action: "importing time module or calling time.sleep()"
    warning: "Use context.time.sleep() for testability. Direct time.sleep() makes tests slow."
  - action: "implementing CLI flags that affect post-mutation behavior"
    warning: "Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk pr land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target)."
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

## TUI Exit-with-Command Pattern

The TUI can request command execution after exit. This allows the TUI to trigger CLI commands that require a fresh terminal (not running inside Textual).

### App Side (tui/app.py)

```python
class ErkDashApp(App):
    def __init__(self, ...):
        ...
        self.exit_command: str | None = None  # Command to run after exit

# In a ModalScreen:
def _on_confirmed(self, result: bool | None) -> None:
    if result is True:
        app = self.app
        if isinstance(app, ErkDashApp):
            app.exit_command = "erk implement 123"
        self.dismiss()
        self.app.exit()
```

### CLI Side (cli/commands/list_cmd.py)

```python
app = ErkDashApp(provider, filters)
app.run()

# After TUI exits, check for command to execute
if app.exit_command:
    import os
    import shlex
    args = shlex.split(app.exit_command)
    os.execvp(args[0], args)  # Replaces current process
```

### When to Use

Use this pattern when:

- TUI action requires fresh terminal output (not Textual rendering)
- Command needs to run interactively after TUI closes
- Chaining from TUI to another CLI command

### Testing Considerations

When mocking `ErkDashApp` in tests, include the `exit_command` attribute:

```python
class MockApp:
    def __init__(self, provider, filters, refresh_interval):
        self.exit_command: str | None = None  # Required attribute

    def run(self):
        pass
```

## Integration Layer Directory Structure

Erk uses a consistent directory structure for all integration layers (git, github, graphite, etc). Each integration follows the ABC/Real/Fake/DryRun pattern.

### Standard Directory Layout

```
packages/erk-shared/src/erk_shared/
├── git/                           # Core git integration
│   ├── __init__.py                # Re-exports all implementations
│   ├── abc.py                     # ABC interface definition
│   ├── real.py                    # Production implementation
│   ├── fake.py                    # In-memory test implementation
│   ├── dry_run.py                 # No-op wrapper for dry-run mode
│   └── printing.py                # (Optional) Wrapper that logs operations
├── github/                        # GitHub API integration
│   ├── __init__.py
│   ├── abc.py
│   ├── real.py
│   └── fake.py
└── integrations/                  # Domain-specific integrations
    ├── erk_wt/                    # Erk worktree operations
    │   ├── __init__.py
    │   ├── abc.py
    │   ├── real.py
    │   └── fake.py
    ├── graphite/                  # Graphite stack operations
    │   ├── __init__.py
    │   ├── abc.py
    │   ├── real.py
    │   └── fake.py
    └── time/                      # Time abstraction
        ├── __init__.py
        ├── abc.py
        ├── real.py
        └── fake.py
```

### Standard Files

**`abc.py`** - Interface definition:

```python
from abc import ABC, abstractmethod

class MyIntegration(ABC):
    """Abstract interface for MyIntegration operations."""

    @abstractmethod
    def do_operation(self, arg: str) -> str:
        """Perform operation with given argument."""
        ...
```

**`real.py`** - Production implementation:

```python
import subprocess
from erk_shared.my_integration.abc import MyIntegration

class RealMyIntegration(MyIntegration):
    """Production implementation using subprocess."""

    def do_operation(self, arg: str) -> str:
        result = subprocess.run(
            ["my-cli", "operation", arg],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
```

**`fake.py`** - Test implementation:

```python
from erk_shared.my_integration.abc import MyIntegration

class FakeMyIntegration(MyIntegration):
    """In-memory fake for testing."""

    def __init__(self) -> None:
        self.operations_called: list[str] = []

    def do_operation(self, arg: str) -> str:
        self.operations_called.append(arg)
        return f"fake-result-{arg}"
```

**`dry_run.py`** - No-op wrapper (optional):

```python
from erk_shared.my_integration.abc import MyIntegration

class DryRunMyIntegration(MyIntegration):
    """No-op wrapper that tracks but doesn't execute operations."""

    def __init__(self, delegate: MyIntegration) -> None:
        self.delegate = delegate
        self.operations: list[str] = []

    def do_operation(self, arg: str) -> str:
        self.operations.append(f"do_operation({arg})")
        return ""  # No-op, return empty or default value
```

**`__init__.py`** - Re-export pattern:

```python
"""MyIntegration operations."""

from erk_shared.my_integration.abc import MyIntegration
from erk_shared.my_integration.real import RealMyIntegration
from erk_shared.my_integration.fake import FakeMyIntegration

__all__ = [
    "MyIntegration",      # ABC interface
    "RealMyIntegration",  # Production implementation
    "FakeMyIntegration",  # Test implementation
]
```

### Integration Locations

**Core integrations** (used across the codebase):

- `packages/erk-shared/src/erk_shared/git/` - Git operations
- `packages/erk-shared/src/erk_shared/github/` - GitHub API
- `packages/erk-shared/src/erk_shared/graphite/` - Graphite stack operations

**Domain integrations** (specific domains):

- `packages/erk-shared/src/erk_shared/integrations/<name>/` - Domain-specific operations

### When to Create a New Integration

**Create a new integration when:**

- Wrapping external CLI tool (git, gh, gt)
- Wrapping external API (GitHub REST API)
- Abstracting system operations (time, filesystem)
- Isolating subprocess calls for testing

**Extend existing integration when:**

- Adding method to existing tool (e.g., new git operation)
- Enhancing existing functionality
- Operation fits natural domain of existing integration

### Import Pattern

**From consumers:**

```python
# Import from top-level package (uses __init__.py re-exports)
from erk_shared.git import Git, RealGit, FakeGit
from erk_shared.github import GitHub, RealGitHub, FakeGitHub
from erk_shared.integrations.erk_wt import ErkWtKit, RealErkWtKit, FakeErkWtKit
```

**Not this:**

```python
# DON'T import from implementation files directly
from erk_shared.git.real import RealGit  # Bypasses __init__.py
```

### Testing All Four Layers

When adding a method to an integration ABC:

1. **ABC**: Add abstract method signature
2. **Real**: Implement with subprocess/API calls
3. **Fake**: Implement with in-memory tracking
4. **DryRun**: Add no-op wrapper (if integration has dry-run layer)

**Example workflow:**

```python
# 1. ABC - Add method signature
class Git(ABC):
    @abstractmethod
    def get_branch_upstream(self, path: Path, branch: str) -> str | None:
        """Get upstream tracking branch."""
        ...

# 2. Real - Implement with git CLI
class RealGit(Git):
    def get_branch_upstream(self, path: Path, branch: str) -> str | None:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{u}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else None

# 3. Fake - Implement with in-memory state
class FakeGit(Git):
    def __init__(self) -> None:
        self.upstream_branches: dict[str, str] = {}

    def get_branch_upstream(self, path: Path, branch: str) -> str | None:
        return self.upstream_branches.get(branch)

# 4. DryRun - Add no-op wrapper
class DryRunGit(Git):
    def get_branch_upstream(self, path: Path, branch: str) -> str | None:
        # Delegate to wrapped implementation (doesn't execute git)
        return self.delegate.get_branch_upstream(path, branch)
```

### Migration Notes

If you find code that should be an integration but isn't:

1. **Create integration directory** with abc.py, real.py, fake.py
2. **Extract subprocess calls** into Real implementation
3. **Write Fake implementation** for testing
4. **Update consumers** to use injected dependency instead of direct calls
5. **Update tests** to use Fake instead of mocking subprocess

## Branch Context Detection

Commands that need to behave differently on trunk vs feature branches use the branch context pattern.

### The BranchContext Pattern

```python
@dataclass(frozen=True)
class BranchContext:
    """Branch context information for current git repository.

    Attributes:
        is_on_trunk: True if current branch is trunk (main/master)
        current_branch: Name of the current branch
        trunk_branch: Name of the trunk branch (main or master)
    """
    is_on_trunk: bool
    current_branch: str
    trunk_branch: str
```

### Helper Function

```python
def get_branch_context(git: Git, path: Path) -> BranchContext:
    """Determine branch context for a repository path.

    Detects:
    - Current branch name
    - Trunk branch name (prefers 'main', falls back to 'master')
    - Whether current branch is trunk

    Args:
        git: Git integration for querying branch information
        path: Path to git repository or worktree

    Returns:
        BranchContext with trunk detection information
    """
    current_branch = git.get_current_branch(path)
    trunk_branch = "main" if git.branch_exists(path, "main") else "master"
    is_on_trunk = current_branch == trunk_branch

    return BranchContext(
        is_on_trunk=is_on_trunk,
        current_branch=current_branch,
        trunk_branch=trunk_branch,
    )
```

### When to Use

Use branch context when command behavior differs based on trunk vs feature branch:

**Trunk branch behavior:**

- Baseline operations (e.g., "show all open feature branches")
- Repository-wide queries
- Stack management from trunk perspective

**Feature branch behavior:**

- Feature-specific operations (e.g., "sessions for this feature")
- Branch-relative queries
- Single-branch workflows

### Example Usage

```python
from erk_shared.branch_context import BranchContext, get_branch_context

def list_relevant_items(git: Git, path: Path) -> list[str]:
    """List items relevant to current branch context."""
    branch_ctx = get_branch_context(git, path)

    if branch_ctx.is_on_trunk:
        # On trunk: show all feature branches
        return git.list_branches(path, remotes=False)
    else:
        # On feature: show items for current feature only
        return [branch_ctx.current_branch]
```

### Real-World Example

From `list_sessions.py` (kit CLI command):

```python
# Get branch context to determine session filtering
branch_ctx = get_branch_context(git, cwd)

# Output includes branch context for downstream consumers
output = {
    "branch_context": {
        "is_on_trunk": branch_ctx.is_on_trunk,
        "current_branch": branch_ctx.current_branch,
        "trunk_branch": branch_ctx.trunk_branch,
    },
    "sessions": sessions,  # Filtered based on branch context
}
```

### Testing Branch Context

```python
def test_command_on_trunk() -> None:
    """Test command behavior on trunk branch."""
    fake_git = FakeGit()
    fake_git.current_branch = "main"
    fake_git.branches = {"main": "abc123"}

    branch_ctx = get_branch_context(fake_git, Path("/repo"))

    assert branch_ctx.is_on_trunk is True
    assert branch_ctx.current_branch == "main"
    assert branch_ctx.trunk_branch == "main"

def test_command_on_feature() -> None:
    """Test command behavior on feature branch."""
    fake_git = FakeGit()
    fake_git.current_branch = "feature-123"
    fake_git.branches = {"main": "abc123", "feature-123": "def456"}

    branch_ctx = get_branch_context(fake_git, Path("/repo"))

    assert branch_ctx.is_on_trunk is False
    assert branch_ctx.current_branch == "feature-123"
    assert branch_ctx.trunk_branch == "main"
```

### Trunk Detection Logic

The helper implements this precedence:

1. **Check for 'main' branch** - Most common modern convention
2. **Fall back to 'master'** - Legacy convention
3. **Compare current branch** to detected trunk

This ensures correct detection regardless of repository trunk name.

## Design Principles

These patterns reflect erk's core design principles:

1. **Dependency Injection over Configuration** - Behavior determined by what's injected, not flags
2. **Explicit Context Management** - Context must be regenerated when environment changes
3. **Layered Error Handling** - Different error handling at different architectural boundaries
4. **Testability First** - Patterns enable easy testing with fakes and mocks
