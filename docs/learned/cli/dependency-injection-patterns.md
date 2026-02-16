---
title: Dependency Injection in Exec Scripts
read_when:
  - "writing erk exec scripts"
  - "testing exec scripts that use gateways"
  - "understanding exec script architecture"
  - "migrating exec scripts from subprocess to gateways"
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
tripwires:
  - action: "implementing business logic with gateways"
    warning: "Never create gateway instances in business logic — inject them as parameters"
  - action: "implementing internal CLI functions"
    warning: "Separate _*_impl() functions return exit codes or discriminated unions, never call sys.exit()"
  - action: "retrieving dependencies in Click commands"
    warning: "Click commands retrieve real implementations from context via require_* helpers"
---

# Dependency Injection in Exec Scripts

Exec scripts use Click's context injection to enable fast, subprocess-free testing. This separates CLI wiring from testable business logic.

## Why This Pattern Exists

**Problem**: Traditional exec scripts hardcode subprocess calls and instantiate gateways inline, making tests slow and requiring subprocess mocking.

**Solution**: Inject gateway dependencies through Click context, extract business logic to pure functions accepting ABC types.

**Benefits**:

- Tests call `_*_impl()` directly with fakes — no subprocess mocks, no slow processes
- Explicit dependencies in function signatures reveal what the command actually does
- Business logic functions are independently testable without CLI setup
- Single gateway implementation change fixes all exec scripts using it

## The Architecture

### Three-Layer Separation

1. **Click command** (CLI wiring) — retrieves real dependencies, handles CLI concerns
2. **Implementation function** (business logic) — pure function accepting gateway ABCs
3. **Gateway interfaces** (abstraction boundary) — ABC types enable fake substitution

### Critical Rule: No Gateway Instantiation in Business Logic

<!-- Source: src/erk/cli/commands/exec/scripts/ci_verify_autofix.py, _verify_autofix_impl() -->

Business logic functions accept gateway ABCs as keyword-only parameters. The Click command handles instantiation, passing real implementations from context. Tests pass fakes directly.

See `_verify_autofix_impl()` in `src/erk/cli/commands/exec/scripts/ci_verify_autofix.py` for the canonical example — it accepts `CIRunner` and `GitHub` ABCs as keyword-only parameters, never instantiating concrete implementations.

## Context Retrieval Pattern

<!-- Source: packages/erk-shared/src/erk_shared/context/helpers.py -->

Click commands use `require_*` helpers to extract typed dependencies from the Click context. The pattern: (1) extract dependencies via `require_*`, (2) instantiate any gateways not in context, (3) pass all dependencies to `_*_impl()`, (4) handle result.

See `packages/erk-shared/src/erk_shared/context/helpers.py` for all available `require_*` helpers.

## Test Pattern

<!-- Source: tests/unit/cli/commands/exec/scripts/test_ci_verify_autofix.py -->

Tests bypass Click entirely, calling `_*_impl()` directly with fakes. The test creates fakes with desired behavior (e.g., `FakeCIRunner.create_passing_all()`), calls the impl function directly, and asserts on both the result structure and gateway interactions.

See `tests/unit/cli/commands/exec/scripts/test_ci_verify_autofix.py` for complete test examples.

## Return Value Patterns

Implementation functions use two patterns depending on complexity:

### Exit Codes (Simple Scripts)

For scripts with binary success/failure:

```python
def _my_impl(*, git: Git, repo_root: Path) -> int:
    """Business logic returning exit code.

    Returns:
        0 on success, 1 on failure
    """
    if git.branch.branch_exists(repo_root, "main"):
        return 0
    return 1
```

### Discriminated Unions (Complex Scripts)

<!-- Source: src/erk/cli/commands/exec/scripts/detect_trunk_branch.py -->
<!-- Source: src/erk/cli/commands/exec/scripts/ci_verify_autofix.py -->

For scripts outputting structured data or detailed error information:

```python
@dataclass(frozen=True)
class SuccessResult:
    success: Literal[True]
    data: str

@dataclass(frozen=True)
class ErrorResult:
    success: Literal[False]
    error_type: Literal["not-found", "invalid"]
    message: str

def _my_impl(*, git: Git) -> SuccessResult | ErrorResult:
    """Business logic returning discriminated union."""
    # Return structured result
```

The Click command converts the discriminated union to JSON or appropriate exit code.

See `_detect_trunk_branch_impl()` in `src/erk/cli/commands/exec/scripts/detect_trunk_branch.py` and `_verify_autofix_impl()` in `src/erk/cli/commands/exec/scripts/ci_verify_autofix.py` for this pattern in production.

## Migration Checklist

When migrating an exec script from subprocess to gateway-based DI:

1. **Identify subprocess calls** — Find all `subprocess.run()` invocations
2. **Find or create gateway ABC** — Check if an appropriate gateway exists; create one if needed
3. **Extract business logic** — Move core logic to separate `_*_impl()` function
4. **Add gateway parameters** — Make all gateways keyword-only parameters with ABC types
5. **Wire Click command** — Use `require_*` helpers to extract context dependencies
6. **Pass real implementations** — Instantiate any gateways not in context, pass to `_*_impl()`
7. **Write tests with fakes** — Test business logic directly, passing gateway fakes
8. **Remove subprocess calls** — Replace with gateway method calls
9. **Verify subprocess-free** — Ensure no `subprocess` imports remain

## Common Anti-Patterns

### Mixing CLI Concerns with Business Logic

**WRONG**: Business logic scattered inside Click command:

```python
@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)
    result = subprocess.run(["pytest"], cwd=cwd)  # ❌ Untestable
    if result.returncode == 0:
        click.echo("Tests passed")
```

**CORRECT**: Extracted business logic with injected dependencies:

```python
def _my_command_impl(*, ci_runner: CIRunner, cwd: Path) -> int:
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=cwd)
    return 0 if result.passed else 1

@click.command()
@click.pass_context
def my_command(ctx: click.Context) -> None:
    cwd = require_cwd(ctx)
    ci_runner = RealCIRunner()
    exit_code = _my_command_impl(ci_runner=ci_runner, cwd=cwd)
    if exit_code == 0:
        click.echo("Tests passed")
    raise SystemExit(exit_code)
```

### Direct Subprocess in Business Logic

**WRONG**: Subprocess calls in business logic prevent fake injection:

```python
def _my_impl(*, console: Console) -> int:
    result = subprocess.run(["pytest"])  # ❌ Tests must mock subprocess
    return result.returncode
```

**CORRECT**: Gateway abstraction enables fake substitution:

```python
def _my_impl(*, ci_runner: CIRunner) -> int:
    result = ci_runner.run_check(name="pytest", cmd=["pytest"], cwd=Path.cwd())
    return 0 if result.passed else 1
```

## Related Documentation

- [Gateway Inventory](../architecture/gateway-inventory.md) — Available gateway ABCs
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — Creating new gateways
- [Fake-Driven Testing](../testing/fake-driven-testing.md) — Using gateway fakes in tests
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — Return value patterns
