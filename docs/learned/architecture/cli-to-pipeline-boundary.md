---
title: CLI-to-Pipeline Boundary Pattern
read_when:
  - "refactoring complex CLI commands"
  - "separating business logic from Click layer"
  - "deciding when to extract pipeline from CLI command"
tripwires:
  - action: "writing complex business logic directly in Click command functions"
    warning: "Extract to pipeline layer when command has >3 distinct steps or complex state management. CLI layer should handle: Click decorators, parameter parsing, output formatting. Pipeline layer should handle: business logic, state management, error types."
---

# CLI-to-Pipeline Boundary Pattern

Complex CLI commands benefit from clear separation between Click layer (UI concerns) and pipeline layer (business logic). The land command refactoring demonstrates when and how to extract pipelines.

## Two-Layer Architecture

### CLI Layer (`land_cmd.py`)

**Responsibilities**:

- Click decorators (`@click.command`, `@click.option`)
- Parameter parsing and validation (Click level)
- Output formatting (success messages, error display)
- Context creation and dependency injection
- Calling pipeline layer functions

**File size**: 1,707 lines (includes command variants, helpers, output formatting)

**Key characteristic**: No business logic - delegates to pipeline layer

### Pipeline Layer (`land_pipeline.py`)

**Responsibilities**:

- Business logic (validation, execution steps)
- State management (LandState dataclass)
- Error types (LandError with structured fields)
- Discriminated union return types
- Functional composition of steps

**File size**: 706 lines (pure business logic, 20 functions)

**Key characteristic**: No Click imports - framework-agnostic

## Decision Threshold: When to Extract Pipeline

Extract pipeline layer when command meets ANY of these criteria:

### 1. Complexity Indicators

- **>3 distinct steps** that could fail independently
- **Complex state management** (>5 fields tracking progress)
- **Multiple error types** that need structured handling
- **Validation + execution phases** that should be separate

### 2. Testability Indicators

- **Hard to test** without invoking full CLI
- **Integration tests dominate** (no unit tests for business logic)
- **Slow test suite** due to subprocess/API calls in every test

### 3. Reusability Indicators

- **Logic needed outside CLI** (exec scripts, TUI, API)
- **Multiple entry points** (interactive mode, script mode)
- **Different output formats** (JSON, human-readable, TUI)

## Land Command as Reference

Before refactoring:

- **Single file**: `land_cmd.py` (~1200 lines) mixing Click and business logic
- **Hard to test**: Required invoking Click runner
- **Unclear error boundaries**: Exceptions mixed with return codes

After refactoring (PR #6333):

- **CLI layer**: `land_cmd.py` (1,707 lines) - Click decorators, output, context creation
- **Pipeline layer**: `land_pipeline.py` (706 lines) - validation/execution pipelines
- **Clear boundaries**: CLI handles UI, pipeline handles logic
- **Testable**: 772 lines of pipeline unit tests (no Click runner needed)

## Benefits of Separation

### 1. Independent Testability

**CLI layer tests** (integration-style):

```python
def test_land_command_with_pr_number(cli_runner) -> None:
    """Test land command with explicit PR number."""
    result = cli_runner.invoke(land, ["--pr", "123"])
    assert result.exit_code == 0
    assert "Landed PR #123" in result.output
```

**Pipeline layer tests** (unit-style):

```python
def test_resolve_target_with_pr_number() -> None:
    """resolve_target should populate pr_number from input."""
    state = make_initial_state(pr_number_or_branch=123)
    ctx = create_test_context(...)

    result = resolve_target(ctx, state)

    assert isinstance(result, LandState)
    assert result.pr_number == 123
```

### 2. Clear Error Boundaries

**CLI layer** - Handles display:

```python
@click.command()
def land(...) -> None:
    result = run_validation_pipeline(ctx, state)
    if isinstance(result, LandError):
        click.echo(f"Error: {result.message}", err=True)
        raise SystemExit(1)
    # Continue with execution...
```

**Pipeline layer** - Returns structured errors:

```python
def validate_checks(ctx: ErkContext, state: LandState) -> LandState | LandError:
    if not checks_passing:
        return LandError(
            phase="validation",
            error_type="pr-checks-failing",
            message="PR has failing checks",
            details={"pr_number": state.pr_number},
        )
    return state
```

### 3. Reusable Logic

Pipeline layer is framework-agnostic:

```python
# CLI usage
result = run_validation_pipeline(ctx, state)

# Exec script usage (no Click)
result = run_validation_pipeline(ctx, state)

# TUI usage (future)
result = run_validation_pipeline(ctx, state)
```

## Boundary Interface Pattern

### CLI → Pipeline: State Objects

CLI constructs initial state from Click parameters:

```python
@click.command()
@click.option("--pr", type=int)
@click.option("--skip-objective", is_flag=True)
def land(pr: int | None, skip_objective: bool) -> None:
    # Construct initial state from CLI params
    state = make_initial_state(
        pr_number_or_branch=pr,
        skip_objective_update=skip_objective,
        skip_update_main=False,
    )

    # Call pipeline with state
    result = run_validation_pipeline(ctx, state)
```

### Pipeline → CLI: Discriminated Unions

Pipeline returns typed results:

```python
# Pipeline returns LandState | LandError
result = run_validation_pipeline(ctx, state)

# CLI checks type and formats output
if isinstance(result, LandError):
    click.echo(f"Validation failed: {result.message}", err=True)
    if result.details:
        click.echo(f"Details: {result.details}")
    raise SystemExit(1)

# Type narrowing: result is LandState
click.echo(f"Validation passed for PR #{result.pr_number}")
```

## When NOT to Extract Pipeline

Simple commands don't benefit from pipeline extraction:

### Keep CLI Layer Only If

- **≤3 steps** with no complex state
- **Single error type** (just success/failure)
- **No reusability** needed outside CLI
- **Fast tests** possible with Click runner

**Example**: `erk status` command (simple status display)

```python
@click.command()
def status() -> None:
    worktrees = ctx.git_worktree.list_worktrees(repo_root)
    for wt in worktrees:
        click.echo(f"{wt.branch}: {wt.path}")
```

No pipeline needed - logic is trivial.

## Periodic Audit Recommendation

Commands accumulate complexity over time. Audit commands annually for extraction opportunities:

1. **Identify complex commands** (>500 lines, >3 steps)
2. **Check test coverage** (integration-only vs unit+integration)
3. **Assess reusability** (needed outside CLI?)
4. **Batch extraction** in dedicated refactoring PRs

## Reference Implementations

### Land Command

- **CLI**: `src/erk/cli/commands/workflows/land_cmd.py` (1,707 lines)
- **Pipeline**: `src/erk/cli/commands/workflows/land_pipeline.py` (706 lines)
- **Tests**: `tests/commands/workflows/test_land_pipeline.py` (772 lines)
- **PR**: #6333 - Refactor land command to function pipeline

### Commands Still Needing Extraction

Commands that could benefit from pipeline extraction (based on complexity):

- `erk plan implement` - Multiple phases (setup, execute, commit)
- `erk pr address` - Complex state (review threads, feedback classification)
- `erk stack sync` - Multi-step rebase workflow

## Related Documentation

- [Linear Pipelines](linear-pipelines.md) - Two-pipeline pattern architecture
- [Land State Threading](land-state-threading.md) - Immutable state management
- [Two-Phase Validation Model](../cli/two-phase-validation-model.md) - Foundation pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Error type design
