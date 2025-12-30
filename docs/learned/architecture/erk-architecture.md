---
title: Erk Architecture Patterns
read_when:
  - "understanding erk architecture"
  - "implementing dry-run patterns"
  - "regenerating context after os.chdir"
  - "detecting root worktree"
  - "adding composing template methods to ABC"
tripwires:
  - action: "passing dry_run boolean flags through function parameters"
    warning: "Use dependency injection with DryRunGit/DryRunGitHub wrappers instead of boolean flags."
  - action: "calling os.chdir() in erk code"
    warning: "After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError."
  - action: "importing time module or calling time.sleep()"
    warning: "Use context.time.sleep() for testability. Direct time.sleep() makes tests slow."
  - action: "implementing CLI flags that affect post-mutation behavior"
    warning: "Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk pr land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target)."
  - action: "editing docs/agent/index.md or docs/agent/tripwires.md directly"
    warning: "These are generated files. Edit the source frontmatter instead, then run 'dot-agent docs sync'."
  - action: "comparing worktree path to repo_root to detect root worktree"
    warning: "Use WorktreeInfo.is_root instead of path comparison. Path comparison fails when running from within a non-root worktree because ctx.cwd resolves differently."
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
from erk_shared.gateway.time.real import RealTime

time = RealTime()
time.sleep(2.0)  # Actually sleeps for 2 seconds
```

**Testing (FakeTime)**:

```python
from erk_shared.gateway.time.fake import FakeTime

fake_time = FakeTime()
fake_time.sleep(2.0)  # Returns immediately, tracks call

# Assert sleep was called with expected duration
assert fake_time.sleep_calls == [2.0]
```

### Real-World Examples

**Retry with exponential backoff**: Use `context.time.sleep(delay)` in retry loops for instant test execution. See `src/erk/cli/commands/land_stack/` for production patterns.

**GitHub API stabilization**:

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

The `Time` ABC defines abstract methods for time operations including `sleep()` and `now()`. Implementations:

- **RealTime**: Uses actual `time.sleep()` and `datetime.now()`
- **FakeTime**: Returns immediately, tracks calls for test assertions

See `erk_shared/gateway/time/abc.py` for the canonical interface definition.

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

## Gateway Directory Structure

Erk uses a consistent directory structure for all gateways (git, github, graphite, etc). Each gateway follows the ABC/Real/Fake/DryRun pattern.

### Standard Directory Layout

```
packages/erk-shared/src/erk_shared/
├── git/                           # Core git gateway
│   ├── __init__.py                # Re-exports all implementations
│   ├── abc.py                     # ABC interface definition
│   ├── real.py                    # Production implementation
│   ├── fake.py                    # In-memory test implementation
│   ├── dry_run.py                 # No-op wrapper for dry-run mode
│   └── printing.py                # (Optional) Wrapper that logs operations
├── github/                        # GitHub API gateway
│   ├── __init__.py
│   ├── abc.py
│   ├── real.py
│   └── fake.py
└── gateway/                       # Domain-specific gateways
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

class MyGateway(ABC):
    """Abstract interface for MyGateway operations."""

    @abstractmethod
    def do_operation(self, arg: str) -> str:
        """Perform operation with given argument."""
        ...
```

**`real.py`** - Production implementation:

```python
import subprocess
from erk_shared.my_gateway.abc import MyGateway

class RealMyGateway(MyGateway):
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
from erk_shared.my_gateway.abc import MyGateway

class FakeMyGateway(MyGateway):
    """In-memory fake for testing."""

    def __init__(self) -> None:
        self.operations_called: list[str] = []

    def do_operation(self, arg: str) -> str:
        self.operations_called.append(arg)
        return f"fake-result-{arg}"
```

**`dry_run.py`** - No-op wrapper (optional):

```python
from erk_shared.my_gateway.abc import MyGateway

class DryRunMyGateway(MyGateway):
    """No-op wrapper that tracks but doesn't execute operations."""

    def __init__(self, delegate: MyGateway) -> None:
        self.delegate = delegate
        self.operations: list[str] = []

    def do_operation(self, arg: str) -> str:
        self.operations.append(f"do_operation({arg})")
        return ""  # No-op, return empty or default value
```

**`__init__.py`** - Re-export pattern:

```python
"""MyGateway operations."""

from erk_shared.my_gateway.abc import MyGateway
from erk_shared.my_gateway.real import RealMyGateway
from erk_shared.my_gateway.fake import FakeMyGateway

__all__ = [
    "MyGateway",      # ABC interface
    "RealMyGateway",  # Production implementation
    "FakeMyGateway",  # Test implementation
]
```

### Gateway Locations

**Core gateways** (used across the codebase):

- `packages/erk-shared/src/erk_shared/git/` - Git operations
- `packages/erk-shared/src/erk_shared/github/` - GitHub API
- `packages/erk-shared/src/erk_shared/graphite/` - Graphite stack operations

**Domain gateways** (specific domains):

- `packages/erk-shared/src/erk_shared/gateway/<name>/` - Domain-specific operations

### When to Create a New Gateway

**Create a new gateway when:**

- Wrapping external CLI tool (git, gh, gt)
- Wrapping external API (GitHub REST API)
- Abstracting system operations (time, filesystem)
- Isolating subprocess calls for testing

**Extend existing gateway when:**

- Adding method to existing tool (e.g., new git operation)
- Enhancing existing functionality
- Operation fits natural domain of existing gateway

### Import Pattern

**From consumers:**

```python
# Import from top-level package (uses __init__.py re-exports)
from erk_shared.git import Git, RealGit, FakeGit
from erk_shared.github import GitHub, RealGitHub, FakeGitHub
```

**Not this:**

```python
# DON'T import from implementation files directly
from erk_shared.git.real import RealGit  # Bypasses __init__.py
```

### Testing All Four Layers

When adding a method to a gateway ABC:

1. **ABC**: Add abstract method signature
2. **Real**: Implement with subprocess/API calls
3. **Fake**: Implement with in-memory tracking
4. **DryRun**: Add no-op wrapper (if gateway has dry-run layer)

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

If you find code that should be a gateway but isn't:

1. **Create gateway directory** with abc.py, real.py, fake.py
2. **Extract subprocess calls** into Real implementation
3. **Write Fake implementation** for testing
4. **Update consumers** to use injected dependency instead of direct calls
5. **Update tests** to use Fake instead of mocking subprocess

## Composing Template Method Pattern

The gateway ABCs use a variant of the **Template Method** pattern where concrete methods compose abstract methods to provide higher-level operations. Unlike classic Template Method (where subclasses override hooks to customize an algorithm), here the concrete methods are pure compositions that work identically for all implementations - no override points, just convenience wrappers.

### When to Use

Add a composing template method to an ABC when:

1. The logic only depends on abstract methods already in the ABC
2. There's no implementation-specific behavior (same logic for Real/Fake/DryRun)
3. The operation would otherwise be duplicated or require passing the gateway around

### Examples in Graphite ABC

| Method                       | Composes              | Purpose                                  |
| ---------------------------- | --------------------- | ---------------------------------------- |
| `get_parent_branch()`        | `get_all_branches()`  | Extract single parent from branch map    |
| `get_child_branches()`       | `get_all_branches()`  | Extract children list from branch map    |
| `find_ancestor_worktree()`   | `get_parent_branch()` | Walk parent chain to find worktree       |
| `squash_branch_idempotent()` | `squash_branch()`     | Add error handling for idempotent squash |

### Pattern Structure

```python
class Gateway(ABC):
    @abstractmethod
    def primitive_operation(self, ...) -> Result:
        """Subclasses must implement."""
        ...

    def composite_operation(self, ...) -> HigherLevelResult:
        """Concrete method - same for all implementations.

        Composes primitive_operation() to provide convenience API.
        All implementations (Real, Fake, DryRun) inherit this unchanged.
        """
        result = self.primitive_operation(...)
        # Additional logic using result
        return transformed_result
```

### Benefits

- **No duplication**: Logic defined once, inherited by all implementations
- **Automatic testing**: Works with FakeGraphite, no separate fake needed
- **Discoverability**: Related operations live together on the interface
- **Lighter dependencies**: Takes primitive args (Git, Path) not heavy context objects

### When NOT to Use

Don't add a composing template method when:

- The logic requires implementation-specific behavior
- The method would need overriding in some implementations
- The logic doesn't naturally belong to the gateway's domain

In those cases, keep the logic as a standalone function or in the calling module.

## Branch Context Detection

Commands that need to behave differently on trunk vs feature branches use the branch context pattern.

### The BranchContext Pattern

`BranchContext` is a frozen dataclass with three fields:

- `current_branch`: Name of the current branch
- `trunk_branch`: Name of the trunk branch (main or master)
- `is_on_trunk`: True if current branch is trunk

See `erk_shared/extraction/types.py` for the dataclass definition.

### Helper Function

The `get_branch_context()` helper detects current branch, trunk branch (prefers 'main', falls back to 'master'), and whether current branch is trunk.

See `erk_shared/extraction/session_discovery.py` for the canonical implementation.

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

Commands typically use branch context to decide behavior:

- **On trunk**: Show all feature branches, repository-wide queries
- **On feature branch**: Show items for current feature only, branch-relative queries

See `kit_cli_commands/erk/list_sessions.py` for a real-world usage example.

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

## Root Worktree Detection

**ALWAYS use `WorktreeInfo.is_root` instead of path comparison to identify the root worktree.**

### The Problem

When running from within a non-root worktree, path comparison fails because:

1. `ctx.cwd` resolves to the worktree path (e.g., `/Users/me/erks/repo/feature-branch`)
2. `repo_root` from git discovery resolves to the main repo (e.g., `/Users/me/repos/repo`)
3. Direct path comparison always returns False, even when you're in the root worktree

### Wrong Pattern

```python
# WRONG: Path comparison breaks from non-root worktrees
def is_root_worktree(worktree_path: Path, repo_root: Path) -> bool:
    return worktree_path.resolve() == repo_root.resolve()

# WRONG: Manual computation of is_root
is_root = worktree_path.resolve() == repo_root.resolve()
```

### Correct Pattern

```python
# CORRECT: Use WorktreeInfo.is_root from git worktree list
worktrees = ctx.git.list_worktrees(repo_root)
for wt in worktrees:
    if wt.is_root:
        # This is the root worktree
        handle_root_worktree(wt)
    else:
        # This is a feature worktree
        handle_feature_worktree(wt)
```

### How WorktreeInfo.is_root Works

`WorktreeInfo.is_root` is populated by `RealGit.list_worktrees()` when parsing `git worktree list --porcelain`:

- Git marks the root worktree with `branch refs/heads/<trunk>` where the `.git` directory lives
- The first worktree entry (before any blank line separator) is always the root
- `is_root=True` is set based on this git metadata, not path comparison

### When to Use

Use `wt.is_root` whenever you need to:

- Filter out the root worktree from worktree lists
- Identify which worktree is the main repository
- Determine special handling for root vs feature worktrees

### Examples in Codebase

```python
# From checkout.py - handling root worktree specially
if wt.is_root:
    # Root worktree navigation
    activate_root_repo(ctx, repo, script, command_name="checkout")

# From checkout_cmd.py - filtering worktrees
if not wt.is_root:
    # Only show non-root worktrees in picker
    worktree_options.append(wt)
```

## Design Principles

These patterns reflect erk's core design principles:

1. **Dependency Injection over Configuration** - Behavior determined by what's injected, not flags
2. **Explicit Context Management** - Context must be regenerated when environment changes
3. **Layered Error Handling** - Different error handling at different architectural boundaries
4. **Testability First** - Patterns enable easy testing with fakes and mocks
