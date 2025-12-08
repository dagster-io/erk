---
title: Kit CLI Command Development
read_when:
  - "adding new kit CLI commands"
  - "creating kit commands from scratch"
  - "understanding kit command file structure"
  - "designing agent-consumable JSON output"
  - "handling errors in kit CLI commands"
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

import click

from dot_agent_kit.context_helpers import require_cwd


@click.command(name="your-command")
@click.argument("arg_name")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
@click.pass_context
def your_command(ctx: click.Context, arg_name: str, output_json: bool) -> None:
    """Brief docstring for --help."""
    # Use require_cwd(ctx) for worktree-scoped operations (NOT Path.cwd())
    worktree_path = require_cwd(ctx)

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

1. **Worktree-scoped**: Use `require_cwd(ctx)` for operations relative to current worktree (NOT `Path.cwd()`)
2. **JSON output**: Always provide `--json` flag for machine-readable output
3. **Exit codes**: Return 0 for success, 1 for errors
4. **Error handling**: Use `click.echo(..., err=True)` for errors, then `raise SystemExit(1)`
5. **Context injection**: Use `@click.pass_context` and `require_*()` helpers for dependencies

## Example Commands

Reference these existing commands for patterns:

- `check_impl.py` - Validation with dry-run mode
- `mark_step.py` - File mutation with JSON output
- `list_sessions.py` - Discovery with filtering options

## Structured JSON Output for Agent Consumption

Kit CLI commands consumed by agents should use typed dataclasses for consistent, parseable output.

### Success/Error Dataclass Pattern

Define separate frozen dataclasses for success and error responses:

```python
from dataclasses import asdict, dataclass
import json

@dataclass(frozen=True)
class ReviewCommentSuccess:
    """Success response for PR review comments."""

    success: bool  # Always True for success
    pr_number: int
    pr_url: str
    threads: list[dict]


@dataclass(frozen=True)
class ReviewCommentError:
    """Error response for PR review comments."""

    success: bool  # Always False for errors
    error_type: str  # Machine-readable error category
    message: str  # Human-readable explanation
```

**Key patterns:**

- Use `@dataclass(frozen=True)` for immutability
- Include `success: bool` field in both types
- Add `error_type` field for programmatic handling
- Separate types for success vs error (clearer than union)

### Exit Code 0 for Agent Consumption

Commands consumed by agents should return exit code 0 for both success AND graceful errors:

```python
@click.command(name="get-pr-review-comments")
@click.pass_context
def get_pr_review_comments(ctx: click.Context) -> None:
    """Fetch PR review comments for agent context injection."""
    github = require_github(ctx)

    try:
        threads = github.get_pr_review_threads(repo_root, pr_number)
    except RuntimeError as e:
        # Graceful error: exit 0 with error JSON
        result = ReviewCommentError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None  # Exit 0, not 1

    result = ReviewCommentSuccess(
        success=True,
        pr_number=pr_number,
        threads=formatted_threads,
    )
    click.echo(json.dumps(asdict(result), indent=2))
    raise SystemExit(0)
```

**Why exit 0 for errors?**

- Agents parse stdout JSON to determine success/failure
- Non-zero exit codes may cause shell pipelines to fail
- `|| true` pattern becomes unnecessary
- Error information is in the structured output, not the exit code

**When to use non-zero exit codes:**

- Context initialization failures (e.g., missing dependencies)
- Invalid command-line arguments (handled by Click)
- Unrecoverable internal errors

### Error Type Categories

Use consistent `error_type` values for programmatic handling:

| error_type                | When to use                         |
| ------------------------- | ----------------------------------- |
| `branch_detection_failed` | Could not determine current branch  |
| `no_pr_for_branch`        | No PR exists for the current branch |
| `pr_not_found`            | Specified PR number doesn't exist   |
| `github_api_failed`       | GitHub API call failed              |
| `resolution_failed`       | Thread/comment resolution failed    |
| `invalid_progress_format` | YAML/progress file parsing error    |

### Complete Example

```python
"""Resolve a PR review thread via GraphQL mutation.

Usage:
    dot-agent run erk resolve-review-thread --thread-id "PRRT_xxxx"

Output:
    JSON with success status

Exit Codes:
    0: Always (even on error, to support || true pattern)
    1: Context not initialized
"""

import json
from dataclasses import asdict, dataclass

import click

from dot_agent_kit.context_helpers import require_github, require_repo_root


@dataclass(frozen=True)
class ResolveThreadSuccess:
    """Success response for thread resolution."""

    success: bool
    thread_id: str


@dataclass(frozen=True)
class ResolveThreadError:
    """Error response for thread resolution."""

    success: bool
    error_type: str
    message: str


@click.command(name="resolve-review-thread")
@click.option("--thread-id", required=True, help="GraphQL node ID of the thread")
@click.pass_context
def resolve_review_thread(ctx: click.Context, thread_id: str) -> None:
    """Resolve a PR review thread."""
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)

    try:
        resolved = github.resolve_review_thread(repo_root, thread_id)
    except RuntimeError as e:
        result = ResolveThreadError(
            success=False,
            error_type="github_api_failed",
            message=str(e),
        )
        click.echo(json.dumps(asdict(result), indent=2))
        raise SystemExit(0) from None

    if resolved:
        result_success = ResolveThreadSuccess(success=True, thread_id=thread_id)
        click.echo(json.dumps(asdict(result_success), indent=2))
    else:
        result_error = ResolveThreadError(
            success=False,
            error_type="resolution_failed",
            message=f"Failed to resolve thread {thread_id}",
        )
        click.echo(json.dumps(asdict(result_error), indent=2))

    raise SystemExit(0)
```

## Related Documentation

- **[cli-commands.md](cli-commands.md)** — Python/LLM boundary patterns for kit commands
- **[code-architecture.md](code-architecture.md)** — Kit code organization
- **[dependency-injection.md](dependency-injection.md)** — Using DotAgentContext in commands
