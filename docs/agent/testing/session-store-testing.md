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

| Method                                             | Description                           |
| -------------------------------------------------- | ------------------------------------- |
| `get_current_session_id()`                         | Returns configured current session ID |
| `find_sessions(project_cwd, min_size=0, limit=10)` | Returns sessions from fake data       |
| `read_session(project_cwd, session_id)`            | Returns session content               |
| `has_project(project_cwd)`                         | Checks if project exists              |
| `get_latest_plan(project_cwd, session_id=None)`    | Returns plan content from fake plans  |

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

## Testing Plan Access

The `FakeClaudeCodeSessionStore` supports fake plan data via the `plans` parameter:

### Basic Plan Setup

```python
fake_store = FakeClaudeCodeSessionStore(
    plans={"my-feature": "# My Feature Plan\n\n- Step 1\n- Step 2"},
)

# Returns plan content
plan = fake_store.get_latest_plan(tmp_path)
assert plan == "# My Feature Plan\n\n- Step 1\n- Step 2"
```

### Session-Scoped Plan Lookup

When `session_id` matches a key in `plans`, that specific plan is returned:

```python
fake_store = FakeClaudeCodeSessionStore(
    plans={
        "session-abc": "# Plan for Session ABC",
        "session-xyz": "# Plan for Session XYZ",
    },
)

# Returns specific plan when session_id matches
plan = fake_store.get_latest_plan(tmp_path, session_id="session-abc")
assert "Session ABC" in plan
```

### Testing "No Plan Found"

```python
fake_store = FakeClaudeCodeSessionStore(plans={})  # Empty plans
plan = fake_store.get_latest_plan(tmp_path)
assert plan is None
```

### Replacing Monkeypatch Patterns

Before (monkeypatch approach):

```python
@pytest.fixture
def plans_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    monkeypatch.setattr(
        "some.module.get_plans_dir",
        lambda: plans,
    )
    return plans

def test_something(plans_dir: Path) -> None:
    (plans_dir / "test.md").write_text("# Plan")
    # ...
```

After (fake store approach):

```python
def test_something() -> None:
    fake_store = FakeClaudeCodeSessionStore(
        plans={"test": "# Plan"},
    )
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(session_store=fake_store),
    )
    # ...
```

## Related Topics

- [Local Plans Architecture](../architecture/local-plans.md) - How the local plans system works
- [Kit CLI Testing Patterns](kit-cli-testing.md) - General patterns for testing kit CLI commands
- [Mock Elimination Workflow](mock-elimination.md) - How to replace mocks with fakes
