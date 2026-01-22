---
title: Exec Script Implementation Patterns
read_when:
  - "creating a new exec command"
  - "adding CLI command to src/erk/cli/commands/exec/scripts/"
  - "wrapping GitHub API operations"
tripwires:
  - action: "adding a new exec command to src/erk/cli/commands/exec/scripts/"
    warning: "Must register in 3 places: (1) src/erk/cli/commands/exec/group.py with exec_group.add_command(), (2) .claude/skills/erk-exec-reference/SKILL.md command table, (3) docs/learned/cli/exec-commands.md if public-facing. Missing registration causes silent documentation gaps."
---

# Exec Script Implementation Patterns

Exec scripts are small, focused CLI commands that wrap single operations for reuse across slash commands, CI scripts, and other erk tooling.

## When to Create an Exec Command

Create an exec command when:

- **Reusability**: The operation is needed in multiple places (slash commands, CI, other exec scripts)
- **Complexity**: The raw operation requires error handling, JSON parsing, or multiple steps
- **Rate limits**: You need to use REST API instead of `gh` porcelain commands

Do NOT create an exec command when:

- The operation is only used once (inline it instead)
- It's trivial with no error handling needed
- It duplicates existing functionality

## Exec Command Architecture

### Two Implementation Approaches

**1. Gateway Methods** (preferred): Use when gateway methods exist

```python
# close_issue_with_comment.py - uses gateway methods
github_issues = require_issues(ctx)
comment_id = github_issues.add_comment(repo_root, issue_number, comment)
github_issues.close_issue(repo_root, issue_number)
```

Benefits: Testable with fakes, supports dry-run, consistent error handling

**2. Direct `gh api`** (when necessary): Use when no gateway method exists

```python
# get_pr_commits.py - direct API call
result = subprocess.run(
    ["gh", "api", f"repos/{{owner}}/{{repo}}/pulls/{{pr_number}}/commits", "--jq", "..."],
    capture_output=True, text=True
)
```

When acceptable: Exec scripts only, where integration testing is the goal

### JSON Output Format

All exec commands return structured JSON:

**On success:**

```json
{
  "success": true,
  "resource_id": 123,
  "operation_specific_fields": "..."
}
```

**On error:**

```json
{
  "success": false,
  "error": "Descriptive error message",
  "resource_id": 123,
  "partial_success_info": "..."
}
```

### Exit Codes

| Code | Meaning                                    |
| ---- | ------------------------------------------ |
| 0    | Success                                    |
| 1    | Expected error (not found, validation)     |
| 2+   | Unexpected error (API failure, exceptions) |

### Error Handling for Multi-Step Operations

When combining operations, include partial success information:

```python
# Add comment first (partial success possible)
comment_id = github_issues.add_comment(repo_root, issue_number, comment)

try:
    github_issues.close_issue(repo_root, issue_number)
except Exception as e:
    # Include comment_id even though close failed
    click.echo(json.dumps({
        "success": False,
        "error": str(e),
        "comment_id": comment_id  # Partial success info
    }))
    raise SystemExit(1)
```

## Registration Checklist

After creating a new exec script, update:

1. `src/erk/cli/commands/exec/group.py` - register with `exec_group.add_command()`
2. `.claude/skills/erk-exec-reference/SKILL.md` - add to command summary table
3. `docs/learned/cli/exec-commands.md` - if command is public-facing

## Examples

- `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py`: Gateway method pattern, multi-step atomic operation
- `src/erk/cli/commands/exec/scripts/get_pr_commits.py`: Direct API pattern, REST endpoint wrapper

## Related Topics

- [GitHub API Rate Limits](../architecture/github-api-rate-limits.md) - Understanding REST vs GraphQL and why exec commands matter
- [Exec Script Testing](../testing/exec-script-testing.md) - How to test exec commands with proper context injection
