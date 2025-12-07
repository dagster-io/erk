---
title: Kit CLI Command Development
read_when:
  - "adding new kit CLI commands"
  - "creating kit commands from scratch"
  - "understanding kit command file structure"
---

# Kit CLI Command Development

This guide explains how to add new CLI commands to the erk kit.

## File Structure

Kit CLI commands live in the kit package:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/
├── kit.yaml                           # Command registration
└── kit_cli_commands/erk/
    └── your_command.py                # Implementation
```

## Step 1: Create the Command File

Create a Python file in `kit_cli_commands/erk/` with this pattern:

```python
"""Short description of what the command does.

Usage:
    dot-agent run erk your-command [options]

Exit Codes:
    0: Success
    1: Error
"""

import json
from pathlib import Path

import click


@click.command(name="your-command")
@click.argument("arg_name")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
def your_command(arg_name: str, output_json: bool) -> None:
    """Brief docstring for --help."""
    # Use Path.cwd() for worktree-scoped operations
    worktree_path = Path.cwd()

    # Implement logic...
    result = do_something(worktree_path, arg_name)

    if output_json:
        click.echo(json.dumps({"success": True, "result": result}))
    else:
        click.echo(f"Result: {result}")
```

## Step 2: Register in kit.yaml

Add entry to `kit_cli_commands:` section:

```yaml
kit_cli_commands:
  # ... existing commands
  - name: your-command
    path: kit_cli_commands/erk/your_command.py
    description: Short description for help text
```

## Invocation

Commands are invoked via:

```bash
dot-agent run erk your-command arg_value --json
```

## Key Patterns

1. **Worktree-scoped**: Use `Path.cwd()` for operations relative to current worktree
2. **JSON output**: Always provide `--json` flag for machine-readable output
3. **Exit codes**: Return 0 for success, 1 for errors
4. **Error handling**: Use `click.echo(..., err=True)` for errors, then `raise SystemExit(1)`

## Agent-Consumable JSON Output Pattern

For commands that agents will consume (not just humans), use structured dataclass responses instead of ad-hoc JSON dictionaries.

### Core Pattern

```python
from dataclasses import asdict, dataclass
import json

@dataclass(frozen=True)
class MyCommandSuccess:
    """Success response."""
    success: bool
    result: str
    details: dict

@dataclass(frozen=True)
class MyCommandError:
    """Error response."""
    success: bool
    error_type: str
    message: str

# In your command implementation
result = MyCommandSuccess(success=True, result="done", details={...})
click.echo(json.dumps(asdict(result), indent=2))
raise SystemExit(0)  # Exit 0 for BOTH success and graceful errors
```

### Key Principles

1. **Exit code 0 for both success AND graceful errors**: Agents parse JSON output. Non-zero exit codes should only indicate programming errors or missing context.

2. **Structured error types**: Use `error_type` field for programmatic error handling (e.g., `"pr_not_found"`, `"branch_detection_failed"`)

3. **Frozen dataclasses**: Use `@dataclass(frozen=True)` for immutability and clarity

4. **asdict() for serialization**: Use `asdict()` to convert dataclass to dict for JSON serialization

### Complete Example

```python
"""Fetch PR review comments for agent context injection.

Usage:
    dot-agent run erk get-pr-review-comments
    dot-agent run erk get-pr-review-comments --pr 123

Output:
    JSON with success status, PR info, and review threads

Exit Codes:
    0: Success (or graceful error with JSON output)
    1: Context not initialized
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import click
from erk_shared.github.types import PRNotFound

from dot_agent_kit.context_helpers import require_git, require_github, require_repo_root


@dataclass(frozen=True)
class ReviewCommentSuccess:
    """Success response for PR review comments."""
    success: bool
    pr_number: int
    pr_url: str
    pr_title: str
    threads: list[dict]


@dataclass(frozen=True)
class ReviewCommentError:
    """Error response for PR review comments."""
    success: bool
    error_type: str
    message: str


@click.command(name="get-pr-review-comments")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.pass_context
def get_pr_review_comments(ctx: click.Context, pr: int | None) -> None:
    """Fetch PR review comments for agent context injection."""
    # Get dependencies from context
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    git = require_git(ctx)

    # Determine PR number
    pr_number = pr
    if pr_number is None:
        # Get current branch and find its PR
        cwd = Path.cwd()
        branch = git.get_current_branch(cwd)
        if branch is None:
            result = ReviewCommentError(
                success=False,
                error_type="branch_detection_failed",
                message="Could not determine current branch",
            )
            click.echo(json.dumps(asdict(result), indent=2))
            raise SystemExit(0)  # Exit 0 for graceful error

        pr_result = github.get_pr_for_branch(repo_root, branch)
        if isinstance(pr_result, PRNotFound):
            result = ReviewCommentError(
                success=False,
                error_type="no_pr_for_branch",
                message=f"No PR found for branch '{branch}'",
            )
            click.echo(json.dumps(asdict(result), indent=2))
            raise SystemExit(0)  # Exit 0 for graceful error

        pr_number = pr_result.number

    # Fetch PR details
    pr_result = github.get_pr(repo_root, pr_number)
    if isinstance(pr_result, PRNotFound):
        result = ReviewCommentError(
            success=False,
            error_type="pr_not_found",
            message=f"PR #{pr_number} not found",
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0)  # Exit 0 for graceful error

    # Fetch review threads
    try:
        threads = github.get_pr_review_threads(repo_root, pr_number)
    except RuntimeError as e:
        result = ReviewCommentError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None  # Exit 0 for graceful error

    # Success case
    result_success = ReviewCommentSuccess(
        success=True,
        pr_number=pr_number,
        pr_url=pr_result.url,
        pr_title=pr_result.title,
        threads=[format_thread(t) for t in threads],
    )
    click.echo(json.dumps(asdict(result_success), indent=2))
    raise SystemExit(0)
```

### Error Handling Guidelines

**Exit 0 for graceful errors:**

```python
# ✅ CORRECT: Resource not found → structured error, exit 0
if isinstance(pr_result, PRNotFound):
    result = ReviewCommentError(
        success=False,
        error_type="pr_not_found",
        message=f"PR #{pr_number} not found",
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)  # Agent can parse this
```

**Exit 1 for context failures:**

```python
# ✅ CORRECT: Missing required context → fail hard, exit 1
try:
    github = require_github(ctx)
except RuntimeError as e:
    click.echo(f"Error: {e}", err=True)
    raise SystemExit(1)  # Cannot proceed without context
```

### Structured Error Types

Use descriptive, programmatic error types:

| Error Type                | Meaning                            |
| ------------------------- | ---------------------------------- |
| `branch_detection_failed` | Could not determine current branch |
| `no_pr_for_branch`        | Branch has no associated PR        |
| `pr_not_found`            | Specified PR doesn't exist         |
| `github_api_failed`       | GitHub API call failed             |
| `invalid_progress_format` | File format validation failed      |

Benefits:

- Agents can handle specific errors programmatically
- Errors are self-documenting
- Easy to extend with new error types

### Testing Pattern

Test both success and error cases with frozen dataclasses:

```python
def test_command_success() -> None:
    """Test successful command execution."""
    # Arrange
    github = FakeGitHub(prs={123: make_pr(...)})

    # Act
    result = runner.invoke(get_pr_review_comments, ["--pr", "123"], obj=make_context(github))

    # Assert
    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["pr_number"] == 123


def test_command_pr_not_found() -> None:
    """Test graceful error when PR not found."""
    # Arrange
    github = FakeGitHub(prs={})  # Empty - no PRs

    # Act
    result = runner.invoke(get_pr_review_comments, ["--pr", "999"], obj=make_context(github))

    # Assert
    assert result.exit_code == 0  # Graceful error still exits 0
    output = json.loads(result.output)
    assert output["success"] is False
    assert output["error_type"] == "pr_not_found"
```

## Example Commands

Reference these existing commands for patterns:

- `check_impl.py` - Validation with dry-run mode
- `mark_step.py` - File mutation with JSON output
- `list_sessions.py` - Discovery with filtering options
- `get_pr_review_comments.py` - Agent-consumable JSON with structured errors

## Related Documentation

- **[cli-commands.md](cli-commands.md)** — Python/LLM boundary patterns for kit commands
- **[code-architecture.md](code-architecture.md)** — Kit code organization
- **[dependency-injection.md](dependency-injection.md)** — Using DotAgentContext in commands
