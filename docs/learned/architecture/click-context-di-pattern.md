---
title: Click Context Dependency Injection Pattern
read_when:
  - "adding dependency injection to a Click command"
  - "using @click.pass_context with require_*() helpers"
  - "testing Click commands with ErkContext"
tripwires:
  - action: "accessing ctx.obj directly without a require_*() helper"
    warning: "Use typed require_*() helpers (require_issues, require_git, require_cwd, etc.) instead of direct ctx.obj access. Helpers provide type narrowing and clear error messages."
---

# Click Context Dependency Injection Pattern

Erk CLI commands use Click's context system for dependency injection, with typed helper functions that extract and narrow dependencies from the context object.

## Three-Layer Pattern

### Layer 1: Click Decorator

```python
@click.command()
@click.option("--issue", type=int, required=True)
@click.pass_context
def my_command(ctx: click.Context, *, issue: int) -> None:
    """Command description."""
    issues = require_issues(ctx)
    _my_command_impl(issues=issues, issue=issue)
```

### Layer 2: require\_\*() Helper

<!-- Source: packages/erk-shared/src/erk_shared/context/helpers.py:64-94 -->

```python
def require_issues(ctx: click.Context) -> GitHubIssues:
    """Extract GitHubIssues from Click context."""
    if ctx.obj is None:
        click.echo("Error: Context not initialized", err=True)
        raise SystemExit(1)
    if not isinstance(ctx.obj, ErkContext):
        click.echo("Error: Context must be ErkContext", err=True)
        raise SystemExit(1)
    return ctx.obj.issues
```

Available helpers: `require_issues()`, `require_git()`, `require_cwd()`, `require_prompt_executor()`.

### Layer 3: Implementation Function

```python
def _my_command_impl(*, issues: GitHubIssues, issue: int) -> None:
    """Pure business logic, no Click dependency."""
    result = issues.get_issue(repo_root, issue)
    # ... business logic
```

## Testing via ErkContext.for_test()

The implementation function receives typed dependencies, making testing straightforward:

```python
def test_my_command() -> None:
    issues = FakeGitHubIssues(issues={1: IssueInfo(...)})
    runner = CliRunner()

    result = runner.invoke(
        my_command,
        ["--issue", "1"],
        obj=ErkContext.for_test(issues=issues),
    )

    assert result.exit_code == 0
```

## Why This Pattern

1. **Type safety**: `require_*()` helpers narrow `ctx.obj` to concrete types
2. **Testability**: Implementation functions accept typed interfaces, not Click contexts
3. **Clear errors**: Missing dependencies produce descriptive error messages, not AttributeError

## Reference Implementation

See `validate_claude_credentials.py` in `src/erk/cli/commands/exec/scripts/` for a complete example of the three-layer pattern with `@click.pass_context` → `require_*()` → implementation function.

## Related Documentation

- [CLI Testing Patterns](../testing/cli-testing.md) — Testing Click commands with ErkContext.for_test()
- [Erk Architecture Patterns](erk-architecture.md) — Broader DI patterns
