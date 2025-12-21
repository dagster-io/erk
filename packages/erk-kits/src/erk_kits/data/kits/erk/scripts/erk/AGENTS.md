# Kit CLI Script Standards

## Required Pattern: Click Context Dependency Injection

All kit CLI commands in this folder MUST use Click's context system for dependency injection.

### Required Pattern

```python
import click
from erk_shared.context.helpers import require_cwd

@click.command(name="my-command")
@click.pass_context
def my_command(ctx: click.Context) -> None:
    """Command description."""
    cwd = require_cwd(ctx)
    # Use cwd instead of Path.cwd()
```

### Why This Pattern?

1. **Testability**: Tests inject dependencies via `obj=ErkContext.for_test(cwd=tmp_path)`
2. **No monkeypatching**: Tests don't need `monkeypatch.chdir()` or filesystem manipulation
3. **Explicit dependencies**: All dependencies visible in function signature via context
4. **Consistency**: All commands follow the same pattern

### Available Helper Functions

From `erk_shared.context.helpers`:

| Helper                   | Returns  | Usage                     |
| ------------------------ | -------- | ------------------------- |
| `require_cwd(ctx)`       | `Path`   | Current working directory |
| `require_repo_root(ctx)` | `Path`   | Repository root path      |
| `require_git(ctx)`       | `Git`    | Git operations            |
| `require_github(ctx)`    | `GitHub` | GitHub operations         |

### Anti-Patterns

```python
# ❌ WRONG: bypasses dependency injection
def my_command() -> None:
    progress_file = Path.cwd() / ".impl" / "progress.md"

# ✅ CORRECT: uses injected path
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)
    progress_file = cwd / ".impl" / "progress.md"
```

## Testing Requirements

Every kit CLI command MUST have tests that use context injection:

```python
from click.testing import CliRunner
from erk_shared.context import ErkContext

def test_my_command(tmp_path: Path) -> None:
    """Test using context injection."""
    runner = CliRunner()
    result = runner.invoke(
        my_command,
        ["--json"],
        obj=ErkContext.for_test(cwd=tmp_path),
    )
    assert result.exit_code == 0
```

### Test Location

- Unit tests: `tests/unit/kits/kits/erk/`
- Integration tests: `tests/integration/kits/kits/erk/`

## See Also

- [Kit CLI Dependency Injection Patterns](/.erk/docs/agent/kits/dependency-injection.md)
- [fake-driven-testing skill](/.claude/skills/fake-driven-testing/)
