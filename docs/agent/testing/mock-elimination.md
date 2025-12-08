---
title: "Eliminating Mocks with Fakes"
read_when:
  - "Encountering tests with unittest.mock.patch()"
  - "Refactoring tests to use fakes instead of mocks"
  - "Understanding when to eliminate mocks"
  - "Learning the mock-to-fake migration workflow"
related_docs:
  - "testing/session-store-testing.md"
  - "testing/dot-agent-context-testing.md"
  - "architecture/erk-architecture.md"
---

# Eliminating Mocks with Fakes

## Overview

When you encounter tests with `unittest.mock.patch()`, consider whether a fake can replace the mock. Fakes are preferred because they:

- Test real behavior, not call signatures
- Don't break when implementation changes
- Are reusable across tests
- Provide type safety

## Workflow

### Step 1: Identify Mock Targets

Look for patterns like:

```python
with patch("module.function", return_value=value):
    ...

@patch("module.SomeClass.method")
def test_something(mock_method):
    ...
```

### Step 2: Check for Existing Fakes

Common fakes in this codebase:

- `FakeGit` - Git operations
- `FakeGitHubIssues` - GitHub issue operations
- `FakeClaudeCodeSessionStore` - Session store operations
- `FakeGraphite` - Graphite operations

**Location**: Look in `erk_shared/testing/fakes/` or check import statements in existing tests.

### Step 3: Refactor Source Code (if needed)

If the mocked function reads from filesystem/external state, consider:

#### Option 1: Adding a dependency injection point (ABC + fake)

If you need a new abstraction:

```python
# Before: Direct filesystem access
def get_config() -> dict:
    path = Path(".config/app.yml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))

# After: Dependency injection
from abc import ABC, abstractmethod

class ConfigStore(ABC):
    @abstractmethod
    def load_config(self) -> dict:
        ...

class FileConfigStore(ConfigStore):
    def load_config(self) -> dict:
        path = Path(".config/app.yml")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

class FakeConfigStore(ConfigStore):
    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    def load_config(self) -> dict:
        return self._config
```

#### Option 2: Using an existing abstraction (e.g., session_store)

If an abstraction already exists:

```python
# Before: File-based (requires mocking)
def process_plan(plan_path: Path, session_id: str | None = None) -> None:
    effective_session_id = session_id or _get_session_id_from_file()
    # ... use effective_session_id

def _get_session_id_from_file() -> str | None:
    path = Path(".erk/scratch/current-session-id")
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None

# After: Dependency injection (uses fake)
def process_plan(
    plan_path: Path,
    session_store: ClaudeCodeSessionStore,
    session_id: str | None = None,
) -> None:
    effective_session_id = session_id or session_store.get_current_session_id()
    # ... use effective_session_id
```

### Step 4: Update Tests

Replace mocks with fake configuration:

```python
# Before: Mock
from unittest.mock import patch

def test_process_plan_with_session_id(tmp_path: Path) -> None:
    with patch("module._get_session_id_from_file", return_value="session-id"):
        result = runner.invoke(
            command,
            ["--plan", str(tmp_path / "plan.md")],
            obj=ctx,
        )
        assert result.exit_code == 0

# After: Fake
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
)

def test_process_plan_with_session_id(tmp_path: Path) -> None:
    fake_store = FakeClaudeCodeSessionStore(current_session_id="session-id")
    result = runner.invoke(
        command,
        ["--plan", str(tmp_path / "plan.md")],
        obj=DotAgentContext.for_test(session_store=fake_store, cwd=tmp_path),
    )
    assert result.exit_code == 0
```

### Step 5: Remove Unused Imports

After eliminating all mocks from a test file, remove:

```python
from unittest.mock import patch  # Remove if no longer used
from unittest.mock import MagicMock  # Remove if no longer used
```

## Real-World Example: Plan Save to Issue

### Before: 12 mocks

```python
from unittest.mock import patch, MagicMock

def test_save_plan_to_issue() -> None:
    with patch("erk.cli.plan_save_to_issue._get_session_id_from_file") as mock_session:
        with patch("erk.cli.plan_save_to_issue._read_session_log") as mock_read:
            with patch("erk.cli.plan_save_to_issue._get_project_dir") as mock_project:
                # ... 9 more mocks ...
                mock_session.return_value = "abc123"
                mock_read.return_value = "session content"
                # ... configure other mocks ...

                result = runner.invoke(command, obj=ctx)
                assert result.exit_code == 0
```

### After: 0 mocks

```python
from erk_shared.extraction.claude_code_session_store import (
    FakeClaudeCodeSessionStore,
    FakeProject,
    FakeSessionData,
)
from erk_shared.testing.fakes.fake_github_issues import FakeGitHubIssues
from erk_shared.testing.fakes.fake_git import FakeGit

def test_save_plan_to_issue(tmp_path: Path) -> None:
    fake_store = FakeClaudeCodeSessionStore(
        current_session_id="abc123",
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(
                        content="session content",
                        size_bytes=100,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )
    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )

    result = runner.invoke(
        command,
        obj=DotAgentContext.for_test(
            session_store=fake_store,
            github_issues=fake_gh,
            git=fake_git,
            cwd=tmp_path,
        ),
    )
    assert result.exit_code == 0
    assert len(fake_gh.created_issues) == 1
```

## When to Keep Mocks

Mocks are still appropriate for:

1. **Third-party APIs with no fake**: When an external API is too complex to fake
2. **Expensive operations in integration tests**: When you want to test integration logic without actual I/O
3. **Testing error conditions**: When you need to simulate specific error scenarios

```python
# ✅ ACCEPTABLE: Mocking external API for error testing
@patch("requests.post")
def test_api_error_handling(mock_post: MagicMock) -> None:
    mock_post.side_effect = requests.ConnectionError("Network error")
    with pytest.raises(APIError, match="Network error"):
        send_notification(message="test")
```

## Decision Tree

```
Is the mocked code an integration layer (Git, GitHub, FileSystem, Database)?
├─ YES: Use existing fake (FakeGit, FakeGitHubIssues, FakeClaudeCodeSessionStore)
└─ NO: Is it a heavyweight external API?
    ├─ YES: Consider creating a fake if heavily used, otherwise keep mock
    └─ NO: Is it a simple helper function?
        ├─ YES: Consider making it a pure function (no mocking needed)
        └─ NO: Keep mock if it's rarely used or test-specific
```

## Benefits Summary

| Aspect                 | Mocks                                | Fakes                                   |
| ---------------------- | ------------------------------------ | --------------------------------------- |
| **Refactoring safety** | Brittle (break on signature changes) | Robust (break only on behavior changes) |
| **Reusability**        | Low (specific to each test)          | High (shared across tests)              |
| **Type safety**        | No (MagicMock bypasses types)        | Yes (implements real interface)         |
| **Test clarity**       | Low (setup noise)                    | High (clear intent)                     |
| **Maintenance**        | High (update per refactor)           | Low (update once in fake)               |

## See Also

- [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) - Session store fake usage
- [DotAgentContext.for_test() Reference](dot-agent-context-testing.md) - Injecting fakes into context
- [Erk Architecture Patterns](../architecture/erk-architecture.md) - Dependency injection patterns
