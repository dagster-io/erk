---
title: Kit CLI Dependency Injection Patterns
read_when:
  - "writing kit CLI commands"
  - "testing kit CLI commands"
  - "using DotAgentContext"
tripwires:
  - action: "using Path.cwd() in kit CLI commands"
    warning: "Use require_cwd(ctx) instead. Path.cwd() bypasses dependency injection and makes tests require monkeypatching."
---

# Kit CLI Dependency Injection Patterns

This document covers the dependency injection patterns for kit CLI commands in erk-kits.

## Overview

Kit CLI commands receive dependencies via Click's context system (`@click.pass_context`). The `DotAgentContext` dataclass holds all dependencies (git, github, graphite gateways) and is:

1. **Created once** at CLI entry point via `create_context()`
2. **Threaded through** the application via `ctx.obj`
3. **Accessed safely** using `require_*()` helper functions (LBYL pattern)

## Context Architecture

```python
@dataclass(frozen=True)
class DotAgentContext:
    """Immutable context holding all dependencies.

    Attributes:
        github_issues: GitHub Issues integration for querying/commenting
        git: Git operations integration for branch/commit queries
        github: GitHub integration for PR operations
        debug: Debug flag for error handling (full stack traces)
        repo_root: Repository root directory (detected at CLI entry)
        cwd: Current working directory (worktree path)
    """
    github_issues: GitHubIssues
    git: Git
    github: GitHub
    debug: bool
    repo_root: Path
    cwd: Path
```

**Key design decisions:**

- **Frozen dataclass**: Prevents accidental modification at runtime
- **Immutable**: All dependencies set at creation time
- **Repository vs worktree paths**: `repo_root` is the git repository root, `cwd` is the current worktree

## Writing Kit CLI Commands

### Basic Pattern

```python
import click
from erk_kits.context_helpers import require_github_issues
from erk_shared.context.helpers import (
    require_repo_root,
    require_git,
    require_cwd,
)

@click.command(name="my-command")
@click.pass_context
def my_command(ctx: click.Context) -> None:
    """Example kit CLI command with dependency injection."""
    # Get dependencies from context using helper functions
    github_issues = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)
    cwd = require_cwd(ctx)

    # Use dependencies
    branch = git.get_current_branch(cwd)
    issue = github_issues.get_issue(repo_root, issue_number=123)
```

### Available Helper Functions

All helpers follow the LBYL (Look Before You Leap) pattern:

| Helper                       | Returns        | Usage                                |
| ---------------------------- | -------------- | ------------------------------------ |
| `require_github_issues(ctx)` | `GitHubIssues` | Create/update issues, add comments   |
| `require_git(ctx)`           | `Git`          | Branch operations, commit queries    |
| `require_github(ctx)`        | `GitHub`       | PR operations, status checks         |
| `require_repo_root(ctx)`     | `Path`         | Repository root path                 |
| `require_cwd(ctx)`           | `Path`         | Current working directory (worktree) |

**Error handling:** All helpers check if `ctx.obj is None` and exit with clear error message if context is not initialized.

### Real-World Example

From `mark_impl_started.py`:

```python
@click.command(name="mark-impl-started")
@click.pass_context
def mark_impl_started(ctx: click.Context) -> None:
    """Update implementation started event in GitHub issue."""
    # Get dependencies
    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)

    # Read issue reference from .impl/issue.json
    impl_dir = cwd / ".impl"
    issue_ref = read_issue_reference(impl_dir)

    if issue_ref is None:
        result = MarkImplError(
            success=False,
            error_type="no_issue_reference",
            message="No issue reference found",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)

    # Get GitHub Issues from context
    try:
        github_issues = require_github_issues(ctx)
    except SystemExit:
        result = MarkImplError(
            success=False,
            error_type="context_not_initialized",
            message="Context not initialized",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    # Fetch and update issue
    issue = github_issues.get_issue(repo_root, issue_ref.issue_number)
    updated_body = update_plan_header_local_impl_event(
        issue_body=issue.body,
        local_impl_at=timestamp,
        event="started",
    )
    github_issues.update_issue_body(repo_root, issue_ref.issue_number, updated_body)
```

## Testing Kit CLI Commands

### Pattern 1: Using `ErkContext.for_test()` (Recommended)

For commands that use `@click.pass_context`, inject test context via `obj` parameter:

```python
from click.testing import CliRunner
from erk_shared.context import ErkContext
from erk_shared.github.issues import FakeGitHubIssues

def test_my_command() -> None:
    """Test command with fake dependencies."""
    # Arrange: Create fake dependencies
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Act: Invoke command with test context
    result = runner.invoke(
        my_command,
        ["--arg", "value"],
        obj=ErkContext.for_test(github_issues=fake_gh),
    )

    # Assert
    assert result.exit_code == 0
    assert len(fake_gh.created_issues) == 1
```

**Why this pattern?**

- Uses in-memory fakes (no subprocess calls)
- Full control over dependencies
- Clear test isolation
- Follows Layer 4 testing strategy (business logic over fakes)

### Pattern 2: Using `monkeypatch` for Indirect Dependencies

For commands that create dependencies internally (not via context):

```python
def test_command_with_monkeypatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test command that internally creates dependencies."""
    # Arrange: Set up fake plan store
    fake_plan_store = FakePlanStore(plans={"1028": plan})

    # Mock the factory that creates the dependency
    monkeypatch.setattr(
        "my_module.GitHubPlanStore",
        lambda github_issues: fake_plan_store,
    )

    # Act: Run command
    runner = CliRunner()
    result = runner.invoke(
        my_command,
        ["--arg", "value"],
    )

    # Assert
    assert result.exit_code == 0
```

### DotAgentContext.for_test() API

```python
@staticmethod
def for_test(
    github_issues: GitHubIssues | None = None,
    git: Git | None = None,
    github: GitHub | None = None,
    debug: bool = False,
    repo_root: Path | None = None,
    cwd: Path | None = None,
) -> "DotAgentContext":
    """Create test context with optional pre-configured implementations.

    All parameters are optional. Unspecified values default to fakes:
    - github_issues: Defaults to FakeGitHubIssues()
    - git: Defaults to FakeGit()
    - github: Defaults to FakeGitHub()
    - repo_root: Defaults to Path("/fake/repo")
    - cwd: Defaults to Path("/fake/worktree")
    """
```

**Example with custom paths:**

```python
def test_with_real_filesystem(tmp_path: Path) -> None:
    """Test command with real filesystem paths."""
    fake_git = FakeGit()
    ctx = DotAgentContext.for_test(
        git=fake_git,
        repo_root=tmp_path,
        cwd=tmp_path / "worktree",
    )

    result = runner.invoke(my_command, obj=ctx)
    assert result.exit_code == 0
```

## Production Context Creation

For reference, here's how production context is created at CLI entry point:

```python
def create_context(*, debug: bool) -> DotAgentContext:
    """Create production context with real implementations.

    Called once at CLI entry point. Detects repository root using
    git rev-parse and exits with error if not in a git repository.
    """
    from erk_shared.git.real import RealGit
    from erk_shared.github.real import RealGitHub
    from erk_shared.gateway.time.real import RealTime

    # Detect repo root
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        click.echo("Error: Not in a git repository", err=True)
        raise SystemExit(1)

    repo_root = Path(result.stdout.strip())
    cwd = Path.cwd()

    return DotAgentContext(
        github_issues=RealGitHubIssues(),
        git=RealGit(),
        github=RealGitHub(time=RealTime()),
        debug=debug,
        repo_root=repo_root,
        cwd=cwd,
    )
```

## Common Patterns

### Error Handling with Graceful Degradation

For commands used with `|| true` pattern in bash:

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    """Command that never fails the parent script."""
    try:
        github = require_github_issues(ctx)
    except SystemExit:
        # Gracefully degrade
        result = {"success": False, "error": "Context not initialized"}
        click.echo(json.dumps(result, indent=2))
        raise SystemExit(0) from None  # Exit 0 for || true pattern

    # Normal operation
    # ...
```

### Repository vs Worktree Paths

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    """Command that works with both repo root and worktree."""
    repo_root = require_repo_root(ctx)  # /path/to/repo
    cwd = require_cwd(ctx)              # /path/to/repo/worktrees/feature
    git = require_git(ctx)

    # Operations that need repo root (e.g., GitHub API calls)
    github_issues.get_issue(repo_root, issue_number=123)

    # Operations that need worktree path (e.g., git operations)
    branch = git.get_current_branch(cwd)
```

### Why `require_cwd(ctx)` Instead of `Path.cwd()`

**NEVER use `Path.cwd()` in kit CLI commands.** Always use `require_cwd(ctx)`.

| Approach           | Testability | Why                                                          |
| ------------------ | ----------- | ------------------------------------------------------------ |
| `require_cwd(ctx)` | ✅ Easy     | Inject any path via `DotAgentContext.for_test(cwd=tmp_path)` |
| `Path.cwd()`       | ❌ Hard     | Requires `monkeypatch` or `os.chdir()` in tests              |

**Anti-pattern:**

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    impl_dir = Path.cwd() / ".impl"  # ❌ WRONG: bypasses DI
    # ...
```

**Correct pattern:**

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)
    impl_dir = cwd / ".impl"  # ✅ CORRECT: uses injected path
    # ...
```

The production context captures `Path.cwd()` once at CLI entry point and stores it in `DotAgentContext.cwd`. Commands access it via `require_cwd(ctx)`, enabling tests to inject arbitrary paths without filesystem manipulation.

## See Also

- [fake-driven-testing skill](.claude/docs/fake-driven-testing/) - Layer 4 testing strategy
- [CLI Development](../cli/) - Command organization and output styling
- [Testing](../testing/) - General testing patterns
