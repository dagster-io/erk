---
title: CLI Testing Patterns
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "writing tests for erk CLI commands"
  - "using ErkContext.for_test()"
  - "testing Click commands with context"
tripwires:
  - action: "testing code that reads ERK_PLAN_BACKEND or other environment variables via CliRunner"
    warning: "CliRunner env var isolation: ambient env vars from the developer shell leak into CliRunner by default and cause intermittent test failures. Use CliRunner(env={'ERK_PLAN_BACKEND': '...'}) to override, or CliRunner(mix_stderr=False, env={}) to isolate completely. Never rely on ambient env being clean."
    score: 7
  - action: "renaming a user-facing string in CLI output and updating related test assertions"
    warning: "Test assertion lag: after renaming display strings (e.g., 'issue' → 'plan'), grep all test files for the old literal before committing. Tests using old string literals against stale snapshots will silently pass — the failure only surfaces in CI on a clean checkout."
    score: 6
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
from erk_shared.context.context import ErkContext
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues

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

<!-- Source: packages/erk-shared/src/erk_shared/context/context.py -->

See `ErkContext.for_test()` method in `packages/erk-shared/src/erk_shared/context/context.py` for complete API signature and default values. Key parameters include `github_issues`, `git`, `github`, `claude_installation`, `prompt_executor`, `debug`, `repo_root`, `cwd`, and `repo_info`.

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
        obj=ErkContext.for_test(),  # Uses all defaults
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
        obj=ErkContext.for_test(github_issues=fake_gh),
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
        obj=ErkContext.for_test(
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
        obj=ErkContext.for_test(github_issues=fake_gh),
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

    # Act
    result = runner.invoke(
        my_command,
        obj=ErkContext.for_test(
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

From `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py`:

```python
from erk_shared.context.context import ErkContext
from erk_shared.gateway.claude_installation.fake import FakeClaudeInstallation
from erk_shared.gateway.github.issues.fake import FakeGitHubIssues

def test_plan_save_to_issue_success() -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    plan_content = """# My Feature

This is a comprehensive feature plan that includes all the necessary details.

- Step 1: Implement the feature
- Step 2: Add tests for the feature"""
    fake_store = FakeClaudeInstallation.for_test(plans={"test-plan": plan_content})
    runner = CliRunner()

    result = runner.invoke(
        plan_save_to_issue,
        ["--format", "json"],
        obj=ErkContext.for_test(
            github_issues=fake_gh,
            claude_installation=fake_store,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["title"] == "My Feature"
```

**Key points:**

- Uses `ErkContext.for_test()` with multiple fakes
- No mocks needed - all dependencies injected via fakes
- Inspects fake state after command execution
- Validates JSON output format

### Example 2: Testing with Claude Installation Fake

```python
from erk_shared.gateway.claude_installation.fake import (
    FakeClaudeInstallation,
    FakeProject,
    FakeSessionData,
)

def test_uses_session_data(tmp_path: Path) -> None:
    """Test that command uses session data from claude installation."""
    session_id = "store-session-abc123"
    session_content = '{"type": "user", "message": {"content": "test"}}\n'

    fake_installation = FakeClaudeInstallation.for_test(
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
        obj=ErkContext.for_test(claude_installation=fake_installation, cwd=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["session_ids"] == [session_id]
```

**Key points:**

- Uses `FakeClaudeInstallation` with `FakeProject` and `FakeSessionData`
- No file system or mocking needed for session data
- See [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) for more details

## Comparison with Other Testing Approaches

### vs CliRunner with Real Context

**DON'T DO THIS:**

```python
def test_command_with_real_context() -> None:
    """BAD: Uses real subprocess calls."""
    runner = CliRunner()
    result = runner.invoke(my_command)  # No obj= parameter
    # This will call real git/gh/gt commands!
```

**DO THIS:**

```python
def test_command_with_fake_context() -> None:
    """GOOD: Uses fake implementations."""
    runner = CliRunner()
    result = runner.invoke(
        my_command,
        obj=ErkContext.for_test(),  # Uses fakes
    )
```

### vs monkeypatch

**Use `ErkContext.for_test()` when:**

- Command accepts `@click.pass_context` and uses `require_*()` helpers
- You want to inspect fake state after execution
- Command is an erk CLI command

**Use `monkeypatch` when:**

- Command creates dependencies internally (not via context)
- Mocking factory functions or module-level imports
- Testing code that doesn't use ErkContext

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

- [ ] Use `ErkContext.for_test()` to create test context
- [ ] Pass context via `obj=` parameter to `runner.invoke()`
- [ ] Create separate fakes when you need to inspect state
- [ ] Use `tmp_path` for filesystem interactions (never hardcode paths)
- [ ] Test both success and error paths
- [ ] Validate exit codes and output formats
- [ ] Ensure tests complete instantly (no subprocess calls)

## Common Mistakes

### Mistake 1: Not Passing Context

```python
# WRONG: Command will fail because ctx.obj is None
result = runner.invoke(my_command, ["--arg", "value"])
```

```python
# CORRECT: Pass context via obj parameter
result = runner.invoke(
    my_command,
    ["--arg", "value"],
    obj=ErkContext.for_test(),
)
```

### Mistake 2: Creating Fake Inside invoke()

```python
# WRONG: Can't inspect fake state after test
result = runner.invoke(
    my_command,
    obj=ErkContext.for_test(github_issues=FakeGitHubIssues()),
)
# No reference to the fake!
```

```python
# CORRECT: Create fake before invoke()
fake_gh = FakeGitHubIssues()
result = runner.invoke(
    my_command,
    obj=ErkContext.for_test(github_issues=fake_gh),
)
# Can now assert on fake_gh.created_issues
```

### Mistake 3: Hardcoding Paths

```python
# WRONG: Hardcoded path might not exist
result = runner.invoke(
    my_command,
    obj=ErkContext.for_test(cwd=Path("/fake/worktree")),
)
# Command tries to read /fake/worktree/.impl/plan.md - fails!
```

```python
# CORRECT: Use tmp_path fixture
def test_command(tmp_path: Path) -> None:
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan.md").write_text("# Test")

    result = runner.invoke(
        my_command,
        obj=ErkContext.for_test(cwd=tmp_path),
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

### When to Use monkeypatch.chdir() vs ErkContext

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

## Pattern 6: FakeGitHub with Shared FakeGitHubIssues

When testing code that uses both `PlanBackend` and direct `FakeGitHubIssues` operations, both must operate on the same instance:

```python
def test_plan_operations_with_shared_issues() -> None:
    """Test that plan_backend and direct issue operations share state."""
    issues = FakeGitHubIssues()
    runner = CliRunner()

    result = runner.invoke(
        my_command,
        obj=ErkContext.for_test(github_issues=issues),
    )

    # Both plan_backend metadata writes and direct issue queries
    # see the same data because they share the issues instance
    assert result.exit_code == 0
```

**Critical:** Always pass `issues=issues` to `build_workspace_test_context` when using custom `FakeGitHubIssues`. Without it, `plan_backend` operates on a different instance and metadata writes are invisible to your test assertions.

## See Also

- [fake-driven-testing skill](/.claude/skills/fake-driven-testing/) - Complete 5-layer testing strategy
- [Testing Guide](testing.md) - General testing patterns
- [Testing with FakeClaudeCodeSessionStore](session-store-testing.md) - Session store fake details
- [Mock Elimination Workflow](mock-elimination.md) - Replacing mocks with fakes
