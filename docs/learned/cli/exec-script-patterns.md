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

## Parameterized URL Construction

Exec scripts that construct GitHub URLs (issue links, PR links) must use `get_repo_identifier(ctx)` instead of hardcoding repository names.

**Pattern**:

```python
from erk_shared.context.helpers import get_repo_identifier

repo_identifier = get_repo_identifier(ctx)
if repo_identifier is None:
    # Handle missing repo — return error result
    ...

url = f"https://github.com/{repo_identifier}/issues/{issue_number}"
```

**LBYL**: Always check `repo_identifier is not None` before constructing URLs. The function returns `None` when the repository cannot be determined from git remote.

**Scripts using this pattern**:

- `plan_create_review_pr.py` — Constructs PR and issue URLs for review workflow
- `plan_save_to_issue.py` — Constructs source repo reference for cross-repo plans
- `run_review.py` — Gets repository name for review context

## Reference Implementations

- `plan_submit_for_review.py` - Plan content extraction
- `plan_create_review_branch.py` - Branch creation with plan file
