# Plan: Add Kit CLI Command Testing Documentation

## Objective

Add documentation for the kit CLI command testing pattern to the `fake-driven-testing` skill.

## Status

- **Click 8.2+ stdout/stderr separation**: Already documented in this session (lines 207-232 of patterns.md)
- **Kit CLI command testing recipe**: Needs to be added

## Implementation

### File to Modify

`packages/dot-agent-kit/src/dot_agent_kit/data/kits/fake-driven-testing/skills/fake-driven-testing/references/patterns.md`

### Change: Add "Kit CLI Command Testing" Section

Add a new section after "Using CliRunner for CLI Tests" (around line 330, after "Why CliRunner (NOT subprocess)?").

**Content to add:**

```markdown
## Kit CLI Command Testing

**Pattern**: Test kit CLI commands using CliRunner with DotAgentContext.for_test() and fakes.

### Basic Structure

```python
from pathlib import Path
from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues
from dot_agent_kit.context import DotAgentContext

def test_kit_cli_command(tmp_path: Path) -> None:
    """Test a kit CLI command with fakes."""
    # 1. Configure fakes with initial state
    fake_gh = FakeGitHubIssues(
        issues={100: make_issue_info(100)},
        comments={100: ["comment body"]},
    )
    fake_git = FakeGit()

    # 2. Create CliRunner
    runner = CliRunner()

    # 3. Use isolated_filesystem for file operations
    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        # 4. Create required directories (e.g., .erk/scratch)
        (cwd / ".erk" / "scratch").mkdir(parents=True)

        # 5. Invoke command with DotAgentContext.for_test()
        result = runner.invoke(
            my_kit_command,
            ["arg1", "--option", "value"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh,
                git=fake_git,
                repo_root=cwd,
                cwd=cwd,
            ),
        )

    # 6. Assert results
    assert result.exit_code == 0, result.output
    # Parse JSON output if applicable
    output = json.loads(result.output)
    assert output["success"] is True
```

### Key Components

**DotAgentContext.for_test()**: Creates a test context with injected fakes:
- `github_issues`: FakeGitHubIssues for GitHub API operations
- `git`: FakeGit for git operations
- `repo_root`: Path to simulated repository root
- `cwd`: Current working directory

**isolated_filesystem**: Creates a temporary directory that:
- Isolates tests from real filesystem
- Auto-cleans up after test
- Use `temp_dir=tmp_path` to place inside pytest's tmp_path

**Required Directory Setup**: Some commands expect directories to exist:
- `.erk/scratch/` for scratch files
- `.impl/` for implementation plans
- `.claude/` for Claude artifacts

### Testing JSON Output

Many kit commands output JSON. Parse and assert:

```python
result = runner.invoke(command, args, obj=ctx)
assert result.exit_code == 0

output = json.loads(result.output)
assert output["success"] is True
assert output["issue_number"] == 100
assert "expected_field" in output
```

### Testing stdout vs stderr

Use `result.stdout` and `result.stderr` for commands that write to both:

```python
result = runner.invoke(command, ["--stdout"], obj=ctx)

# XML in stdout, JSON metadata in stderr
assert "<session" in result.stdout
metadata = json.loads(result.stderr)
assert metadata["success"] is True
```

### Example: Testing with FakeGitHubIssues

```python
from datetime import UTC, datetime
from erk_shared.github.issues.types import IssueInfo

def make_issue_info(number: int) -> IssueInfo:
    """Helper to create test IssueInfo."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Issue #{number}",
        body="Test body",
        state="OPEN",
        url=f"https://github.com/owner/repo/issues/{number}",
        labels=["test-label"],
        assignees=[],
        created_at=now,
        updated_at=now,
    )

def test_command_with_issues(tmp_path: Path) -> None:
    fake_gh = FakeGitHubIssues(
        issues={
            100: make_issue_info(100),
            200: make_issue_info(200),
        },
        comments={
            100: ["First comment", "Second comment"],
            200: [],
        },
    )
    # ... rest of test
```

### Why This Pattern?

**Fast**: No real GitHub API calls, no real git operations
**Reliable**: Deterministic behavior, no network flakiness
**Isolated**: Each test runs in clean environment
**Debuggable**: Can inspect fake state after operations
```

## Files to Reference

These tests demonstrate the pattern:
- `packages/dot-agent-kit/tests/unit/kits/erk/test_extract_session_from_issue.py`
- `packages/dot-agent-kit/tests/unit/kits/erk/test_plan_save_to_issue.py`
- `packages/dot-agent-kit/tests/unit/kits/erk/test_add_issue_label.py`