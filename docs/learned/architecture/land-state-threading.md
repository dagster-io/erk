---
title: Land State Threading Pattern
read_when:
  - "implementing pipelines with immutable state"
  - "using dataclasses.replace() for state updates"
  - "designing stateful workflows with frozen dataclasses"
tripwires:
  - action: "threading state through pipeline steps with mutable dataclasses"
    warning: "Use frozen dataclasses (@dataclass(frozen=True)) for pipeline state. Update fields with dataclasses.replace() to create new instances. Immutability enables caching, testability, and replay."
---

# Land State Threading Pattern

Pipeline steps thread immutable state through functional transformations. The land command demonstrates state threading with frozen dataclasses and `dataclasses.replace()`.

## Core Pattern: Frozen Dataclass State

State is represented as a frozen dataclass:

```python
@dataclass(frozen=True)
class LandState:
    """Immutable state threaded through land pipeline."""
    # CLI inputs (user-controllable)
    pr_number_or_branch: int | str | None
    skip_objective_update: bool
    skip_update_main: bool

    # Resolved values (populated during validation)
    pr_number: int | None = None
    pr_details: PRDetails | None = None
    target_branch: str | None = None
    repo_root: Path | None = None

    # Derived flags (computed from resolved values)
    is_learn_plan: bool = False
    has_review_pr: bool = False
    target_is_trunk: bool = False

    # Learn plan metadata (populated if is_learn_plan)
    learn_issue_number: int | None = None
    learn_tripwire_files: list[Path] | None = None
```

**Key characteristics**:

- `frozen=True` - Immutable after creation
- Fields populate progressively through pipeline stages
- ~13 fields tracking validation → resolution → execution flow

## State Update with dataclasses.replace()

Pipeline steps create new state instances:

```python
def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Resolve PR number and target branch from input."""
    # Validation logic...
    pr_number = ...
    pr_details = ...
    target_branch = pr_details.base_branch

    # Create new state with updated fields
    return dataclasses.replace(
        state,
        pr_number=pr_number,
        pr_details=pr_details,
        target_branch=target_branch,
    )
```

**Benefits**:

- Original state unchanged (safe to replay)
- Type-safe updates (IDE autocomplete for field names)
- Compiler catches typos in field names
- Explicit about which fields change

## Field Lifecycle: CLI Inputs → Resolution → Validation → Execution

State fields populate in stages:

### Stage 1: Initial State (from CLI)

```python
state = LandState(
    pr_number_or_branch=None,  # User didn't specify PR
    skip_objective_update=False,
    skip_update_main=False,
)
```

Fields: Only CLI inputs set

### Stage 2: After resolve_target Step

```python
state = dataclasses.replace(
    state,
    pr_number=123,
    pr_details=PRDetails(...),
    target_branch="main",
)
```

Fields: CLI inputs + resolved PR info

### Stage 3: After validate_checks Step

```python
state = dataclasses.replace(
    state,
    is_learn_plan=True,  # Detected from PR labels
    has_review_pr=False,
)
```

Fields: CLI inputs + resolved PR + derived flags

### Stage 4: After check_learn_status Step (Execution Pipeline)

```python
state = dataclasses.replace(
    state,
    learn_issue_number=456,
    learn_tripwire_files=[Path("docs/learned/architecture/tripwires.md")],
)
```

Fields: All validation fields + learn metadata

## Benefits of Immutability

### 1. Testability

Tests can assert on state at any pipeline stage:

```python
def test_resolve_target_updates_pr_number() -> None:
    """resolve_target should populate pr_number field."""
    initial_state = make_initial_state(pr_number_or_branch="feature-branch")
    ctx = create_test_context(...)

    result = resolve_target(ctx, initial_state)

    assert isinstance(result, LandState)  # Not an error
    assert result.pr_number == 123
    assert result.pr_details is not None
    # Original state unchanged
    assert initial_state.pr_number is None
```

### 2. Replay Capability

Same initial state + same context always produces same result:

```python
state = make_initial_state(pr_number_or_branch=123)

# Run validation twice with same inputs
result1 = run_validation_pipeline(ctx, state)
result2 = run_validation_pipeline(ctx, state)

# Results are identical (cached)
assert result1 is result2
```

### 3. Debugging

Can reconstruct exact state at any pipeline stage by logging state snapshots:

```python
def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    logger.debug(f"resolve_target: input state = {state}")
    # ... logic ...
    new_state = dataclasses.replace(state, pr_number=pr_number)
    logger.debug(f"resolve_target: output state = {new_state}")
    return new_state
```

## Progressive Population Pattern

Fields start as `None`, then populate as pipeline progresses:

| Field                   | Stage      | Populated By Step    |
| ----------------------- | ---------- | -------------------- |
| `pr_number`             | Validation | `resolve_target`     |
| `pr_details`            | Validation | `resolve_target`     |
| `target_branch`         | Validation | `resolve_target`     |
| `is_learn_plan`         | Validation | `validate_checks`    |
| `learn_issue_number`    | Execution  | `check_learn_status` |
| `learn_tripwire_files   | Execution  | `update_learn_plan`  |
| `skip_objective_update` | Initial    | CLI argument         |
| `skip_update_main`      | Initial    | CLI argument         |

**Pattern**: Required fields have no default; optional fields default to `None` or `False`.

## Type Narrowing After Validation

After validation pipeline, certain fields are guaranteed non-None:

```python
# After validation
validated_state = run_validation_pipeline(ctx, initial_state)
if isinstance(validated_state, LandError):
    handle_error(validated_state)
    return

# Type narrowing: validated_state is LandState (not error)
# However, fields like pr_number could still be None at runtime
# (validation doesn't populate all fields)

# Execution pipeline can assume validated fields are non-None
assert validated_state.pr_number is not None
assert validated_state.target_branch is not None
```

**Caveat**: Python's type system doesn't track field-level narrowing. Use assertions or early returns in execution steps if fields must be non-None.

## Comparison to Mutable State

### Mutable Approach (DON'T)

```python
@dataclass
class LandState:  # NOT frozen
    pr_number: int | None = None

def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    # Mutates input state
    state.pr_number = 123  # BAD: modifies caller's state
    return state
```

**Problems**:

- Caller's state is modified (unexpected side effect)
- Can't replay - state changes after first run
- Can't cache - same input produces different results
- Hard to test - need to reset state between tests

### Immutable Approach (DO)

```python
@dataclass(frozen=True)
class LandState:
    pr_number: int | None = None

def resolve_target(ctx: ErkContext, state: LandState) -> LandState | LandError:
    # Creates new state, input unchanged
    return dataclasses.replace(state, pr_number=123)  # GOOD: immutable
```

**Benefits**:

- Input state unchanged
- Safe to replay with same input
- Cacheable with `@cache` decorator
- Easy to test - no state cleanup needed

## Reference Implementation

**File**: `src/erk/cli/commands/workflows/land_pipeline.py:50-79`

**LandState Definition**:

```python
@dataclass(frozen=True)
class LandState:
    """State threaded through land pipeline."""
    # ~13 fields with clear lifecycle
    # See lines 50-79 for complete definition
```

**Usage in Pipeline Steps**: Every step function signature:

```python
def step_name(ctx: ErkContext, state: LandState) -> LandState | LandError:
    # Validation logic
    if error_condition:
        return LandError(...)

    # State update (immutable)
    return dataclasses.replace(state, new_field=value)
```

## Related Documentation

- [Linear Pipelines](linear-pipelines.md) - Two-pipeline pattern with validation and execution
- [Pipeline Transformation Patterns](pipeline-transformation-patterns.md) - Functional composition
- [Erk Architecture Patterns](erk-architecture.md) - Immutable dataclass patterns
