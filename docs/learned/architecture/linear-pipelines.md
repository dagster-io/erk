---
title: Linear Pipeline Architecture
read_when:
  - "designing multi-step operations with validation and execution phases"
  - "refactoring complex commands into functional pipelines"
  - "working with land command or similar staged workflows"
tripwires:
  - action: "creating a new complex command with multiple validation steps"
    warning: "Consider two-pipeline pattern: validation pipeline (check preconditions) + execution pipeline (perform operations). Use discriminated unions (State | Error) for pipeline steps. Reference land_pipeline.py as exemplar."
---

# Linear Pipeline Architecture

Complex workflows benefit from separating validation (check preconditions) from execution (perform operations). The land command demonstrates a two-pipeline pattern with functional composition and immutable state threading.

## Two-Pipeline Pattern

The land command uses two separate pipelines:

1. **Validation Pipeline** (5 steps) - Check preconditions, no mutations
2. **Execution Pipeline** (6 steps) - Perform operations that modify state

**Benefits**:

- Clear separation of read-only checks from mutations
- Can run validation without side effects
- Execution steps assume validation passed
- Each pipeline is independently testable

## Pipeline Step Signature

All steps follow the same signature:

```python
LandStep = Callable[[ErkContext, LandState], LandState | LandError]
```

**Input**: Takes context and current state
**Output**: Returns either updated state OR error (short-circuits pipeline)

This signature enables:

- Functional composition (steps chain together)
- Type-safe error propagation
- Consistent testing patterns

## Validation Pipeline (5 Steps)

**Purpose**: Check preconditions without mutating repository state

```python
def run_validation_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run all validation steps, short-circuit on first error."""
    for step in [
        resolve_target,
        validate_checks,
        check_no_conflicts,
        check_no_uncommitted_changes,
        check_branch_up_to_date,
    ]:
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result  # Short-circuit on error
        state = result  # Thread state to next step
    return state
```

**Key characteristics**:

- Read-only operations (no mutations)
- Fails fast on first error
- Returns enriched state with resolved values
- Cached with `@cache` decorator (idempotent)

## Execution Pipeline (6 Steps)

**Purpose**: Perform operations that modify repository state

```python
def run_execution_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run all execution steps, short-circuit on first error."""
    for step in [
        merge_pr_step,
        check_learn_status,
        update_learn_plan,
        promote_tripwires,
        close_review_pr,
        cleanup_branches,
    ]:
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result  # Short-circuit on error
        state = result  # Thread state to next step
    return state
```

**Key characteristics**:

- Mutating operations (modifies repository state)
- Assumes validation passed
- Steps may have dependencies on previous step results
- Cached with `@cache` decorator

## Shell Script Serialization Bridge

Between validation and execution pipelines, state is serialized to a shell script for exec-based execution:

```python
# After validation
validated_state = run_validation_pipeline(ctx, initial_state)

# Serialize to shell script for exec
script = generate_execution_script(validated_state)

# Exec the script (replaces current process)
os.execvp(script_path, [script_path])
```

**Why serialization?**

- Exec replaces the current process (can't pass Python objects)
- Shell script captures validated state as flags/arguments
- Enables resumability (script can be re-executed)

**State fields included in script**:

- PR number (resolved from branch or user input)
- Target branch name
- Skip flags (skip-objective, skip-update-main)
- Learn plan metadata (if applicable)

**State fields NOT included** (recomputed on exec):

- Repository paths (resolved from cwd on exec)
- PR details (fetched fresh from GitHub API)
- Conflict status (checked again before execution)

## Pipeline Runners with Caching

Both pipelines use `@cache` decorator for idempotency:

```python
@cache
def run_validation_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    ...

@cache
def run_execution_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    ...
```

**Benefits**:

- Multiple calls with same inputs return cached result
- Enables testing with multiple assertions without re-running
- Idempotent - same inputs always produce same output

**Caveat**: State objects must be immutable (frozen dataclasses) for caching to work correctly.

## State Factories

Two factory functions create initial state for each pipeline:

### make_initial_state()

Creates state for validation pipeline from CLI inputs:

```python
def make_initial_state(
    *,
    pr_number_or_branch: int | str | None,
    skip_objective_update: bool,
    skip_update_main: bool,
) -> LandState:
    """Create initial state from CLI arguments."""
    return LandState(
        pr_number_or_branch=pr_number_or_branch,
        skip_objective_update=skip_objective_update,
        skip_update_main=skip_update_main,
        # All other fields None - resolved in validation pipeline
    )
```

### make_execution_state()

Creates state for execution pipeline from validated state or shell script arguments:

```python
def make_execution_state(
    pr_number: int,
    target_branch: str,
    skip_objective_update: bool,
    skip_update_main: bool,
) -> LandState:
    """Create execution state from resolved values."""
    return LandState(
        pr_number=pr_number,
        target_branch=target_branch,
        skip_objective_update=skip_objective_update,
        skip_update_main=skip_update_main,
        # All resolution fields are set
        pr_number_or_branch=pr_number,  # Use resolved value
    )
```

## Static vs User-Controllable Flags

The pipeline distinguishes two types of configuration:

**Static flags** (computed from state, not user-controllable):

- `is_learn_plan` - Detected from PR labels/branch patterns
- `has_review_pr` - Checked via GitHub API
- `target_is_trunk` - Computed from target branch name

**User-controllable flags** (CLI options, preserved in exec script):

- `skip_objective_update` - User chose to skip objective handling
- `skip_update_main` - User chose to skip main branch update

**Why this matters**:

- Static flags are recomputed fresh on each run
- User-controllable flags are serialized to exec script
- Ensures consistent behavior across validation and execution

## Reference Implementation

**File**: `src/erk/cli/commands/workflows/land_pipeline.py` (706 lines, 20 functions)

**Structure**:

- Lines 1-49: Imports and type aliases
- Lines 50-79: LandState dataclass definition (~13 fields)
- Lines 82-89: LandError dataclass definition
- Lines 92-156: Validation pipeline and step functions
- Lines 159-224: Execution pipeline and step functions
- Lines 227-303: State factories and utilities
- Lines 306-706: Individual pipeline step implementations

**Test coverage**: `tests/commands/workflows/test_land_pipeline.py` (772 lines) with comprehensive unit tests for each pipeline step.

## Relationship to Two-Phase Validation Model

The linear pipeline architecture extends the [two-phase validation model](../cli/two-phase-validation-model.md):

- **Phase 1** (CLI layer): Parse arguments, construct initial state
- **Phase 2** (Validation pipeline): Validate preconditions, resolve values
- **Phase 3** (Execution pipeline): Perform mutations with validated state

The two pipelines compose Phase 2 (validation) and Phase 3 (execution) into clean functional sequences.

## Related Documentation

- [Land State Threading](land-state-threading.md) - Immutable state management with dataclasses.replace()
- [CLI-to-Pipeline Boundary](cli-to-pipeline-boundary.md) - Separating CLI concerns from business logic
- [Learn Plan Land Flow](../cli/learn-plan-land-flow.md) - Learn-plan-specific execution pipeline steps
- [Two-Phase Validation Model](../cli/two-phase-validation-model.md) - Foundation pattern
- [Pipeline Transformation Patterns](pipeline-transformation-patterns.md) - Functional pipeline composition
