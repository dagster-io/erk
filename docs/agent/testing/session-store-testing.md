---
title: Testing with FakeClaudeCodeSessionStore
read_when:
  - "testing code that reads session data"
  - "using FakeClaudeCodeSessionStore"
  - "mocking session ID lookup"
---

# Testing with FakeClaudeCodeSessionStore

`FakeClaudeCodeSessionStore` provides an in-memory fake for testing code that needs session store operations.

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

# Store with current session ID only
fake_store = FakeClaudeCodeSessionStore(current_session_id="my-session-id")

# Store with full session data
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

Pass the fake store through `DotAgentContext.for_test()`:

```python
from dot_agent_kit.context import DotAgentContext

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

### `get_current_session_id() -> str | None`

Returns the current session ID (from constructor).

```python
store = FakeClaudeCodeSessionStore(current_session_id="abc-123")
session_id = store.get_current_session_id()
assert session_id == "abc-123"
```

### `find_sessions(project_cwd: Path, *, min_size: int = 0, limit: int = 10) -> list[Session]`

Finds sessions for a project, sorted newest first (by `modified_at`).

```python
sessions = store.find_sessions(
    Path("/my/project"),
    min_size=1000,  # Filter out small sessions
    limit=5,        # Return at most 5
)

for session in sessions:
    print(session.session_id, session.size_bytes, session.is_current)
```

**Returns**:
```python
@dataclass
class Session:
    session_id: str
    size_bytes: int
    modified_at: float
    is_current: bool  # True if matches current_session_id
```

### `read_session(project_cwd: Path, session_id: str, *, include_agents: bool = True) -> SessionContent | None`

Reads full session content (main + agent logs).

```python
content = store.read_session(
    Path("/my/project"),
    session_id="abc-123",
    include_agents=True,
)

if content:
    print(content.main_content)  # JSONL from main session
    for agent_id, agent_log in content.agent_logs:
        print(f"Agent {agent_id}: {agent_log}")
```

**Returns**:
```python
@dataclass
class SessionContent:
    main_content: str  # JSONL content
    agent_logs: list[tuple[str, str]]  # (agent_id, JSONL content)
```

### `has_project(project_cwd: Path) -> bool`

Checks if project has any session data.

```python
assert store.has_project(Path("/my/project")) is True
assert store.has_project(Path("/other")) is False
```

## Mock Elimination Workflow

### Before: Mock-Heavy Test

```python
# BAD: Using mocks
def test_list_sessions(mocker):
    mock_store = mocker.MagicMock()
    mock_store.find_sessions.return_value = [
        Session("abc", 1024, 1000.0, True),
    ]

    ctx = DotAgentContext(session_store=mock_store, ...)
    result = list_sessions_command(ctx)

    mock_store.find_sessions.assert_called_once()
```

**Problems**:
- Mock configuration brittle (method names, argument order)
- No type checking (mock accepts anything)
- Test doesn't verify fake implementation

### After: Fake-Based Test

```python
# GOOD: Using fake
def test_list_sessions(tmp_path: Path):
    store = FakeClaudeCodeSessionStore(
        current_session_id="abc",
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc": FakeSessionData(
                        content="...",
                        size_bytes=1024,
                        modified_at=1000.0,
                    )
                }
            )
        },
    )

    ctx = DotAgentContext.for_test(session_store=store, cwd=tmp_path)
    result = list_sessions_command(ctx)

    assert result.exit_code == 0
    assert "abc" in result.output
```

**Benefits**:
- Real implementation (no mock setup)
- Type-safe (constructor enforces structure)
- Tests fake behavior (catches fake bugs)

## Real-World Example

From `test_plan_save_to_issue.py`:

```python
def test_plan_save_to_issue_uses_session_store_for_current_session_id(
    plans_dir: Path, tmp_path: Path
) -> None:
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

## Testing Flag Overrides

When testing that a CLI flag overrides the session store value, ensure only the flag's session exists in the store:

```python
def test_flag_overrides_session_store(tmp_path: Path) -> None:
    """Test --session-id flag takes precedence over store."""
    flag_session_id = "flag-session-xyz"
    store_session_id = "store-session-abc"

    # Only include the flag session in the store
    # This verifies the flag is actually being used
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id=store_session_id,
        projects={
            tmp_path: FakeProject(
                sessions={
                    flag_session_id: FakeSessionData(
                        content='{"type": "user"}\n',
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    result = runner.invoke(
        my_command,
        ["--session-id", flag_session_id],
        obj=DotAgentContext.for_test(session_store=fake_store, cwd=tmp_path),
    )

    # If this passes, the flag was used (store session doesn't exist)
    assert result.exit_code == 0
```

## Related Topics

- [Kit CLI Testing Patterns](kit-cli-testing.md) - General patterns for testing kit CLI commands
- [Mock Elimination Workflow](mock-elimination.md) - How to replace mocks with fakes
