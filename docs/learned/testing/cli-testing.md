---
title: CLI Testing Patterns
read_when:
  - "writing tests for erk CLI commands"
  - "using ErkContext.for_test()"
  - "testing Click commands with context"
---

# CLI Testing Patterns

This document covers testing patterns specific to erk CLI commands that use `ErkContext` for dependency injection.

## Overview

Erk CLI commands use Click's context system (`@click.pass_context`) to receive dependencies. Testing these commands requires passing a test context via the `obj` parameter to `CliRunner.invoke()`.

## The ErkContext.for_test() Pattern

`ErkContext.for_test()` is the canonical factory method for creating test contexts with fake dependencies.

### Basic Usage

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

### Why This Pattern?

This pattern is **mandatory** for testing erk CLI commands because:

1. **Layer 4 testing** - Tests business logic over fakes (70% of tests should be Layer 4)
2. **No subprocess calls** - Uses in-memory fakes instead of real git/gh/gt commands
3. **Fast tests** - Completes instantly without external dependencies
4. **Clear test isolation** - Each test has its own independent fake state
5. **Full control** - Can pre-configure fake state for specific test scenarios

### API Signature

```python
@staticmethod
def for_test(
    github_issues: GitHubIssues | None = None,
    git: Git | None = None,
    github: GitHub | None = None,
    session_store: ClaudeCodeSessionStore | None = None,
    debug: bool = False,
    repo_root: Path | None = None,
    cwd: Path | None = None,
) -> "DotAgentContext":
    """Create test context with optional pre-configured implementations.

    All parameters are optional. Unspecified values default to fakes:
    - github_issues: Defaults to FakeGitHubIssues()
    - git: Defaults to FakeGit()
    - github: Defaults to FakeGitHub()
    - session_store: Defaults to FakeClaudeCodeSessionStore()
    - repo_root: Defaults to Path("/fake/repo")
    - cwd: Defaults to Path("/fake/worktree")

    Returns:
        DotAgentContext configured with provided values and test defaults
    """
```

## Testing Patterns

### Pattern 1: Default Fakes

When you don't need to inspect fake state, use defaults:

```python
def test_command_with_defaults() -> None:
    """Test command using default fake implementations."""
    runner = CliRunner()

    result = runner.invoke(
        my_command,
        ["--format", "json"],
        obj=DotAgentContext.for_test(),  # Uses all defaults
    )

    assert result.exit_code == 0
```

### Pattern 2: Pre-Configured Fakes

When you need to inspect fake state or pre-configure behavior:

```python
def test_command_creates_issue() -> None:
    """Test command creates GitHub issue."""
    # Arrange: Create fake we can inspect later
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Act: Run command with our fake
    result = runner.invoke(
        create_issue_command,
        ["--title", "Test Issue"],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    # Assert: Inspect fake state
    assert result.exit_code == 0
    assert len(fake_gh.created_issues) == 1
    title, body, labels = fake_gh.created_issues[0]
    assert title == "Test Issue"
```

### Pattern 3: Custom Paths with tmp_path

When command interacts with filesystem:

```python
def test_command_with_filesystem(tmp_path: Path) -> None:
    """Test command with real filesystem paths."""
    # Arrange: Set up test directory structure
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Test Plan")

    fake_git = FakeGit()
    runner = CliRunner()

    # Act: Run command with custom paths
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(
            git=fake_git,
            repo_root=tmp_path,
            cwd=tmp_path,
        ),
    )

    # Assert
    assert result.exit_code == 0
    assert (tmp_path / "output.txt").exists()
```

### Pattern 4: Testing Error Handling

When testing error paths:

```python
def test_command_handles_missing_issue() -> None:
    """Test command handles missing GitHub issue gracefully."""
    # Arrange: Empty fake (no issues)
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    # Act: Run command that expects issue #999
    result = runner.invoke(
        my_command,
        ["999"],
        obj=DotAgentContext.for_test(github_issues=fake_gh),
    )

    # Assert: Command exits with error
    assert result.exit_code == 1
    assert "Issue #999 not found" in result.output
```

### Pattern 5: Multiple Dependencies

When command uses multiple dependencies:

```python
def test_command_with_multiple_dependencies() -> None:
    """Test command that uses git, github, and github_issues."""
    # Arrange: Create multiple fakes
    fake_git = FakeGit()
    fake_gh = FakeGitHub()
    fake_gh_issues = FakeGitHubIssues()
    runner = CliRunner()

    # Pre-configure git state
    fake_git.branches["feature"] = "abc123"
    fake_git.current_branch = "feature"

    # Act
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(
            git=fake_git,
            github=fake_gh,
            github_issues=fake_gh_issues,
        ),
    )

    # Assert: Check all fakes were used correctly
    assert result.exit_code == 0
    assert len(fake_gh_issues.created_issues) == 1
    assert len(fake_gh.created_prs) == 1
```

## Real-World Examples

### Example 1: Testing plan-save-to-issue

From `test_plan_save_to_issue.py`:

```python
def test_plan_save_to_issue_success(plans_dir: Path, tmp_path: Path) -> None:
    """Test successful plan extraction and issue creation."""
    # Arrange: Create plan file and configure fakes
    plan = "# My Feature\n\n- Step 1\n- Step 2"
    (plans_dir / "test-project-abc123.md").write_text(plan)

    fake_gh = FakeGitHubIssues()
    fake_git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeCodeSessionStore(current_session_id=None)

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
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["title"] == "My Feature"
```

**Key points:**

- Uses `DotAgentContext.for_test()` with multiple fakes
- No mocks needed - all dependencies injected via fakes
- Inspects fake state after command execution
- Validates JSON output format

### Example 2: Testing with Session Store

```python
def test_uses_session_store_for_current_session_id(tmp_path: Path) -> None:
    """Test that command uses session store for current session ID."""
    session_id = "store-session-abc123"
    session_content = '{"type": "user", "message": {"content": "test"}}\n'

    fake_store = FakeClaudeCodeSessionStore(
        current_session_id=session_id,
        projects={
            tmp_path: FakeProject(
                sessions={
                    session_id: FakeSessionData(
                        content=session_content,
                        size_bytes=2000,
                        modified_at=1234567890.0,
                    )
                }
            )
        },
    )

    result = runner.invoke(
        my_command,
        ["--format", "json"],
        obj=DotAgentContext.for_test(session_store=fake_store, cwd=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["session_ids"] == [session_id]
```

**Key points:**

- Uses `FakeClaudeCodeSessionStore` for session data
- No file system or mocking needed for session ID lookup
- See [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) for more details

## Comparison with Other Testing Approaches

### vs CliRunner with Real Context

❌ **DON'T DO THIS:**

```python
def test_command_with_real_context() -> None:
    """BAD: Uses real subprocess calls."""
    runner = CliRunner()
    result = runner.invoke(my_command)  # No obj= parameter
    # This will call real git/gh/gt commands!
```

✅ **DO THIS:**

```python
def test_command_with_fake_context() -> None:
    """GOOD: Uses fake implementations."""
    runner = CliRunner()
    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(),  # Uses fakes
    )
```

### vs monkeypatch

**Use `DotAgentContext.for_test()` when:**

- Command accepts `@click.pass_context` and uses `require_*()` helpers
- You want to inspect fake state after execution
- Command is an erk CLI command

**Use `monkeypatch` when:**

- Command creates dependencies internally (not via context)
- Mocking factory functions or module-level imports
- Testing code that doesn't use DotAgentContext

**Example using monkeypatch:**

```python
def test_command_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test command that internally creates dependencies."""
    fake_store, _ = create_plan_store_with_plans({})

    # Mock the factory that creates the dependency
    monkeypatch.setattr(
        "my_module.GitHubPlanStore",
        lambda github_issues: fake_store,
    )

    runner = CliRunner()
    result = runner.invoke(my_command, ["--arg", "value"])

    assert result.exit_code == 0
```

## Testing Checklist

When writing tests for erk CLI commands:

- [ ] Use `DotAgentContext.for_test()` to create test context
- [ ] Pass context via `obj=` parameter to `runner.invoke()`
- [ ] Create separate fakes when you need to inspect state
- [ ] Use `tmp_path` for filesystem interactions (never hardcode paths)
- [ ] Test both success and error paths
- [ ] Validate exit codes and output formats
- [ ] Ensure tests complete instantly (no subprocess calls)

## Common Mistakes

### Mistake 1: Not Passing Context

```python
# ❌ WRONG: Command will fail because ctx.obj is None
result = runner.invoke(my_command, ["--arg", "value"])
```

```python
# ✅ CORRECT: Pass context via obj parameter
result = runner.invoke(
    my_command,
    ["--arg", "value"],
    obj=DotAgentContext.for_test(),
)
```

### Mistake 2: Creating Fake Inside invoke()

```python
# ❌ WRONG: Can't inspect fake state after test
result = runner.invoke(
    my_command,
    obj=DotAgentContext.for_test(github_issues=FakeGitHubIssues()),
)
# No reference to the fake!
```

```python
# ✅ CORRECT: Create fake before invoke()
fake_gh = FakeGitHubIssues()
result = runner.invoke(
    my_command,
    obj=DotAgentContext.for_test(github_issues=fake_gh),
)
# Can now assert on fake_gh.created_issues
```

### Mistake 3: Hardcoding Paths

```python
# ❌ WRONG: Hardcoded path might not exist
result = runner.invoke(
    my_command,
    obj=DotAgentContext.for_test(cwd=Path("/fake/worktree")),
)
# Command tries to read /fake/worktree/.impl/plan.md - fails!
```

```python
# ✅ CORRECT: Use tmp_path fixture
def test_command(tmp_path: Path) -> None:
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Test")

    result = runner.invoke(
        my_command,
        obj=DotAgentContext.for_test(cwd=tmp_path),
    )
```

## Testing Commands That Use Current Working Directory

Some erk CLI commands use `Path.cwd()` internally rather than receiving the path via `ErkContext`. For these commands, use `monkeypatch.chdir()` to change the working directory before invoking the command.

### Pattern: Using monkeypatch.chdir()

```python
def test_command_with_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test command that reads from current working directory."""
    # Arrange: Setup test files in tmp_path
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Test Plan\n\nContent here.")

    # Change to the test directory BEFORE invoking command
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(my_command, ["--json"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["success"] is True
```

### Key Points

1. **Setup files BEFORE changing directory** - Create the test file structure in `tmp_path` first
2. **Use `monkeypatch.chdir()`** - This changes cwd for the duration of the test and auto-reverts
3. **Use `tmp_path` fixture** - Never hardcode paths like `/tmp/test` or `/fake/path`
4. **Order matters** - `monkeypatch.chdir()` must happen before `runner.invoke()`

### When to Use monkeypatch.chdir() vs DotAgentContext

| Scenario                                | Use                                 |
| --------------------------------------- | ----------------------------------- |
| Command uses `ctx.obj.cwd` from context | `ErkContext.for_test(cwd=tmp_path)` |
| Command uses `Path.cwd()` directly      | `monkeypatch.chdir(tmp_path)`       |
| Command does both                       | Both approaches together            |

### Example: Testing impl-init Command

```python
def test_impl_init_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test impl-init with valid .impl folder."""
    # Arrange: Create .impl folder with plan
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Implementation Plan\n\n## Phase 1\n...")

    # Change to test directory
    monkeypatch.chdir(tmp_path)

    # Act
    runner = CliRunner()
    result = runner.invoke(impl_init, ["--json"])

    # Assert
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert "phases" in data
```

## See Also

- [fake-driven-testing skill](/.claude/skills/fake-driven-testing/) - Complete 5-layer testing strategy
- [Testing Guide](testing.md) - General testing patterns
- [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) - Session store fake details
- [Mock Elimination Workflow](mock-elimination.md) - Replacing mocks with fakes
