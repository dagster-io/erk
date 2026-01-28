---
title: Exec Script Patterns
read_when:
  - "creating new erk exec commands"
  - "structuring exec script implementations"
  - "following exec command templates"
---

# Exec Script Patterns

## Template Structure

Exec scripts follow a consistent template:

### 1. Result Dataclasses

Define frozen dataclasses for success and error responses:

```python
@dataclass(frozen=True)
class MyCommandSuccess:
    success: Literal[True]
    # Command-specific success fields
    result_value: str

@dataclass(frozen=True)
class MyCommandError:
    success: Literal[False]
    error: str  # Machine-readable error code
    message: str  # Human-readable description
```

### 2. Click Command Entry Point

```python
@click.command(name="my-command")
@click.argument("arg_name", type=int)
@click.pass_context
def my_command(ctx: click.Context, arg_name: int) -> None:
    """Brief description of command."""
    # Inject dependencies
    git = require_git(ctx)
    github_issues = require_github_issues(ctx)

    # Call implementation
    result = _my_command_impl(git, github_issues, arg_name)

    # Output JSON result
    click.echo(json.dumps(asdict(result)))

    # Exit with error code if failed
    if isinstance(result, MyCommandError):
        raise SystemExit(1)
```

### 3. Implementation Function

See source files for implementation patterns. The implementation function should:

- Take gateway ABCs as parameters for testability
- Return structured success/error dataclasses
- Use comprehensive error codes for machine-readable failures

### 4. Error Code Convention

Use lowercase snake_case error codes that are:

- Machine-readable (for programmatic handling)
- Descriptive (e.g., `missing_erk_plan_label` not `invalid_input`)
- Actionable (users can understand what went wrong)

### 5. Gateway Injection

Use Click context helpers:

- `require_git(ctx)` - Git operations
- `require_github_issues(ctx)` - GitHub issue operations
- `require_repo_root(ctx)` - Repository root path

## Examples

- `plan_create_review_branch.py` - Plan review branch creation
- `plan_submit_for_review.py` - Plan submission workflow
- `detect_trunk_branch.py` - Trunk branch detection

## Related Topics

- [erk exec Commands](erk-exec-commands.md) - Command reference
- [Exec Script Testing](../testing/exec-script-testing.md) - Testing patterns
- [Error Handling](error-handling.md) - Error handling patterns
