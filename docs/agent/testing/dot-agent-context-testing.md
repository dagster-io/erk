---
title: "DotAgentContext.for_test() Reference"
read_when:
  - "Writing tests for CLI commands using CliRunner"
  - "Injecting fake dependencies into test context"
  - "Understanding available test context parameters"
  - "Setting up test fixtures for commands"
related_docs:
  - "testing/session-store-testing.md"
  - "testing/mock-elimination.md"
  - "testing/kit-cli-testing.md"
---

# DotAgentContext.for_test() Reference

## Overview

`DotAgentContext.for_test()` creates a test context with injectable fake dependencies. This is the primary mechanism for injecting fakes into CLI commands during testing.

## Available Parameters

| Parameter       | Type                     | Default                        | Description               |
| --------------- | ------------------------ | ------------------------------ | ------------------------- |
| `github_issues` | `GitHubIssues`           | `FakeGitHubIssues()`           | GitHub issue operations   |
| `git`           | `Git`                    | `FakeGit()`                    | Git operations            |
| `session_store` | `ClaudeCodeSessionStore` | `FakeClaudeCodeSessionStore()` | Session store operations  |
| `cwd`           | `Path`                   | `Path.cwd()`                   | Current working directory |
| `repo_root`     | `Path`                   | `None`                         | Repository root path      |

## Usage Examples

### Minimal (all defaults)

```python
from dot_agent_kit.context import DotAgentContext

def test_basic_command() -> None:
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(),
    )
    assert result.exit_code == 0
```

### With specific fakes

```python
from pathlib import Path
from dot_agent_kit.context import DotAgentContext
from erk_shared.testing.fakes.fake_git import FakeGit
from erk_shared.testing.fakes.fake_github_issues import FakeGitHubIssues
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
)

def test_command_with_fakes(tmp_path: Path) -> None:
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    fake_gh = FakeGitHubIssues()
    fake_store = FakeClaudeCodeSessionStore(current_session_id="abc123")

    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )
    assert result.exit_code == 0
```

### With session data

```python
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)

def test_command_with_session_data(tmp_path: Path) -> None:
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="test-session-id",
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test-session-id": FakeSessionData(
                        content='{"type": "user", "message": {"content": "Hello"}}\n',
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )
    assert result.exit_code == 0
```

### Testing multiple git repositories

```python
def test_command_across_repos(tmp_path: Path) -> None:
    repo1 = tmp_path / "repo1"
    repo2 = tmp_path / "repo2"

    fake_git = FakeGit(
        current_branches={
            repo1: "main",
            repo2: "feature",
        },
        trunk_branches={
            repo1: "main",
            repo2: "main",
        },
    )

    result = runner.invoke(
        my_command,
        ["--repo", str(repo1)],
        obj=DotAgentContext.for_test(
            git=fake_git,
            cwd=tmp_path,
        ),
    )
    assert result.exit_code == 0
```

## Accessing in Commands

Use `require_*` helpers to get dependencies from context:

```python
import click
from dot_agent_kit.context_helpers import (
    require_cwd,
    require_git,
    require_github_issues,
    require_session_store,
)

@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    """Example command using injected dependencies."""
    github = require_github_issues(ctx)
    git = require_git(ctx)
    session_store = require_session_store(ctx)
    cwd = require_cwd(ctx)

    # Use the dependencies
    current_session = session_store.get_current_session_id()
    current_branch = git.get_current_branch(cwd)
    issues = github.list_issues("owner/repo")

    click.echo(f"Session: {current_session}")
    click.echo(f"Branch: {current_branch}")
    click.echo(f"Issues: {len(issues)}")
```

## Common Patterns

### Testing command with Git operations

```python
def test_command_creates_branch(tmp_path: Path) -> None:
    fake_git = FakeGit(
        current_branches={tmp_path: "main"},
        trunk_branches={tmp_path: "main"},
    )

    result = runner.invoke(
        create_branch_command,
        ["feature-name"],
        obj=DotAgentContext.for_test(
            git=fake_git,
            cwd=tmp_path,
        ),
    )

    assert result.exit_code == 0
    # Verify fake recorded the operation
    assert fake_git.get_current_branch(tmp_path) == "feature-name"
```

### Testing command with GitHub operations

```python
def test_command_creates_issue(tmp_path: Path) -> None:
    fake_gh = FakeGitHubIssues()

    result = runner.invoke(
        create_issue_command,
        ["--title", "Bug report"],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            cwd=tmp_path,
        ),
    )

    assert result.exit_code == 0
    assert len(fake_gh.created_issues) == 1
    assert fake_gh.created_issues[0].title == "Bug report"
```

### Testing command with no current session

```python
def test_command_handles_no_session(tmp_path: Path) -> None:
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    # Command should handle missing session gracefully
    assert result.exit_code == 1
    assert "No active session" in result.output
```

### Testing command with multiple sessions

```python
def test_command_lists_sessions(tmp_path: Path) -> None:
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="current",
        projects={
            tmp_path: FakeProject(
                sessions={
                    "session1": FakeSessionData(
                        content="...",
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    ),
                    "session2": FakeSessionData(
                        content="...",
                        size_bytes=1500,
                        modified_at=1234567800.0,
                    )
                }
            )
        },
    )

    result = runner.invoke(
        list_sessions_command,
        obj=DotAgentContext.for_test(
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    assert result.exit_code == 0
    assert "session1" in result.output
    assert "session2" in result.output
```

## Complete Example: Testing a Complex Command

```python
from pathlib import Path
import pytest
from click.testing import CliRunner
from dot_agent_kit.context import DotAgentContext
from erk_shared.testing.fakes.fake_git import FakeGit
from erk_shared.testing.fakes.fake_github_issues import FakeGitHubIssues
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)

def test_save_plan_to_github(tmp_path: Path) -> None:
    """Test saving a plan to GitHub issue with full context."""
    runner = CliRunner()

    # Setup plan file
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Implementation Plan\n\nStep 1: Do something\n", encoding="utf-8")

    # Setup fakes
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    fake_gh = FakeGitHubIssues()
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="test-session",
        projects={
            tmp_path: FakeProject(
                sessions={
                    "test-session": FakeSessionData(
                        content='{"type": "user", "message": {"content": "Create a plan"}}\n',
                        size_bytes=1000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    # Invoke command
    result = runner.invoke(
        save_plan_command,
        ["--plan", str(plan_file), "--title", "New Feature"],
        obj=DotAgentContext.for_test(
            git=fake_git,
            github_issues=fake_gh,
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    # Assertions
    assert result.exit_code == 0
    assert len(fake_gh.created_issues) == 1
    created_issue = fake_gh.created_issues[0]
    assert created_issue.title == "New Feature"
    assert "Implementation Plan" in created_issue.body
```

## Benefits

1. **Type-safe**: All parameters are typed and checked
2. **Flexible**: Only specify what you need, rest uses sensible defaults
3. **Testable**: Easy to verify behavior through fake mutation tracking
4. **Isolated**: Each test gets its own context, no shared state
5. **Fast**: In-memory fakes, no I/O operations

## See Also

- [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) - Session store patterns
- [Mock Elimination Workflow](mock-elimination.md) - Replacing mocks with fakes
- [Kit CLI Testing](kit-cli-testing.md) - Testing kit CLI commands
