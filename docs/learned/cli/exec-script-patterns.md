---
title: Exec Script Patterns
category: cli
read_when:
  - "Creating new exec CLI commands"
tripwires:
  - action: "importing from erk_shared.gateway when creating exec commands"
    warning: "Gateway ABCs use submodule paths: `erk_shared.gateway.{service}.{resource}.abc`"
---

# Exec Script Patterns

## Template Structure

### 1. Result Dataclasses

```python
@dataclass(frozen=True)
class MyCommandSuccess:
    success: Literal[True]
    # Command-specific fields
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
    """Brief description."""
    git = require_git(ctx)
    github_issues = require_github_issues(ctx)

    result = _my_command_impl(git, github_issues, arg_name)

    click.echo(json.dumps(asdict(result)))
    if isinstance(result, MyCommandError):
        raise SystemExit(1)
```

### 3. Gateway Import Paths

**IMPORTANT:** Gateway ABCs use submodule paths.

```python
# Correct
from erk_shared.gateway.github.issues.abc import GitHubIssues

# Incorrect - will raise ImportError
from erk_shared.gateway.github.abc import GitHubIssues
```

### 4. Plan Metadata Extraction

Reuse existing functions:

```python
from erk.cli.commands.exec.scripts.plan_submit_for_review import (
    extract_plan_header_comment_id,
    extract_plan_from_comment,
)
```

## Error Code Convention

Use lowercase snake_case error codes that are:

- Machine-readable (for programmatic handling)
- Descriptive (e.g., `missing_erk_plan_label` not `invalid_input`)
- Actionable (users understand what went wrong)

## Reference Implementations

- `plan_submit_for_review.py` - Plan content extraction
- `plan_create_review_branch.py` - Branch creation with plan file
