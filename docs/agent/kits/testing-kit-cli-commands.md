---
title: Testing Kit CLI Commands
read_when:
  - "writing tests for kit CLI commands"
  - "testing workflow-integrated commands with JSON output"
  - "using FakeGit and FakeGitHub for kit command testing"
  - "validating structured responses from kit CLI"
---

# Testing Kit CLI Commands

Comprehensive patterns for testing kit CLI commands that integrate with workflows, use structured JSON output, and coordinate with gateway fakes.

**Prerequisites**: Load `fake-driven-testing` skill for foundational testing architecture.

## Overview

Kit CLI commands require specialized testing approaches because they:

- Return structured JSON for agent consumption
- Integrate with git/GitHub operations via gateway abstractions
- Exit with code 0 even on errors (for graceful degradation)
- Support both CLI and programmatic invocation

## Quick Decision: Which Pattern Do I Need?

**Testing basic CLI command?**
→ Use [Pattern 1: Context Injection with CliRunner](#pattern-1-context-injection-with-clirunner)

**Testing complex workflows?**
→ Use [Pattern 2: Declarative Fake Builders](#pattern-2-declarative-fake-builders)

**Testing JSON output?**
→ See [JSON Output Validation](#json-output-validation)

**Testing error handling?**
→ See [Error Case Testing](#error-case-testing)

**Need complete examples?**
→ See [Complete Test Examples](#complete-test-examples)

## Core Testing Patterns

### Pattern 1: Context Injection with CliRunner

**Use for**: Unit testing CLI commands with minimal setup

```python
from click.testing import CliRunner
from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.kits.erk.list_sessions import list_sessions

def test_cli_success(tmp_path: Path) -> None:
    """Test CLI command with successful session listing."""
    git = FakeGit(
        current_branches={tmp_path: "feature-branch"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "abc123": FakeSessionData(
                        content=_user_msg("Test session"),
                        size_bytes=100,
                        modified_at=1234567890.0,
                    )
                }
            )
        }
    )
    context = DotAgentContext.for_test(
        git=git,
        session_store=fake_store,
        cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(list_sessions, [], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["sessions"]) == 1
```

**Key elements**:

- `DotAgentContext.for_test()`: Inject dependencies cleanly
- `CliRunner()`: Click's test runner (not subprocess)
- Scope fakes by path: `current_branches={tmp_path: "branch"}`

### Pattern 2: Declarative Fake Builders

**Use for**: Testing complex operations with fluent setup

```python
from dot_agent_kit.kits.gt.fake_ops import FakeGtKitOps
from dot_agent_kit.kits.gt.land_pr import execute_land_pr, render_events

def test_land_pr_success(tmp_path: Path) -> None:
    """Test successfully landing a PR with declarative setup."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-branch", parent="main")
        .with_pr(123, state="OPEN", title="Add new feature")
        .with_commits(3)
    )

    result = render_events(execute_land_pr(ops, tmp_path))

    assert isinstance(result, LandPrSuccess)
    assert result.success is True
    assert result.pr_number == 123
    assert result.branch_name == "feature-branch"
```

**Benefits**:

- Readable test setup
- No verbose mocking
- Chainable configuration
- Type-safe builders

### Pattern 3: Generator Operation Testing

**Use for**: Operations that yield progress events

Kit operations often yield `ProgressEvent` and `CompletionEvent` types. Use `render_events()` to consume the generator and return the final result:

```python
from dot_agent_kit.kits.gt.operation_types import render_events

def test_operation_with_progress(tmp_path: Path) -> None:
    """Test operation that yields progress events."""
    ops = FakeGtKitOps().with_branch("feature", parent="main")

    # render_events() consumes generator and returns final result
    result = render_events(execute_operation(ops, tmp_path))

    assert isinstance(result, OperationSuccess)
```

**Why `render_events()`?**

- Consumes the generator completely
- Returns the final `CompletionEvent` result
- Simplifies assertions on operation outcomes

### Pattern 4: Mutation Verification

**Use for**: Verifying side effects occurred correctly

```python
def test_verifies_mutations(tmp_path: Path) -> None:
    """Test that expected mutations occurred."""
    git = FakeGit(current_branches={tmp_path: "main"})

    # Perform operation
    execute_checkout(git, tmp_path, "feature-branch")

    # Verify mutation
    assert git.checked_out_branches == ["feature-branch"]
```

**Common mutations to verify**:

- `git.checked_out_branches`: Branches checked out
- `git.created_branches`: Branches created
- `github.merged_prs`: PRs merged
- `fake.created_worktrees`: Worktrees created

## JSON Output Validation

Kit CLI commands return structured JSON for agent consumption.

### Approach 1: Basic Structure Validation

```python
import json

def test_json_output(tmp_path: Path) -> None:
    """Test CLI outputs valid JSON with expected structure."""
    context = DotAgentContext.for_test(cwd=tmp_path)
    runner = CliRunner()
    result = runner.invoke(command, [], obj=context)

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify top-level structure
    assert output["success"] is True
    assert "data" in output
```

### Approach 2: Nested Structure Validation

```python
def test_nested_json_structure(tmp_path: Path) -> None:
    """Test nested JSON fields are present and correct."""
    # ... setup and invoke ...

    output = json.loads(result.output)

    # Verify expected keys
    assert "branch_context" in output
    assert "current_session_id" in output

    # Verify nested structure
    assert "current_branch" in output["branch_context"]
    assert "trunk_branch" in output["branch_context"]
```

### Approach 3: Type Checking JSON Fields

```python
def test_json_field_types(tmp_path: Path) -> None:
    """Test JSON fields have correct types."""
    # ... setup and invoke ...

    output = json.loads(result.output)

    # Check types
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["issue_url"], str)
    assert isinstance(output["labels"], list)
```

### Approach 4: Extracting JSON from Styled Output

Some commands output styled text followed by JSON. Extract the JSON:

```python
def extract_json_from_output(output: str) -> dict:
    """Extract JSON from CLI output with styled messages."""
    json_start = output.find("{")
    if json_start == -1:
        raise ValueError(f"No JSON found in output: {output}")

    brace_count = 0
    for i, char in enumerate(output[json_start:], start=json_start):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                json_str = output[json_start : i + 1]
                return json.loads(json_str)

    raise ValueError("Unclosed JSON object")

def test_extract_json_from_styled_output(tmp_path: Path) -> None:
    """Test extracting JSON from styled CLI output."""
    # ... invoke command that outputs styled text + JSON ...

    data = extract_json_from_output(result.output)
    assert data["success"] is True
```

## Error Case Testing

Kit CLI commands exit with code 0 even on errors (for graceful degradation).

### Testing Error Responses

```python
def test_error_with_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that errors output structured JSON."""
    from dot_agent_kit.cli_result import exit_with_error

    with pytest.raises(SystemExit) as exc_info:
        exit_with_error("validation_failed", "Invalid input provided")

    # Note: exit code is 0, not 1 (graceful degradation)
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    output = json.loads(captured.out)

    assert output["success"] is False
    assert output["error_type"] == "validation_failed"
    assert output["message"] == "Invalid input provided"
```

### Testing Error Scenarios

```python
def test_error_no_pr_exists(tmp_path: Path) -> None:
    """Test error when no PR exists for the branch."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-branch", parent="main")
        # Note: no PR configured
    )

    result = render_events(execute_land_pr(ops, tmp_path))

    assert isinstance(result, LandPrError)
    assert result.success is False
    assert result.error_type == "no_pr_found"
    assert "No PR found" in result.message
```

## Test File Organization

Organize tests into four logical sections:

```python
# ============================================================================
# 1. Helper Function Tests (Layer 3: Pure Unit Tests)
# ============================================================================

def test_format_relative_time_just_now() -> None:
    """Test relative time formatting for recent timestamps."""
    now = time.time()
    assert format_relative_time(now - 10) == "just now"

# ============================================================================
# 2. Success Case Tests (Layer 4: Business Logic over Fakes)
# ============================================================================

def test_list_sessions_success(tmp_path: Path) -> None:
    """Test successfully listing sessions."""
    # ... test implementation ...

# ============================================================================
# 3. Error Case Tests (Layer 4: Business Logic over Fakes)
# ============================================================================

def test_list_sessions_error_not_in_repo(tmp_path: Path) -> None:
    """Test error when not in a git repository."""
    # ... test implementation ...

# ============================================================================
# 4. Edge Cases (Layer 4: Business Logic over Fakes)
# ============================================================================

def test_list_sessions_min_size_boundary(tmp_path: Path) -> None:
    """Test boundary conditions for --min-size filter."""
    # ... test implementation ...
```

## Complete Test Examples

### Example 1: Testing Session Listing with Filters

```python
from click.testing import CliRunner
from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.kits.erk.list_sessions import list_sessions

def test_list_sessions_with_min_size_filter(tmp_path: Path) -> None:
    """Test that --min-size filters out small sessions."""
    git = FakeGit(
        current_branches={tmp_path: "feature"},
        trunk_branches={tmp_path: "main"},
    )
    fake_store = FakeClaudeCodeSessionStore(
        projects={
            tmp_path: FakeProject(
                sessions={
                    "small": FakeSessionData(
                        content=_user_msg("Short"),
                        size_bytes=50,  # Below threshold
                        modified_at=1234567890.0,
                    ),
                    "large": FakeSessionData(
                        content=_user_msg("Long content here"),
                        size_bytes=150,  # Above threshold
                        modified_at=1234567891.0,
                    ),
                }
            )
        }
    )
    context = DotAgentContext.for_test(
        git=git,
        session_store=fake_store,
        cwd=tmp_path
    )

    runner = CliRunner()
    result = runner.invoke(
        list_sessions,
        ["--min-size", "100"],
        obj=context
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert len(output["sessions"]) == 1
    assert output["sessions"][0]["session_id"] == "large"
```

### Example 2: Testing Worktree Creation from Issue

```python
from dot_agent_kit.kits.erk.fake_erk_wt_kit import FakeErkWtKit

def test_create_from_issue_number_success(tmp_path: Path) -> None:
    """Test creating worktree from plain issue number."""
    issue_body = """
    ## Implementation Plan
    - Step 1: Do thing
    - Step 2: Do other thing
    """

    fake = FakeErkWtKit(
        parse_results={
            "123": IssueParseResult(
                success=True,
                issue_number=123,
                message="Successfully parsed",
            )
        },
        issues={
            123: IssueData(
                number=123,
                title="Add Feature X",
                body=issue_body,
                state="open",
                url="https://github.com/owner/repo/issues/123",
                labels=["erk-plan"],
            )
        },
        worktree_result=WorktreeCreationResult(
            success=True,
            worktree_name="feature-x",
            worktree_path=str(tmp_path / "feature-x"),
            branch_name="issue-123-add-feature-x",
        ),
    )

    success, result = create_wt_from_issue_impl("123", fake)

    assert success is True
    assert isinstance(result, WorktreeCreationSuccess)
    assert result.issue_number == 123
    assert result.worktree_name == "feature-x"

    # Verify mutations
    assert len(fake.created_worktrees) == 1
    assert "## Implementation Plan" in fake.created_worktrees[0]
```

### Example 3: Testing PR Landing with Navigation

```python
from dot_agent_kit.kits.gt.fake_ops import FakeGtKitOps

def test_land_pr_with_auto_navigation(tmp_path: Path) -> None:
    """Test landing PR and navigating to child branch."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-1", parent="main")
        .with_branch("feature-2", parent="feature-1")  # Child branch
        .with_pr(123, state="OPEN", title="Feature 1")
    )

    result = render_events(
        execute_land_pr(ops, tmp_path, navigate_to_child=True)
    )

    assert isinstance(result, LandPrSuccess)
    assert result.navigated_to == "feature-2"

    # Verify checkout occurred
    git = ops.git
    assert isinstance(git, FakeGit)
    assert git.checked_out_branches == ["feature-2"]
```

## Best Practices

### 1. Use Frozen Dataclasses for Immutability

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class DotAgentContext:
    """Immutable context holding all dependencies."""
    github_issues: GitHubIssues
    git: Git
    github: GitHub
    session_store: ClaudeCodeSessionStore
```

### 2. Test Both Success and Error Paths

```python
# Success path
def test_operation_success(tmp_path: Path) -> None:
    """Test successful operation."""
    # ...

# Error paths
def test_operation_error_no_pr(tmp_path: Path) -> None:
    """Test error when no PR exists."""
    # ...

def test_operation_error_pr_closed(tmp_path: Path) -> None:
    """Test error when PR is closed."""
    # ...
```

### 3. Verify Mutations When Side Effects Matter

```python
def test_verifies_side_effects(tmp_path: Path) -> None:
    """Test that side effects occurred as expected."""
    git = FakeGit(current_branches={tmp_path: "main"})

    # Perform operation
    create_branch(git, tmp_path, "feature")

    # Verify mutation
    assert "feature" in git.created_branches
```

### 4. Use Descriptive Test Names

```python
# Good: Describes what and why
def test_list_sessions_min_size_filters_tiny_sessions(tmp_path: Path) -> None:
    """Test that --min-size filters out tiny sessions."""

# Bad: Vague
def test_list_sessions_filter(tmp_path: Path) -> None:
    """Test filtering."""
```

### 5. Test Edge Cases Explicitly

```python
def test_format_relative_time_boundary_30_seconds() -> None:
    """Test boundary at 30 seconds."""
    now = time.time()
    assert format_relative_time(now - 29) == "just now"
    assert format_relative_time(now - 31) == "0m ago"
```

## Common Pitfalls

### ❌ Don't Mock When Fakes Are Available

**Bad**:

```python
with patch("subprocess.run") as mock_run:
    mock_run.return_value = Mock(returncode=0)
```

**Good**:

```python
ops = FakeGtKitOps().with_branch("feature", parent="main")
```

### ❌ Don't Forget to Scope Fakes by Path

**Bad**:

```python
git = FakeGit(current_branches={"main"})  # String, not scoped
```

**Good**:

```python
git = FakeGit(current_branches={tmp_path: "main"})  # Scoped by path
```

### ❌ Don't Expect Exit Code 1 for Errors

Kit CLI commands exit with code 0 for graceful degradation:

**Bad**:

```python
assert result.exit_code == 1  # Won't happen!
```

**Good**:

```python
assert result.exit_code == 0
output = json.loads(result.output)
assert output["success"] is False
```

### ❌ Don't Forget to Reset Cache in Builders

When implementing builder patterns:

```python
def with_branch(self, branch: str, parent: str = "main") -> "FakeGtKitOps":
    """Set current branch and its parent."""
    self._branches[branch] = parent
    self._git_instance = None  # Reset cache!
    self._github_instance = None
    return self
```

## Common Test Fixtures

### CliRunner Fixture

```python
import pytest
from click.testing import CliRunner

@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()
```

### Test Data Helpers

```python
import json

def _user_msg(text: str) -> str:
    """Create JSON content for a user message."""
    return json.dumps({"type": "user", "message": {"content": text}})
```

## Related Documentation

- [Fake-Driven Testing](../../fake-driven-testing.md) - Overall testing architecture
- [Push-Down Pattern](push-down-pattern.md) - Kit CLI design philosophy
- [Kit CLI Commands](cli-commands.md) - Building kit CLI commands
