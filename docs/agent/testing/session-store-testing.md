---
title: "Testing with FakeClaudeCodeSessionStore"
read_when:
  - "Writing tests that need session ID lookup"
  - "Testing code that discovers or lists sessions"
  - "Eliminating mocks for session file operations"
  - "Understanding session store test patterns"
related_docs:
  - "testing/mock-elimination.md"
  - "testing/dot-agent-context-testing.md"
  - "architecture/erk-shared-package.md"
---

# Testing with FakeClaudeCodeSessionStore

## When to Use

Use `FakeClaudeCodeSessionStore` when testing code that needs:

- Current session ID lookup
- Session discovery/listing
- Session content reading

## Basic Setup

```python
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)

# Empty store - no sessions
fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

# Store with current session ID
fake_store = FakeClaudeCodeSessionStore(current_session_id="my-session-id")

# Store with session data
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
```

## Injecting via DotAgentContext

```python
result = runner.invoke(
    my_command,
    ["--format", "json"],
    obj=DotAgentContext.for_test(
        github_issues=fake_gh,
        git=fake_git,
        session_store=fake_store,
        cwd=tmp_path,
    ),
)
```

## Key Methods

- `get_current_session_id()` - Returns configured current session ID
- `find_sessions(project_cwd, min_size=0, limit=10)` - Returns sessions from fake data
- `read_session(project_cwd, session_id)` - Returns session content
- `has_project(project_cwd)` - Checks if project exists

## Complete Example

```python
from pathlib import Path
import pytest
from click.testing import CliRunner
from dot_agent_kit.context import DotAgentContext
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)

def test_command_uses_current_session_id(tmp_path: Path) -> None:
    """Test that command uses session store for session ID lookup."""
    runner = CliRunner()

    # Setup fake with current session
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="abc123",
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(
                        content='{"type": "user", "message": {"content": "Test"}}\n',
                        size_bytes=1000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    result = runner.invoke(
        my_command,
        ["--format", "json"],
        obj=DotAgentContext.for_test(
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    assert result.exit_code == 0
    # Verify command used the session ID from store
```

## Benefits Over File-Based Mocks

Before (with mocks):

```python
with patch("module._get_session_id_from_file", return_value="session-id"):
    result = runner.invoke(command, obj=ctx)
```

After (with fake):

```python
fake_store = FakeClaudeCodeSessionStore(current_session_id="session-id")
result = runner.invoke(
    command,
    obj=DotAgentContext.for_test(session_store=fake_store),
)
```

**Advantages**:

- Tests real behavior, not call signatures
- No brittle mock paths that break on refactoring
- Reusable across tests
- Type-safe injection

## Session Data Construction

For tests that need session content:

```python
fake_store = FakeClaudeCodeSessionStore(
    current_session_id="test-session",
    projects={
        tmp_path: FakeProject(
            sessions={
                "test-session": FakeSessionData(
                    content='''
{"type": "user", "message": {"content": "Create a plan"}}
{"type": "assistant", "message": {"content": "Here is the plan..."}}
'''.strip(),
                    size_bytes=150,
                    modified_at=1234567890.0,
                ),
                "other-session": FakeSessionData(
                    content='{"type": "user", "message": {"content": "Other"}}',
                    size_bytes=50,
                    modified_at=1234567800.0,
                )
            }
        )
    },
)
```

## Testing Session Discovery

```python
def test_list_sessions(tmp_path: Path) -> None:
    """Test listing sessions from store."""
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

    sessions = fake_store.find_sessions(tmp_path, min_size=1000)
    assert len(sessions) == 2
```

## Testing No Session Scenario

```python
def test_no_current_session(tmp_path: Path) -> None:
    """Test behavior when no current session exists."""
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(
            session_store=fake_store,
            cwd=tmp_path,
        ),
    )

    # Verify command handles missing session gracefully
    assert "No active session" in result.output
```

## Migration Path

When you encounter tests with session file mocking:

1. **Identify the mocked function**: Look for `patch("module._get_session_id_from_file")`
2. **Check source code**: Does it use `session_store.get_current_session_id()`?
3. **If not, refactor source first**: Replace file-based lookup with session store
4. **Update test**: Replace mock with `FakeClaudeCodeSessionStore`
5. **Remove unused imports**: Clean up `unittest.mock` if no longer needed

## See Also

- [Mock Elimination Workflow](mock-elimination.md) - Step-by-step guide to replacing mocks
- [DotAgentContext.for_test() Reference](dot-agent-context-testing.md) - All injectable parameters
- [erk_shared Package](../architecture/erk-shared-package.md) - Understanding shared code between erk and dot-agent-kit
