---
title: Dependency Injection in Exec Scripts
read_when:
  - "writing erk exec scripts"
  - "testing exec scripts that use gateways"
  - "understanding exec script architecture"
  - "migrating exec scripts from subprocess to gateways"
last_audited: "2026-02-05"
audit_result: edited
---

# Dependency Injection in Exec Scripts

Exec scripts (commands under `src/erk/commands/exec/`) use dependency injection to enable testing without subprocess mocks.

## The Pattern

Exec scripts use **Click context injection** — not standalone `main()` functions:

1. A `@click.command` entry point uses `@click.pass_context` to receive the Click context
2. Gateway dependencies are retrieved via `require_*` helpers from `erk_shared.context.helpers`
3. Business logic is extracted to a separate `_*_impl()` function that accepts gateway ABC types
4. Tests call the `_*_impl()` function directly, passing fakes

### Key Principles

1. **Business logic function** (`_*_impl`) accepts gateway ABC types as keyword-only args
2. **Click command** retrieves real implementations from context
3. **No subprocess calls** in business logic — use gateways instead
4. **Return exit codes** (0 = success, non-zero = failure)

### Reference Examples

- **Script**: `src/erk/commands/exec/ci_verify_autofix.py` — `_verify_autofix_impl()` takes `ci_runner`, `console`, `github`, etc.
- **Tests**: `tests/unit/commands/exec/test_ci_verify_autofix.py` — tests call `_verify_autofix_impl()` with fakes

## Benefits

- **No subprocess mocks** — Use fakes that implement the same interface
- **Fast tests** — No actual process execution
- **Explicit dependencies** — Function signature shows what it needs
- **Single responsibility** — Business logic separate from CLI wiring

## Migration Checklist

When migrating an exec script from subprocess to gateways:

1. Identify subprocess calls to replace
2. Find or create gateway ABC for the capability
3. Extract business logic to separate `_*_impl()` function
4. Add gateway parameters as keyword-only args to the impl function
5. Wire up Click command to pass real implementations from context
6. Write tests using fake implementations
7. Remove `subprocess.run()` calls
8. Verify tests pass without subprocess mocks

## Anti-Patterns

### Mixing CLI and Business Logic

```python
# WRONG: Business logic mixed with CLI wiring
@click.command()
def my_command() -> None:
    result = subprocess.run(["pytest"])
    if result.returncode == 0:
        print("Tests passed")

# CORRECT: Separate impl function with injected dependencies
def _my_command_impl(*, ci_runner: CIRunner) -> int:
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=Path.cwd())
    return 0 if result.passed else 1
```

### Creating Gateways in Business Logic

```python
# WRONG: Hardcoded in business logic
def _my_impl() -> int:
    ci_runner = RealCIRunner()
    result = ci_runner.run_check(...)
    return 0 if result.passed else 1

# CORRECT: Injected
def _my_impl(*, ci_runner: CIRunner) -> int:
    result = ci_runner.run_check(...)
    return 0 if result.passed else 1
```

### Using Subprocess Directly

```python
# WRONG: Direct subprocess
def _my_impl(*, console: Console) -> int:
    result = subprocess.run(["pytest"])
    return result.returncode

# CORRECT: Use gateway
def _my_impl(*, ci_runner: CIRunner, console: Console) -> int:
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=Path.cwd())
    return 0 if result.passed else 1
```

## Related Documentation

- [Gateway Inventory](../architecture/gateway-inventory.md) — Available gateways
- [Subprocess Testing](../testing/subprocess-testing.md) — Testing patterns
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — Creating new gateways
