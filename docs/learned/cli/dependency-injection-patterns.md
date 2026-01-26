---
title: Dependency Injection in Exec Scripts
read_when:
  - "writing erk exec scripts"
  - "testing exec scripts that use gateways"
  - "understanding exec script architecture"
  - "migrating exec scripts from subprocess to gateways"
---

# Dependency Injection in Exec Scripts

Exec scripts (commands under `src/erk/commands/exec/`) use dependency injection to enable testing without subprocess mocks. This document explains the pattern using real examples.

## The Pattern

### Script Structure

```python
# src/erk/commands/exec/my_command.py

def run_my_command(*, ci_runner: CIRunner, console: Console) -> int:
    """Pure business logic with injected dependencies."""
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=Path.cwd())

    if result.passed:
        console.success("Tests passed")
        return 0
    else:
        console.error("Tests failed")
        return 1


def main() -> int:
    """CLI entry point - creates real implementations."""
    from erk_shared.gateway.ci_runner.real import RealCIRunner
    from erk_shared.gateway.console.interactive import InteractiveConsole

    return run_my_command(
        ci_runner=RealCIRunner(),
        console=InteractiveConsole(),
    )


if __name__ == "__main__":
    sys.exit(main())
```

### Key Principles

1. **Business logic function** (`run_my_command`) accepts gateway ABC types
2. **CLI entry point** (`main`) creates real implementations
3. **No subprocess calls** in business logic - use gateways instead
4. **Return exit codes** (0 = success, non-zero = failure)

## Real Example: ci_verify_autofix.py

The `ci_verify_autofix.py` script demonstrates this pattern:

### Business Logic Function

```python
def run_ci_verify_autofix(
    *,
    ci_runner: CIRunner,
    console: Console,
    cwd: Path,
) -> int:
    """Run CI checks with auto-fix, return exit code."""

    # Run formatter
    result = ci_runner.run_check(
        name="prettier",
        cmd=["prettier", "--write", "."],
        cwd=cwd,
    )

    if not result.passed:
        if result.error_type == "command_not_found":
            console.error("prettier not found")
            return 127
        else:
            console.error("prettier failed")
            return 1

    # Run tests
    result = ci_runner.run_check(
        name="pytest",
        cmd=["pytest"],
        cwd=cwd,
    )

    if not result.passed:
        console.error("Tests failed")
        return 1

    console.success("All checks passed")
    return 0
```

### CLI Entry Point

```python
def main() -> int:
    from erk_shared.gateway.ci_runner.real import RealCIRunner
    from erk_shared.gateway.console.interactive import InteractiveConsole

    return run_ci_verify_autofix(
        ci_runner=RealCIRunner(),
        console=InteractiveConsole(),
        cwd=Path.cwd(),
    )
```

### Test Using Fakes

```python
def test_ci_verify_autofix_passes():
    """Test successful CI run."""
    fake_ci = FakeCIRunner.create_passing_all()
    fake_console = FakeConsole()

    exit_code = run_ci_verify_autofix(
        ci_runner=fake_ci,
        console=fake_console,
        cwd=Path("/fake/repo"),
    )

    assert exit_code == 0
    assert fake_ci.check_names_run == ["prettier", "pytest"]
    assert "All checks passed" in fake_console.success_messages


def test_ci_verify_autofix_fails_on_missing_tool():
    """Test missing command handling."""
    fake_ci = FakeCIRunner(
        failing_checks=None,
        missing_commands={"prettier"},
    )
    fake_console = FakeConsole()

    exit_code = run_ci_verify_autofix(
        ci_runner=fake_ci,
        console=fake_console,
        cwd=Path("/fake/repo"),
    )

    assert exit_code == 127  # Command not found
    assert "prettier not found" in fake_console.error_messages
```

## Benefits

### Testability

- **No subprocess mocks** - Use fakes that implement the same interface
- **Fast tests** - No actual process execution
- **Predictable** - Fakes return exactly what you configure

### Clarity

- **Explicit dependencies** - Function signature shows what it needs
- **Single responsibility** - Business logic separate from CLI wiring
- **Easy to reason about** - No hidden globals or subprocess side effects

### Maintainability

- **Gateway updates propagate** - Change interface, update all callers
- **Refactoring confidence** - Tests verify behavior without subprocess coupling
- **Clear boundaries** - CLI layer vs business logic layer

## Common Patterns

### Multiple Gateways

```python
def run_command(
    *,
    git: Git,
    github: GitHub,
    console: Console,
) -> int:
    branch = git.get_current_branch(Path.cwd())
    pr = github.get_pr_for_branch(repo_root, branch)
    console.info(f"PR: {pr.number}")
    return 0
```

### Optional Dependencies

```python
def run_command(
    *,
    ci_runner: CIRunner,
    console: Console,
    cwd: Path | None = None,
) -> int:
    if cwd is None:
        cwd = Path.cwd()

    # Use cwd
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=cwd)
    return 0 if result.passed else 1
```

### Gateway Factories

When a gateway needs complex setup:

```python
def main() -> int:
    from erk_shared.gateway.ci_runner.real import RealCIRunner
    from erk_shared.gateway.time.real import RealTime

    ci_runner = RealCIRunner(time=RealTime())  # CIRunner needs Time

    return run_command(ci_runner=ci_runner)
```

## Migration Checklist

When migrating an exec script from subprocess to gateways:

1. ✅ Identify subprocess calls to replace
2. ✅ Find or create gateway ABC for the capability
3. ✅ Extract business logic to separate function
4. ✅ Add gateway parameters to business logic function
5. ✅ Update `main()` to create real implementations
6. ✅ Write tests using fake implementations
7. ✅ Remove subprocess.run() calls
8. ✅ Verify tests pass without subprocess mocks

## Anti-Patterns

### Mixing CLI and Business Logic

❌ **Wrong:**

```python
def main() -> int:
    # Business logic mixed with CLI wiring
    result = subprocess.run(["pytest"])
    if result.returncode == 0:
        print("Tests passed")
    return result.returncode
```

✅ **Correct:**

```python
def run_command(*, ci_runner: CIRunner) -> int:
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=Path.cwd())
    return 0 if result.passed else 1

def main() -> int:
    return run_command(ci_runner=RealCIRunner())
```

### Creating Gateways in Business Logic

❌ **Wrong:**

```python
def run_command() -> int:
    ci_runner = RealCIRunner()  # Hardcoded in business logic
    result = ci_runner.run_check(...)
    return 0 if result.passed else 1
```

✅ **Correct:**

```python
def run_command(*, ci_runner: CIRunner) -> int:  # Injected
    result = ci_runner.run_check(...)
    return 0 if result.passed else 1
```

### Using Subprocess Directly

❌ **Wrong:**

```python
def run_command(*, console: Console) -> int:
    result = subprocess.run(["pytest"])  # Direct subprocess
    return result.returncode
```

✅ **Correct:**

```python
def run_command(*, ci_runner: CIRunner, console: Console) -> int:
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=Path.cwd())
    return 0 if result.passed else 1
```

## Related Documentation

- [Gateway Inventory](../architecture/gateway-inventory.md) - Available gateways
- [Subprocess Testing](../testing/subprocess-testing.md) - Testing patterns
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - Creating new gateways
