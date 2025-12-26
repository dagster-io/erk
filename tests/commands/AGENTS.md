# CLI Command Testing Patterns

## Overview

All CLI command tests use dependency injection via ErkContext with fake implementations. Tests use Click's `CliRunner` to simulate command execution without actual filesystem or git operations.

## Subdirectory Organization

| Directory     | Focus                    | When to Load                           |
| ------------- | ------------------------ | -------------------------------------- |
| `workspace/`  | create, rename, rm, move | Workspace manipulation commands        |
| `navigation/` | switch, up, down         | Branch navigation commands             |
| `display/`    | status, tree, list       | Information display commands           |
| `shell/`      | Shell integration        | Shell wrapper generation and utilities |
| `management/` | plan                     | Workspace planning commands            |
| `setup/`      | init, config, completion | Initial configuration commands         |

## Standard Test Pattern

```python
from click.testing import CliRunner
from erk.commands.create import create
from erk.context import ErkContext
from tests.fakes.fake_git import FakeGit

def test_command_behavior() -> None:
    # Arrange: Set up fakes with desired state
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature"]
    )

    ctx = ErkContext(
        git=git,
        # ... other dependencies
    )

    runner = CliRunner()

    # Act: Execute command
    result = runner.invoke(
        create,
        ["new-branch"],
        obj=ctx
    )

    # Assert: Verify behavior
    assert result.exit_code == 0
    assert "Created workspace" in result.output
    assert "new-branch" in git.created_branches
```

## Context Construction

🔴 **CRITICAL: Use `env.build_context()` helper instead of manual construction**

The `erk_isolated_fs_env()` context manager provides an `env.build_context()` helper method that eliminates boilerplate when constructing `ErkContext` for tests.

### Anti-Pattern (DO NOT USE)

```python
# ❌ WRONG - Manual GlobalConfig construction with 5+ parameters
from erk.core.config_store import GlobalConfig
from erk.core.context import ErkContext

git = FakeGit(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
)

global_config = GlobalConfig(
    erks_root=env.erks_root,
    use_graphite=False,
    shell_setup_complete=False,
    show_pr_info=True,
    show_pr_checks=False,
)

test_ctx = context_for_test(
    git=git,
    global_config=global_config,
    script_writer=env.script_writer,
    cwd=env.cwd,
)
```

### Correct Pattern (USE THIS)

```python
# ✅ CORRECT - Use env.build_context() helper
git = FakeGit(
    git_common_dirs={env.cwd: env.git_dir},
    default_branches={env.cwd: "main"},
)

test_ctx = env.build_context(git=git)
```

### When to Override Defaults

The `env.build_context()` method accepts optional parameters to customize the context:

```python
# Override specific integration implementations
test_ctx = env.build_context(
    git=custom_git,
    graphite=custom_graphite,
    github=FakeGitHub(),
)

# Enable Graphite integration
test_ctx = env.build_context(
    use_graphite=True,
    show_pr_checks=True,
)

# Combine custom gateways with config flags
test_ctx = env.build_context(
    git=git,
    graphite=graphite,
    use_graphite=True,
    dry_run=False,
)
```

### Available Parameters

- `git`: Custom Git implementation (defaults to FakeGit)
- `graphite`: Custom Graphite implementation (defaults to FakeGraphite)
- `github`: Custom GitHub implementation (defaults to FakeGitHub)
- `shell`: Custom Shell implementation
- `script_writer`: Custom ScriptWriter implementation
- `use_graphite`: Enable Graphite integration (default: False)
- `show_pr_info`: Show PR information (default: True)
- `show_pr_checks`: Show PR checks (default: False)
- `dry_run`: Enable dry-run mode (default: False)
- `cwd`: Override current working directory (default: env.cwd)

### Why This Matters

Using `env.build_context()`:

1. **Reduces boilerplate**: Eliminates 10-15 lines of manual construction
2. **Prevents errors**: Automatically handles parameter wiring
3. **Improves maintainability**: Changes to GlobalConfig don't break every test
4. **Standardizes patterns**: All tests use consistent context construction

## Common Assertions

### Exit Codes

```python
# Success
assert result.exit_code == 0

# User error (validation, missing args)
assert result.exit_code == 2

# Runtime error (git failure, filesystem issue)
assert result.exit_code == 1
```

### Output Verification

```python
# Check for expected messages
assert "Success message" in result.output
assert "Expected value" in result.output

# Check error messages
assert result.exit_code != 0
assert "Error: Expected error" in result.output
```

### State Changes

```python
# Verify mutations via fake's read-only properties
assert "branch-name" in git.created_branches
assert "old-name" in git.deleted_branches
assert git.rename_history == [("old", "new")]
```

## Testing CLI Options

### Boolean Flags

```python
result = runner.invoke(command, ["--force", "arg"])
```

### Options with Values

```python
result = runner.invoke(command, ["--option", "value", "arg"])
```

### Multiple Arguments

```python
result = runner.invoke(command, ["arg1", "arg2"])
```

## Error Handling Tests

```python
def test_command_with_invalid_input() -> None:
    # Arrange: Set up state that will cause validation error
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "existing-branch"]
    )

    ctx = ErkContext(git=git)
    runner = CliRunner()

    # Act: Try to create duplicate branch
    result = runner.invoke(create, ["existing-branch"], obj=ctx)

    # Assert: Verify error handling
    assert result.exit_code != 0
    assert "already exists" in result.output
```

## Subprocess Interaction

Commands that use `subprocess.run` should inject `FakeShell`:

```python
from tests.fakes.fake_shell import FakeShell

shell = FakeShell()
shell.add_command_result(
    "git status",
    returncode=0,
    stdout="clean working tree"
)

ctx = ErkContext(shell=shell)
```

## Test File Organization

**Command tests use plain functions, not test classes.** Test classes should only be used when testing a class or dataclass itself.

**Pattern for command tests (most common):**

```python
# ✅ CORRECT: Plain functions testing CLI commands
def test_create_workspace() -> None:
    # Test implementation using CliRunner
    pass

def test_create_workspace_with_force() -> None:
    # Test implementation
    pass

def test_create_workspace_fails_with_duplicate() -> None:
    # Test implementation
    pass
```

**Single-file pattern:** Most command tests stay in single files since each command typically has a focused set of test cases.

**Only split when:** A command has extensive test coverage (10+ tests) AND splitting creates files with 3+ tests each.

**See [.erk/docs/agent/testing.md#test-organization-principles](../../.erk/docs/agent/testing.md#test-organization-principles) for detailed guidance.**

## See Also

- [../../docs/TESTING.md#unit-test-pattern](../../docs/TESTING.md#unit-test-pattern)
- [../CLAUDE.md](../CLAUDE.md) - Overview of test structure
- [../fakes/](../fakes/) - Available fake implementations
