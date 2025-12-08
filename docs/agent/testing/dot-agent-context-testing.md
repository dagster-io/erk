---
title: DotAgentContext.for_test() Reference
read_when:
  - "testing kit CLI commands"
  - "injecting fake dependencies in tests"
  - "setting up test contexts"
---

# DotAgentContext.for_test() Reference

`DotAgentContext.for_test()` creates a test context with injectable fake dependencies for testing kit CLI commands.

## Overview

When testing kit CLI commands, use `DotAgentContext.for_test()` to inject fake implementations of external dependencies. This enables fast, isolated tests without touching real Git repositories, GitHub APIs, or filesystems.

## Available Parameters

| Parameter       | Type                     | Default                        | Description               |
| --------------- | ------------------------ | ------------------------------ | ------------------------- |
| `github_issues` | `GitHubIssues`           | `FakeGitHubIssues()`           | GitHub issue operations   |
| `git`           | `Git`                    | `FakeGit()`                    | Git operations            |
| `session_store` | `ClaudeCodeSessionStore` | `FakeClaudeCodeSessionStore()` | Session store operations  |
| `cwd`           | `Path`                   | `Path.cwd()`                   | Current working directory |
| `repo_root`     | `Path \| None`           | `None`                         | Repository root path      |

## Usage Examples

### Minimal (all defaults)

Use defaults when testing code that doesn't need specific fake configuration:

```python
from dot_agent_kit.context import DotAgentContext

result = runner.invoke(
    my_command,
    obj=DotAgentContext.for_test()
)
```

### With specific fakes

Configure fakes to match the test scenario:

```python
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
)
from erk_shared.git import FakeGit
from erk_shared.github import FakeGitHubIssues

fake_store = FakeClaudeCodeSessionStore(current_session_id="abc123")
fake_git = FakeGit(
    current_branches={tmp_path: "feature"},
    trunk_branches={tmp_path: "main"},
)
fake_gh = FakeGitHubIssues()

result = runner.invoke(
    my_command,
    obj=DotAgentContext.for_test(
        github_issues=fake_gh,
        git=fake_git,
        session_store=fake_store,
        cwd=tmp_path,
    ),
)
```

### Setting current working directory

Always use `tmp_path` fixture for `cwd` in tests:

```python
def test_my_command(tmp_path: Path) -> None:
    """Test command behavior in temporary directory."""
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(cwd=tmp_path),
    )
```

**NEVER** use hardcoded paths or `Path.cwd()` in tests - this can lead to catastrophic test failures.

## Accessing Dependencies in Commands

Use `require_*` helpers to access injected dependencies from the context:

```python
from dot_agent_kit.context_helpers import (
    require_cwd,
    require_git,
    require_github_issues,
    require_session_store,
)
import click

@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    """Example command that uses injected dependencies."""
    github = require_github_issues(ctx)
    git = require_git(ctx)
    session_store = require_session_store(ctx)
    cwd = require_cwd(ctx)

    # Use dependencies
    session_id = session_store.get_current_session_id()
    branch = git.get_current_branch(cwd)
```

## Real-World Example

From `test_plan_save_to_issue.py`:

```python
from click.testing import CliRunner
from dot_agent_kit.context import DotAgentContext
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)
from erk_shared.git import FakeGit
from erk_shared.github import FakeGitHubIssues

def test_plan_save_to_issue_uses_session_store(tmp_path: Path) -> None:
    """Test that command uses session store for current session ID."""
    store_session_id = "store-session-abc123"
    session_content = '{"type": "user", "message": {"content": "test"}}\n'

    fake_store = FakeClaudeCodeSessionStore(
        current_session_id=store_session_id,
        projects={
            tmp_path: FakeProject(
                sessions={
                    store_session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )

    runner = CliRunner()
    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=DotAgentContext.for_test(
            github_issues=fake_gh,
            git=fake_git,
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["session_ids"] == [store_session_id]
```

## Common Patterns

### Testing with multiple session IDs

```python
fake_store = FakeClaudeCodeSessionStore(
    current_session_id="current-session",
    projects={
        tmp_path: FakeProject(
            sessions={
                "current-session": FakeSessionData(
                    content='{"type": "user"}\n',
                    size_bytes=2000,
                    modified_at=1234567890.0,
                ),
                "old-session": FakeSessionData(
                    content='{"type": "user"}\n',
                    size_bytes=1500,
                    modified_at=1234567800.0,
                ),
            }
        )
    },
)
```

### Testing commands that create issues

```python
fake_gh = FakeGitHubIssues()

result = runner.invoke(
    create_issue_command,
    ["--title", "Test Issue"],
    obj=DotAgentContext.for_test(github_issues=fake_gh, cwd=tmp_path),
)

# Verify issue was created
assert len(fake_gh.created_issues) == 1
assert fake_gh.created_issues[0].title == "Test Issue"
```

### Testing commands that navigate branches

```python
fake_git = FakeGit(
    current_branches={tmp_path: "feature"},
    trunk_branches={tmp_path: "main"},
)

result = runner.invoke(
    switch_branch_command,
    ["main"],
    obj=DotAgentContext.for_test(git=fake_git, cwd=tmp_path),
)
```

## Related Topics

- [Kit CLI Testing Patterns](kit-cli-testing.md) - Comprehensive guide to testing kit CLI commands
- [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) - Session store fake details
- [Mock Elimination Workflow](mock-elimination.md) - How to replace mocks with fakes
- [fake-driven-testing skill](/.claude/skills/fake-driven-testing/) - Complete 5-layer testing strategy
