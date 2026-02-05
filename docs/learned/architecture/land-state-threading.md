---
title: Land State Threading Pattern
read_when:
  - "implementing pipelines with immutable state"
  - "using dataclasses.replace() for state updates"
  - "designing stateful workflows with frozen dataclasses"
tripwires:
  - action: "threading state through pipeline steps with mutable dataclasses"
    warning: "Use frozen dataclasses (@dataclass(frozen=True)) for pipeline state. Update fields with dataclasses.replace() to create new instances. Immutability enables caching, testability, and replay."
last_audited: "2026-02-05 14:21 PT"
audit_result: edited
---

# Land State Threading Pattern

Pipeline steps thread immutable state through functional transformations. The land command demonstrates state threading with frozen dataclasses and `dataclasses.replace()`.

## Core Pattern: Frozen Dataclass State

See `LandState` in `src/erk/cli/commands/land_pipeline.py` (lines 50-79) for the reference implementation.

**Key characteristics**:

- `@dataclass(frozen=True)` -- immutable after creation
- Fields populate progressively through pipeline stages
- 21 fields organized into three groups: CLI inputs, resolved target (populated by `resolve_target`), and derived values (populated by later steps)
- Every step has the signature `(ErkContext, LandState) -> LandState | LandError`

## State Update with dataclasses.replace()

Pipeline steps create new state instances rather than mutating. See `resolve_target()` in `land_pipeline.py` for a concrete example -- it returns `dataclasses.replace(state, branch=..., pr_number=..., pr_details=..., ...)`.

**Benefits**:

- Original state unchanged (safe to replay)
- Type-safe updates (IDE autocomplete for field names)
- Compiler catches typos in field names
- Explicit about which fields change

## Field Lifecycle: CLI Inputs -> Resolution -> Execution

State fields populate in stages. See `make_initial_state()` and `make_execution_state()` in `land_pipeline.py` for how initial state is constructed.

### Stage 1: Initial State (from CLI)

Created by `make_initial_state()`. Only CLI flags and pre-discovered repo paths are set. Discovery fields like `branch`, `pr_number`, `pr_details` start as empty defaults (`""`, `0`, `None`).

### Stage 2: After resolve_target Step

Populates: `branch`, `pr_number`, `pr_details`, `worktree_path`, `is_current_branch`, `use_graphite`, `target_child_branch`.

### Stage 3: After validate_pr Step

Validates PR state (OPEN, base is trunk, no unresolved comments). Returns state unchanged on success.

### Stage 4: After check_learn_status and gather_confirmations Steps

Populates: `plan_issue_number`, `cleanup_confirmed`.

### Stage 5: After resolve_objective Step

Populates: `objective_number`. This completes the validation pipeline.

### Stage 6: Execution Pipeline

`merge_pr` populates `merged_pr_number`. Remaining steps (`update_objective`, `update_learn_plan`, `promote_tripwires`, `close_review_pr`, `cleanup_and_navigate`) perform side effects and return state unchanged.

## Progressive Population Pattern

Fields start as defaults, then populate as pipeline progresses:

| Field               | Stage      | Populated By Step      |
| ------------------- | ---------- | ---------------------- |
| `branch`            | Validation | `resolve_target`       |
| `pr_number`         | Validation | `resolve_target`       |
| `pr_details`        | Validation | `resolve_target`       |
| `worktree_path`     | Validation | `resolve_target`       |
| `is_current_branch` | Validation | `resolve_target`       |
| `use_graphite`      | Validation | `resolve_target`       |
| `plan_issue_number` | Validation | `check_learn_status`   |
| `cleanup_confirmed` | Validation | `gather_confirmations` |
| `objective_number`  | Validation | `resolve_objective`    |
| `merged_pr_number`  | Execution  | `merge_pr`             |

**Pattern**: CLI input fields are required (no defaults). Discovery/derived fields use sentinel defaults (`""`, `0`, `None`, `False`) and are populated by pipeline steps.

## Benefits of Immutability

### 1. Testability

Tests can assert on state at any pipeline stage. Each step is independently testable -- pass in a constructed `LandState`, call the step, assert on the returned state. The original state is never modified. See tests in `tests/unit/cli/commands/land/pipeline/` for examples.

### 2. Replay Capability

Same initial state + same context always produces same result. This is especially valuable for the two-pipeline architecture where validation runs in the CLI process and execution runs in a separate `erk exec land-execute` process.

### 3. Debugging

Can reconstruct exact state at any pipeline stage by logging state snapshots before and after each step.

## Type Narrowing After Validation

After the validation pipeline, certain fields are guaranteed populated (e.g., `pr_number`, `branch`, `pr_details`). However, Python's type system doesn't track field-level narrowing -- the types still show `int | None` etc.

**Caveat**: Use assertions or early returns in execution steps if fields must be non-None. See `gather_confirmations()` in `land_pipeline.py` for an example: `assert state.pr_details is not None`.

## Comparison to Mutable State

### Mutable Approach (DON'T)

```python
@dataclass
class LandState:  # NOT frozen
    pr_number: int | None = None

def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    state.pr_number = 123  # BAD: modifies caller's state
    return state
```

**Problems**: Caller's state is modified (unexpected side effect), can't replay, can't cache, hard to test.

### Immutable Approach (DO)

```python
@dataclass(frozen=True)
class LandState:
    pr_number: int | None = None

def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    return dataclasses.replace(state, pr_number=123)  # GOOD: immutable
```

**Benefits**: Input state unchanged, safe to replay, cacheable, easy to test.

## Reference Implementation

- **LandState definition**: `src/erk/cli/commands/land_pipeline.py` (lines 50-79)
- **Pipeline step definitions**: Same file, validation steps (lines 104-402) and execution steps (lines 410-555)
- **Pipeline runners**: `run_validation_pipeline()` and `run_execution_pipeline()` in the same file
- **State factories**: `make_initial_state()` and `make_execution_state()` in the same file
- **Tests**: `tests/unit/cli/commands/land/pipeline/`

## Related Documentation

- [Linear Pipelines](linear-pipelines.md) - Two-pipeline pattern with validation and execution
- [Pipeline Transformation Patterns](pipeline-transformation-patterns.md) - Functional composition
- [Erk Architecture Patterns](erk-architecture.md) - Immutable dataclass patterns
