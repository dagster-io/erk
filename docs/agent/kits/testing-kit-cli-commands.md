---
title: Testing Kit CLI Commands for Workflow Integration
read_when:
  - "writing tests for kit CLI commands"
  - "testing commands that output JSON"
  - "validating kit CLI command structure"
  - "using CliRunner for command testing"
---

# Testing Kit CLI Commands for Workflow Integration

This guide documents patterns for testing kit CLI commands, especially those designed for GitHub Actions workflow integration.

## Overview

Kit CLI commands pushed down from agent markdown (see [Push Down Pattern](push-down-pattern.md)) require robust testing because they're called by workflows and other agents that expect structured JSON responses.

**Key principle**: Kit CLI commands are the contract between agents/workflows and Python business logic. Test them thoroughly.

## Test Structure Pattern

### Three-Layer Testing Strategy

1. **Unit tests for implementation function** (Layer 4: Business logic over fakes)
2. **Unit tests for JSON structure** (Layer 4: Business logic over fakes)
3. **CLI command tests with CliRunner** (Layer 4: Business logic over fakes)

### File Organization

```
packages/dot-agent-kit/
├── src/dot_agent_kit/data/kits/{kit}/kit_cli_commands/{kit}/{command}.py
└── tests/unit/kits/{kit}/test_{command}.py
```

## Pattern 1: Dataclass-Based JSON Responses

### Implementation Structure

```python
# packages/dot-agent-kit/.../kit_cli_commands/erk/parse_issue_reference.py

from dataclasses import dataclass, asdict
from typing import Literal
import json
import click

@dataclass
class ParsedIssue:
    """Success result with parsed issue number."""
    success: bool
    issue_number: int

@dataclass
class ParseError:
    """Error result when parsing fails."""
    success: bool
    error: Literal["invalid_format", "invalid_number"]
    message: str

def _parse_issue_reference_impl(reference: str) -> ParsedIssue | ParseError:
    """Implementation logic (testable without Click)."""
    # ... implementation ...
    return ParsedIssue(success=True, issue_number=123)

@click.command(name="parse-issue-reference")
@click.argument("issue_reference")
def parse_issue_reference(issue_reference: str) -> None:
    """CLI command wrapper."""
    result = _parse_issue_reference_impl(issue_reference)
    click.echo(json.dumps(asdict(result), indent=2))

    if isinstance(result, ParseError):
        raise SystemExit(1)
```

**Key patterns:**

- Separate `_impl` function for business logic (testable without CLI)
- Dataclasses for structured responses (success and error types)
- Use `asdict()` for JSON serialization
- Exit code 1 for errors, 0 for success
- `success: bool` field for programmatic checking

### Testing Implementation Functions

```python
# tests/unit/kits/erk/test_parse_issue_reference.py

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.parse_issue_reference import (
    ParsedIssue,
    ParseError,
    _parse_issue_reference_impl as parse_issue_reference,
)

def test_parse_plain_number_success() -> None:
    """Test parsing plain issue number."""
    result = parse_issue_reference("776")

    assert isinstance(result, ParsedIssue)
    assert result.success is True
    assert result.issue_number == 776

def test_parse_invalid_input() -> None:
    """Test rejection of invalid input."""
    result = parse_issue_reference("not-a-number")

    assert isinstance(result, ParseError)
    assert result.success is False
    assert result.error == "invalid_format"
    assert "number or GitHub URL" in result.message
```

**Testing patterns:**

- Test `_impl` function directly (no CLI overhead)
- Use `isinstance()` to verify response type
- Assert on dataclass fields
- Test both success and error cases
- Organize tests with section comments (e.g., "# Plain Number Tests")

## Pattern 2: Testing CLI Commands with CliRunner

### Using Click's CliRunner

```python
from click.testing import CliRunner
import json

from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.parse_issue_reference import (
    parse_issue_reference as parse_issue_reference_command,
)

def test_cli_success_plain_number() -> None:
    """Test CLI command with plain issue number."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["776"])

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 776

def test_cli_invalid_input_exit_code() -> None:
    """Test CLI command exits with error code on invalid input."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["invalid"])

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error"] == "invalid_format"
```

**Key patterns:**

- Create `CliRunner()` instance per test (or use fixture)
- Use `runner.invoke(command, [args])`
- Assert on `exit_code` (0 for success, 1 for error)
- Parse `result.output` with `json.loads()`
- Validate JSON structure and values

### Testing JSON Structure

```python
def test_cli_json_output_structure_success() -> None:
    """Test that JSON output has expected structure on success."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["123"])

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "issue_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)

def test_cli_json_output_structure_error() -> None:
    """Test that JSON output has expected structure on error."""
    runner = CliRunner()
    result = runner.invoke(parse_issue_reference_command, ["invalid"])

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify expected keys
    assert "success" in output
    assert "error" in output
    assert "message" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert isinstance(output["message"], str)
```

**Why test structure?**

- Workflows parse JSON output programmatically
- Breaking structure changes break workflows
- Type validation catches serialization issues

## Pattern 3: Testing with Fixtures and Fakes

### Using pytest Fixtures

```python
import pytest
from pathlib import Path
from click.testing import CliRunner

@pytest.fixture
def runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()

@pytest.fixture
def impl_folder(tmp_path: Path) -> Path:
    """Create .impl/ folder with test files."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    plan_md = impl_dir / "plan.md"
    plan_md.write_text("# Test Plan\n\n1. Step one", encoding="utf-8")

    return impl_dir

def test_with_fixtures(runner: CliRunner, impl_folder: Path, monkeypatch) -> None:
    """Test using fixtures for setup."""
    monkeypatch.chdir(impl_folder.parent)

    result = runner.invoke(impl_init, ["--json"])
    assert result.exit_code == 0
```

**Fixture patterns:**

- `runner: CliRunner` fixture for command testing
- `tmp_path: Path` fixture (pytest built-in) for file operations
- `monkeypatch` fixture for changing directory
- Custom fixtures for complex test data setup

### Testing with Fakes (Generator-Based Operations)

```python
from tests.unit.kits.gt.fake_ops import FakeGtKitOps
from erk_shared.integrations.gt.cli import render_events
from erk_shared.integrations.gt.operations.pre_analysis import execute_pre_analysis

def test_pre_analysis_with_uncommitted_changes(tmp_path: Path) -> None:
    """Test pre-analysis when uncommitted changes exist."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-branch", parent="main")
        .with_uncommitted_files(["file.txt"])
        .with_commits(0)
    )

    result = render_events(execute_pre_analysis(ops, tmp_path))

    assert isinstance(result, PreAnalysisResult)
    assert result.success is True
    assert result.uncommitted_changes_committed is True
```

**Key patterns:**

- Builder pattern for fake configuration (`.with_*()` methods)
- `render_events()` consumes generator and returns final result
- Assert on result type and fields
- Fakes track mutations for assertion (see mutation tracking below)

## Pattern 4: Testing Mutations with Fake Tracking

### Mutation Tracking Properties

```python
def test_finalize_amends_local_commit(tmp_path: Path) -> None:
    """Test that finalize amends local commit with PR title and body."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-branch", parent="main")
        .with_commits(1)
        .with_pr(123, url="https://github.com/org/repo/pull/123")
    )

    # Seed the FakeGit with an initial commit to amend
    fake_git = ops.git
    fake_git._commits.append((tmp_path, "Original message", []))

    pr_title = "Add new feature"
    pr_body = "This PR adds a great new feature"

    result = render_events(
        execute_finalize(ops, tmp_path, pr_number=123,
                        pr_title=pr_title, pr_body=pr_body, diff_file=None)
    )

    assert isinstance(result, FinalizeResult)
    assert result.success is True

    # Verify local commit was amended using mutation tracking
    assert len(fake_git._commits) == 1
    amended_message = fake_git._commits[-1][1]
    assert amended_message == "Add new feature\n\nThis PR adds a great new feature"
```

**Mutation tracking patterns:**

- Access fake's internal state (e.g., `fake_git._commits`)
- Verify operations were performed (not just return values)
- Check mutation counts, contents, order
- Use for testing side effects (commits, PR updates, file writes)

### Testing PR Updates

```python
def test_finalize_updates_pr(tmp_path: Path) -> None:
    """Test that finalize updates PR title and body."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-branch", parent="main")
        .with_pr(123, url="https://github.com/org/repo/pull/123")
    )

    result = render_events(
        execute_finalize(ops, tmp_path, pr_number=123,
                        pr_title="New Title", pr_body="New Body", diff_file=None)
    )

    assert isinstance(result, FinalizeResult)
    assert result.success is True

    # Verify PR was updated using mutation tracking
    github = ops.github
    assert (123, "New Title") in github.updated_pr_titles

    # Check body was updated
    bodies = [body for pr_num, body in github.updated_pr_bodies if pr_num == 123]
    assert len(bodies) > 0
    assert "New Body" in bodies[0]
```

## Pattern 5: Test Organization and Documentation

### Test File Structure

```python
"""Tests for parse_issue_reference kit CLI command.

Tests parsing of GitHub issue references from both plain numbers and full URLs.
"""

import json
from click.testing import CliRunner

# ... imports ...

# ============================================================================
# 1. Plain Number Parsing Tests (4 tests)
# ============================================================================

def test_parse_plain_number_success() -> None:
    """Test parsing plain issue number."""
    # ...

# ============================================================================
# 2. GitHub URL Parsing Tests (8 tests)
# ============================================================================

def test_parse_github_url_success() -> None:
    """Test parsing full GitHub URL."""
    # ...

# ============================================================================
# 3. Invalid Input Tests (7 tests)
# ============================================================================

def test_parse_invalid_non_numeric() -> None:
    """Test rejection of non-numeric plain input."""
    # ...

# ============================================================================
# 4. CLI Command Tests (5 tests)
# ============================================================================

def test_cli_success_plain_number() -> None:
    """Test CLI command with plain issue number."""
    # ...
```

**Organization patterns:**

- Module docstring describes what's being tested
- Section comments with test counts
- Group related tests together
- Test names follow pattern: `test_{function}_{scenario}_{expected}`

### Test Documentation

```python
def test_pre_analysis_detects_pr_conflicts_from_github(tmp_path: Path) -> None:
    """Test that PR conflicts are detected and reported informational (not blocking)."""
    ops = (
        FakeGtKitOps()
        .with_repo_root(str(tmp_path))
        .with_branch("feature-branch", parent="master")
        .with_commits(1)
        .with_pr(123, url="https://github.com/org/repo/pull/123")
        .with_pr_conflicts(123)
    )

    result = render_events(execute_pre_analysis(ops, tmp_path))

    # Assert: Should succeed with conflict info included
    assert isinstance(result, PreAnalysisResult)
    assert result.success is True
    assert result.has_conflicts is True
```

**Documentation patterns:**

- Descriptive test names (what scenario, what expectation)
- Docstrings explain testing goals
- Comments before assertions explain expected behavior
- Focus on "why" not "what" in comments

## Pattern 6: Extracting JSON from Styled Output

### When CLI Output Contains Styled Messages

```python
def extract_json_from_output(output: str) -> dict:
    """Extract JSON object from CLI output that may contain styled messages.

    The CLI outputs styled messages (with ↳, ✓, etc.) followed by JSON.
    This function finds and parses the JSON portion.
    """
    # Find the start of JSON (first '{')
    json_start = output.find("{")
    if json_start == -1:
        raise ValueError(f"No JSON found in output: {output}")

    # Find matching closing brace
    brace_count = 0
    for i, char in enumerate(output[json_start:], start=json_start):
        if char == "{":
            brace_count += 1
        elif char == "}":
            brace_count -= 1
            if brace_count == 0:
                json_str = output[json_start : i + 1]
                return json.loads(json_str)

    raise ValueError(f"No complete JSON found in output: {output}")

def test_cli_with_styled_output() -> None:
    """Test extracting JSON from output with progress messages."""
    runner = CliRunner()
    result = runner.invoke(some_command, ["args"])

    # Output might be: "↳ Processing...\n✓ Done\n{\"success\": true}"
    output = extract_json_from_output(result.output)
    assert output["success"] is True
```

**When to use:**

- Commands that print styled progress messages
- Commands that use rich/click styling
- Workflows that need to parse JSON from mixed output

## Testing Checklist

When adding a new kit CLI command:

- [ ] Write unit tests for `_impl` function (business logic)
- [ ] Test success cases with valid inputs
- [ ] Test error cases with invalid inputs
- [ ] Test edge cases (empty strings, zero values, etc.)
- [ ] Write CLI command tests with CliRunner
- [ ] Test JSON output structure (success case)
- [ ] Test JSON output structure (error case)
- [ ] Verify exit codes (0 for success, 1 for error)
- [ ] Test with fixtures if command uses file system
- [ ] Use fakes if command integrates with Git/GitHub
- [ ] Add mutation tracking assertions for side effects
- [ ] Organize tests with section comments
- [ ] Document test intent in docstrings
- [ ] Follow naming pattern: `test_{function}_{scenario}_{expected}`

## Common Patterns Summary

| Pattern             | Use Case                | Example                                 |
| ------------------- | ----------------------- | --------------------------------------- |
| Dataclass responses | Structured JSON output  | `ParsedIssue`, `ParseError`             |
| `_impl` function    | Testable business logic | `_parse_issue_reference_impl()`         |
| CliRunner           | Testing CLI commands    | `runner.invoke(cmd, [args])`            |
| pytest fixtures     | Setup test data         | `tmp_path`, `impl_folder`               |
| Builder pattern     | Configure fakes         | `.with_branch().with_commits()`         |
| Mutation tracking   | Verify side effects     | `fake_git._commits`                     |
| `render_events()`   | Test generators         | `render_events(execute_pre_analysis())` |
| JSON extraction     | Parse mixed output      | `extract_json_from_output()`            |

## Related Documentation

- [Kit CLI Push Down Pattern](push-down-pattern.md) - When to create kit CLI commands
- [Fake-Driven Testing](../../fake-driven-testing/) - Testing strategy overview
- [Kit CLI Commands](cli-commands.md) - How to build kit CLI commands
