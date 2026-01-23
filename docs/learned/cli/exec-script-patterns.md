---
title: Exec Script Implementation Patterns
read_when:
  - "creating a new erk exec command"
  - "adding a script to src/erk/cli/commands/exec/scripts/"
  - "choosing between gateway methods and direct gh api calls"
  - "implementing rate-limit-safe GitHub operations"
tripwires:
  - action: "adding a new exec command to src/erk/cli/commands/exec/scripts/"
    warning: "Must register in group.py. Missing registration causes command to be unavailable."
---

# Exec Script Implementation Patterns

Patterns for implementing commands in `src/erk/cli/commands/exec/scripts/`.

## When to Create an Exec Command

Create a new exec command when:

- **Reusability**: Multiple commands/skills need the same operation
- **Complexity**: Logic is too complex for inline shell commands
- **Rate limits**: Operation needs REST API to avoid GraphQL rate limits
- **Atomicity**: Multiple API calls should succeed or fail together

## Implementation Approaches

### Approach 1: Gateway Methods

Use when the operation already exists or should exist in a gateway:

```python
from erk_shared.context.helpers import require_issues, require_repo_root

@click.command()
@click.pass_context
def close_issue_with_comment(ctx: click.Context, issue_number: int, *, comment: str) -> None:
    github_issues = require_issues(ctx)
    repo_root = require_repo_root(ctx)

    comment_id = github_issues.add_comment(repo_root, issue_number, comment)
    github_issues.close_issue(repo_root, issue_number)
```

Benefits: Testable with fakes, consistent error handling, dry-run support.

### Approach 2: Direct `gh api`

Use for one-off operations or when gateway abstraction adds no value:

```python
result = subprocess.run(
    [
        "gh", "api",
        f"repos/{{owner}}/{{repo}}/pulls/{pr_number}/commits",
        "--jq", "[.[] | {sha: .sha, message: .commit.message}]",
    ],
    capture_output=True,
    text=True,
    cwd=repo_root,
    check=False,
)
```

Note: Always use `gh api` (REST) instead of `gh pr view --json` (GraphQL) to avoid rate limits.

## JSON Output Format

All exec commands with structured output should use consistent JSON:

```python
# Success case
click.echo(json.dumps({
    "success": True,
    "pr_number": pr_number,
    "commits": commits,
}))

# Error case
click.echo(json.dumps({
    "success": False,
    "error": f"Failed to get commits: {result.stderr.strip()}",
}))
raise SystemExit(1)
```

## Exit Code Standards

| Exit Code | Meaning | When to Use                              |
| --------- | ------- | ---------------------------------------- |
| 0         | Success | Operation completed normally             |
| 1         | Error   | API error, not found, validation failure |

## Multi-Step Operations

For operations combining multiple API calls:

1. **Document partial failure states** in the error response
2. **Include already-completed data** so callers can recover
3. **Order operations** so failures leave system in valid state

Example from `close_issue_with_comment`:

```python
# First add the comment
comment_id = github_issues.add_comment(repo_root, issue_number, comment)

# Then close the issue - if this fails, include comment_id in error
try:
    github_issues.close_issue(repo_root, issue_number)
except RuntimeError as e:
    click.echo(json.dumps({
        "success": False,
        "error": f"Failed to close issue: {e}",
        "comment_id": comment_id,  # Caller knows comment was added
    }))
    raise SystemExit(1) from e
```

## Registration Checklist

After creating a new exec script:

1. **Import in group.py**: Add import at top of `src/erk/cli/commands/exec/group.py`
2. **Register command**: Add `exec_group.add_command(func, name="kebab-case-name")`
3. **Regenerate docs**: Run `erk-dev gen-exec-reference-docs`
4. **Add tests**: Create tests in `tests/integration/cli/commands/exec/scripts/`

## Related Documentation

- [Exec Script Testing Patterns](../testing/exec-script-testing.md) - Testing exec commands
- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - REST vs GraphQL quotas
- [GitHub Interface Patterns](../architecture/github-interface-patterns.md) - API access patterns
