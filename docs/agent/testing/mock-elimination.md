---
title: Eliminating Mocks with Fakes
read_when:
  - "refactoring tests to remove unittest.mock"
  - "replacing patch() calls with fakes"
  - "improving test maintainability"
---

# Eliminating Mocks with Fakes

When you encounter tests with `unittest.mock.patch()`, consider whether a fake can replace the mock. Fakes are preferred because they:

- Test real behavior, not call signatures
- Don't break when implementation changes
- Are reusable across tests

## Workflow

### Step 1: Identify Mock Targets

Look for patterns like:

```python
with patch("module.function", return_value=value):
    ...
```

or:

```python
@patch("module.function")
def test_something(mock_fn):
    mock_fn.return_value = value
    ...
```

### Step 2: Check for Existing Fakes

Common fakes in this codebase:

| Fake                         | Replaces                 |
| ---------------------------- | ------------------------ |
| `FakeGit`                    | Git operations           |
| `FakeGitHub`                 | GitHub PR operations     |
| `FakeGitHubIssues`           | GitHub issue operations  |
| `FakeGraphite`               | Graphite operations      |
| `FakeClaudeCodeSessionStore` | Session store operations |

### Step 3: Refactor Source Code (if needed)

If the mocked function reads from filesystem/external state, consider:

1. Adding a dependency injection point (ABC + fake)
2. Using an existing abstraction (e.g., session_store)

**Example: Replace file-based lookup with session store:**

```python
# Before: File-based (requires mocking)
effective_session_id = session_id or _get_session_id_from_file()

# After: Dependency injection (uses fake)
session_store = require_session_store(ctx)
effective_session_id = session_id or session_store.get_current_session_id()
```

### Step 4: Update Tests

Replace mocks with fake configuration:

```python
# Before: Mock
with patch("module._get_session_id_from_file", return_value="session-id"):
    result = runner.invoke(command, obj=ctx)

# After: Fake
fake_store = FakeClaudeCodeSessionStore(current_session_id="session-id")
result = runner.invoke(
    command,
    obj=DotAgentContext.for_test(session_store=fake_store),
)
```

### Step 5: Remove Unused Imports

After eliminating all mocks, remove:

```python
from unittest.mock import patch  # Remove if no longer used
```

## Real-World Example

The `plan_save_to_issue.py` command was refactored to eliminate 12 mocks:

### Before (with mocks)

```python
# Source code
def _get_session_id_from_file() -> str | None:
    """Read session ID from .erk/scratch/session-id file."""
    session_id_file = Path(".erk/scratch/session-id")
    if session_id_file.exists():
        return session_id_file.read_text().strip()
    return None

# Test code
def test_uses_session_id_from_file(tmp_path: Path) -> None:
    with patch(
        "erk_kits.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue._get_session_id_from_file",
        return_value="file-session-id",
    ):
        result = runner.invoke(command, obj=DotAgentContext.for_test())
```

### After (with fakes)

```python
# Source code (refactored)
session_store = require_session_store(ctx)
effective_session_id = session_id or session_store.get_current_session_id()

# Test code
def test_uses_session_store_for_current_session_id(tmp_path: Path) -> None:
    fake_store = FakeClaudeCodeSessionStore(current_session_id="store-session-id")
    result = runner.invoke(
        command,
        obj=DotAgentContext.for_test(session_store=fake_store, cwd=tmp_path),
    )
```

## Benefits

1. **No import path coupling** - Mocks break when you rename/move functions
2. **Behavior-based testing** - Fakes implement real interfaces
3. **Reusable fixtures** - Same fake works across many tests
4. **Clear test intent** - Fake configuration shows expected state

## When Mocks Are Still Appropriate

Keep mocks when:

- Testing third-party library interactions (where you can't inject fakes)
- Verifying specific call sequences (e.g., logging)
- Testing error handling for specific exceptions

## Related Topics

- [Kit CLI Testing Patterns](kit-cli-testing.md) - General patterns for testing kit CLI commands
- [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) - Session store fake details
- [fake-driven-testing skill](/.claude/skills/fake-driven-testing/) - Complete 5-layer testing strategy
