---
title: State Threading Pattern
read_when:
  - "designing linear pipelines with immutable state"
  - "understanding SubmitState or pipeline architecture"
  - "implementing multi-step workflows with frozen dataclasses"
tripwires:
  - action: "mutating pipeline state directly instead of using dataclasses.replace()"
    warning: "Pipeline state must be frozen. Use dataclasses.replace() to create new state at each step."
---

# State Threading Pattern

A pattern for building linear pipelines where each step transforms an immutable state object, with early termination on error.

## The Pattern

```python
@dataclass(frozen=True)
class PipelineState:
    """Immutable state threaded through pipeline steps."""
    cwd: Path
    branch_name: str
    pr_number: int | None
    # ... fields grow as steps complete

@dataclass(frozen=True)
class PipelineError:
    """Error variant for pipeline termination."""
    phase: str
    error_type: str
    message: str

# Each step signature follows this contract
PipelineStep = Callable[[ErkContext, PipelineState], PipelineState | PipelineError]
```

## Pipeline Runner

```python
def run_pipeline(
    ctx: ErkContext,
    state: PipelineState,
    steps: list[PipelineStep],
) -> PipelineState | PipelineError:
    for step in steps:
        result = step(ctx, state)
        if isinstance(result, PipelineError):
            return result  # Short-circuit on first error
        state = result
    return state
```

## Step Implementation

Each step receives the current state and returns either updated state or an error:

```python
def prepare_state(ctx: ErkContext, state: PipelineState) -> PipelineState | PipelineError:
    branch_name = ctx.git.branch.get_current_branch(state.cwd)
    if branch_name is None:
        return PipelineError(phase="prepare", error_type="detached-head", message="Not on a branch")
    return dataclasses.replace(state, branch_name=branch_name)
```

## Key Principles

1. **Frozen dataclasses only**: State is immutable; each step creates a new instance via `dataclasses.replace()`
2. **Discriminated union returns**: Every step returns `State | Error`, checked with `isinstance()`
3. **Single discovery location**: The first step consolidates all discovery (branch name, repo root, issue number) to prevent duplication
4. **Short-circuit on error**: The pipeline runner stops at the first error — no partial execution
5. **LBYL throughout**: Steps check preconditions before acting (`if value is None:` → return error)

## Reference Implementation

`src/erk/cli/commands/pr/submit_pipeline.py`:

- `SubmitState` (lines 49–71): 15+ fields accumulated across 8 pipeline steps
- `SubmitError` (lines 74–81): Error with phase, error_type, message, details
- `SubmitStep` type alias (line 88): `Callable[[ErkContext, SubmitState], SubmitState | SubmitError]`
- `_submit_pipeline()` (lines 705–715): Defines the 8-step pipeline
- Runner (lines 720–725): Iterates steps, short-circuits on `isinstance(result, SubmitError)`

## When to Use

Use state threading when:

- A workflow has 3+ sequential steps that share and accumulate data
- Steps can fail independently, and failures should stop the pipeline
- You need clear error attribution (which phase failed and why)
- Testing individual steps in isolation is valuable

## Related Documentation

- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The `State | Error` union pattern
- [PR Submit Pipeline](../cli/pr-submit-pipeline.md) — The primary exemplar of this pattern
