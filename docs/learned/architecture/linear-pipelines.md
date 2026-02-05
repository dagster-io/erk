---
title: Linear Pipeline Architecture
read_when:
  - "designing multi-step operations with validation and execution phases"
  - "refactoring complex commands into functional pipelines"
  - "working with land command or similar staged workflows"
tripwires:
  - action: "creating a new complex command with multiple validation steps"
    warning: "Consider two-pipeline pattern: validation pipeline (check preconditions) + execution pipeline (perform operations). Use discriminated unions (State | Error) for pipeline steps. Reference land_pipeline.py as exemplar."
last_audited: "2026-02-05 14:22 PT"
audit_result: edited
---

# Linear Pipeline Architecture

Complex workflows benefit from separating validation (check preconditions) from execution (perform operations). The land command demonstrates a two-pipeline pattern with functional composition and immutable state threading.

## Two-Pipeline Pattern

The land command uses two separate pipelines:

1. **Validation Pipeline** (5 steps) - Check preconditions, gather confirmations, resolve values
2. **Execution Pipeline** (6 steps) - Perform operations that modify state

**Benefits**:

- Clear separation of read-only checks from mutations
- Can run validation without side effects
- Execution steps assume validation passed
- Each pipeline is independently testable

## Pipeline Step Signature

All steps follow the same signature (see `LandStep` type alias in `land_pipeline.py`):

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

**Purpose**: Check preconditions, resolve targets, gather user confirmations before any mutations.

The validation steps are: `resolve_target`, `validate_pr`, `check_learn_status`, `gather_confirmations`, `resolve_objective`. See `_validation_pipeline()` in `src/erk/cli/commands/land_pipeline.py` for the authoritative step list.

The runner iterates the steps, threading state through each one and short-circuiting on the first `LandError`. See `run_validation_pipeline()` for the runner implementation.

**Key characteristics**:

- Read-only operations (no mutations)
- Fails fast on first error
- Returns enriched state with resolved values

## Execution Pipeline (6 Steps)

**Purpose**: Perform operations that modify repository state

The execution steps are: `merge_pr`, `update_objective`, `update_learn_plan`, `promote_tripwires`, `close_review_pr`, `cleanup_and_navigate`. See `_execution_pipeline()` in `src/erk/cli/commands/land_pipeline.py` for the authoritative step list.

The runner uses the same iterate-and-short-circuit pattern as validation. See `run_execution_pipeline()`.

**Key characteristics**:

- Mutating operations (modifies repository state)
- Assumes validation passed
- Steps may have dependencies on previous step results

## Shell Script Serialization Bridge

Between validation and execution pipelines, state is serialized to a shell script. The validation pipeline runs in `erk land` (the CLI command), and the execution pipeline runs in `erk exec land-execute` (a separate Click command invoked by the shell script).

**How it works**: After validation passes, `render_land_execution_script()` in `land_cmd.py` generates a shell script that calls `erk exec land-execute` with the validated state encoded as CLI flags. The user sources this script, which invokes the execution pipeline.

**Why serialization?**

- The shell script boundary separates the "approve" step (user sources script) from the "execute" step
- Shell script captures validated state as flags/arguments to `erk exec land-execute`
- Enables resumability (script can be re-executed)

**State fields baked into script** (static, determined at script generation time):

- PR number and branch name (passed as positional args)
- Worktree path, is-current-branch, objective number, use-graphite (baked as flags)

**State fields passed via `"$@"`** (user-controllable):

- `--up`, `--no-pull`, `--no-delete`, `-f` flags

**State fields recomputed on exec**:

- Repository paths (resolved from cwd via `discover_repo_context`)
- PR details (re-fetched by `merge_pr` if needed)
- Plan issue number (re-derived from branch name)

## Pipeline Step Lists with Caching

The step-list builder functions use `@cache` for idempotency:

```python
@cache
def _validation_pipeline() -> tuple[LandStep, ...]:
    return (resolve_target, validate_pr, check_learn_status, ...)

@cache
def _execution_pipeline() -> tuple[LandStep, ...]:
    return (merge_pr, update_objective, update_learn_plan, ...)
```

Note: `@cache` is on the step-list builders (`_validation_pipeline`, `_execution_pipeline`), not on the runner functions themselves. The runners (`run_validation_pipeline`, `run_execution_pipeline`) are not cached.

**Caveat**: State objects must be immutable (frozen dataclasses) for the pipeline pattern to work correctly.

## State Factories

Two factory functions create initial state for each pipeline. See `make_initial_state()` and `make_execution_state()` in `src/erk/cli/commands/land_pipeline.py` for their full signatures.

**`make_initial_state()`**: Creates state for the validation pipeline from CLI inputs. Takes ~10 keyword params including `cwd`, `force`, `script`, `pull_flag`, `no_delete`, `up_flag`, `dry_run`, `target_arg`, `repo_root`, `main_repo_root`. Discovery fields (branch, PR details, etc.) start as defaults and are populated by `resolve_target()`.

**`make_execution_state()`**: Creates state for the execution pipeline from exec script arguments. Takes ~11 keyword params. Re-derives `plan_issue_number` from the branch name. Sets `force=True` (execute mode always skips confirmations) and `dry_run=False`.

## Baked-in vs User-Controllable Flags

The exec script serialization boundary distinguishes two types of state:

**Baked-in flags** (determined at script generation time, not changeable by user):

- `worktree_path` - resolved worktree location
- `is_current_branch` - whether landing from that worktree
- `objective_number` - linked objective issue number
- `use_graphite` - whether Graphite merge is used

**User-controllable flags** (passed through `"$@"`, can be changed when sourcing script):

- `--up` - navigate upstack (child branch resolved at execution time)
- `--no-pull` - skip pull after landing
- `--no-delete` - preserve branch/slot
- `-f` - force flag (execute mode is already non-interactive)

**Why this matters**:

- Baked-in flags capture validated state that shouldn't change
- User-controllable flags allow last-minute adjustment
- Some values (repo paths, PR details) are intentionally recomputed fresh on exec

## Reference Implementation

**File**: `src/erk/cli/commands/land_pipeline.py`

See `LandState` (frozen dataclass, ~21 fields) and `LandError` (frozen dataclass) for the data types. The file contains the pipeline step definitions, runners, and state factories.

**Test coverage**: Tests are split across `tests/unit/cli/commands/land/pipeline/` with separate files for `test_resolve_target.py`, `test_validate_pr.py`, `test_merge_pr.py`, `test_run_validation_pipeline.py`, and `test_run_execution_pipeline.py`.

## Relationship to Two-Phase Validation Model

The linear pipeline architecture extends the [two-phase validation model](../cli/two-phase-validation-model.md):

- **Phase 1** (CLI layer): Parse arguments, construct initial state
- **Phase 2** (Validation pipeline): Validate preconditions, resolve values, gather confirmations
- **Phase 3** (Execution pipeline): Perform mutations with validated state

The two pipelines compose Phase 2 (validation) and Phase 3 (execution) into clean functional sequences.

## Related Documentation

- [Land State Threading](land-state-threading.md) - Immutable state management with dataclasses.replace()
- [CLI-to-Pipeline Boundary](cli-to-pipeline-boundary.md) - Separating CLI concerns from business logic
- [Learn Plan Land Flow](../cli/learn-plan-land-flow.md) - Learn-plan-specific execution pipeline steps
- [Two-Phase Validation Model](../cli/two-phase-validation-model.md) - Foundation pattern
- [Pipeline Transformation Patterns](pipeline-transformation-patterns.md) - Functional pipeline composition
