---
title: State Threading Pattern
read_when:
  - "designing linear pipelines with immutable state"
  - "understanding SubmitState or pipeline architecture"
  - "implementing multi-step workflows with frozen dataclasses"
tripwires:
  - action: "mutating pipeline state directly instead of using dataclasses.replace()"
    warning: "Pipeline state must be frozen. Use dataclasses.replace() to create new state at each step."
  - action: "adding optional fields to pipeline state without defaults"
    warning: "New pipeline state fields must have defaults (usually None) to avoid breaking make_initial_state() factories. See optional-field-propagation.md for the pattern."
---

# State Threading Pattern

State threading is the immutable data flow pattern underlying erk's linear pipelines. This document explains **why** frozen dataclasses and explicit state accumulation matter for pipeline composition, not **what** the code looks like (read the source for that).

## The Core Problem: Mutable State Creates Hidden Dependencies

Traditional imperative code mutates local variables as operations progress:

```python
# WRONG: Mutable state pattern (anti-pattern)
branch_name = None
pr_number = None
issue_number = None

# Step 1
branch_name = get_current_branch()
# Step 2
pr_number = create_pr(branch_name)
# Step 3
issue_number = extract_issue(branch_name)
```

**Why this is wrong:**

1. **Hidden initialization order** — steps must run in exact sequence or variables are undefined
2. **Unclear data flow** — which step populated which variable? Unclear from signatures
3. **Testing friction** — can't test step 3 without running steps 1-2 to populate dependencies
4. **No partial state** — can't pass "state after step 2" as a test fixture

State threading fixes this by making data flow **explicit and compositional**.

## The Solution: Frozen State as Function Arguments

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, SubmitState -->
<!-- Source: src/erk/cli/commands/land_pipeline.py, LandState -->

See `SubmitState` in `src/erk/cli/commands/pr/submit_pipeline.py` and `LandState` in `src/erk/cli/commands/land_pipeline.py` for the reference implementations.

**Pattern structure:**

1. All pipeline state lives in a frozen dataclass with 10-20 fields
2. Each step takes state as input, returns updated state (or error) as output
3. Steps use `dataclasses.replace()` to produce new state with 1-3 fields changed
4. The pipeline runner threads state from step to step

**Why this works:**

- **Explicit dependencies** — step signatures declare exactly which state they consume
- **Testable in isolation** — construct state fixture, call step, assert result fields
- **Clear data flow** — runner shows state transformation sequence at a glance
- **Immutability** — earlier steps can't retroactively change their outputs

## The Accumulation Pattern: Fields Grow as Steps Complete

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, SubmitState fields and make_initial_state -->

The submit pipeline state accumulates 15+ fields across 8 steps. Initial state (from `make_initial_state()`) sets most fields to `None`. Each step populates the fields it resolves.

**Why accumulation instead of separate state objects per phase?**

1. **No adapter code** — one state type flows end-to-end, no conversions between phases
2. **Grep-friendly** — `state.pr_number` appears uniformly across all steps
3. **Forward compatibility** — adding a field only requires updating the steps that populate/consume it, not every step signature

**Trade-off:** State carries fields that aren't relevant to early steps (e.g., `graphite_url` is `None` during validation). This is intentional — the runner doesn't need to know which fields are valid at which step. The `isinstance(result, Error)` check is the only branch.

## The Factory Pattern: make_initial_state() Must Use Defaults

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, make_initial_state -->
<!-- Source: src/erk/cli/commands/land_pipeline.py, make_initial_state and make_execution_state -->

Submit and land both use factory functions to construct initial state. See `make_initial_state()` in both pipelines.

**Why factories instead of direct construction?**

- **Centralized defaults** — all `None` assignments in one place
- **CLI argument mapping** — converts Click parameters to dataclass fields
- **Session ID generation** — default UUID if not provided
- **Multiple entry points** — land has two factories (`make_initial_state` for validation, `make_execution_state` for execution after shell script serialization)

**Critical constraint:** When adding new fields to state, they **must** have default values. Otherwise `make_initial_state()` breaks with "missing required argument" errors. See [Optional Field Propagation](optional-field-propagation.md) for the detailed pattern.

## Discovery Consolidation: The First Step Does All Lookups

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, prepare_state -->

The submit pipeline's `prepare_state()` step resolves 6 fields: `repo_root`, `branch_name`, `parent_branch`, `trunk_branch`, `issue_number`, and performs `.impl/issue.json` validation.

**Why consolidate discovery in step 1 instead of spreading it across steps?**

1. **DRY** — before this pattern, `issue_number` was derived independently in 3+ places
2. **Fail fast** — if branch name can't be resolved or `.impl` validation fails, no later steps run
3. **Explicit preconditions** — later steps assume these fields are populated and never `None`
4. **Single lookup location** — easier to audit "where does `issue_number` come from?"

**Anti-pattern:** Don't add "lazy discovery" steps that re-derive values later. If step 3 needs `repo_root`, it should already be in state from step 1, not re-run `get_repository_root()`.

## Type Narrowing After Error Checks

The discriminated union pattern (`State | Error`) enables type narrowing:

```python
# Inside a step
branch_name = ctx.git.branch.get_current_branch(state.cwd)
if branch_name is None:
    return SubmitError(phase="prepare", error_type="no_branch", ...)
# Type narrowing: branch_name is str here, not str | None
return dataclasses.replace(state, branch_name=branch_name)
```

**Why this matters:**

- **No redundant checks** — caller doesn't re-check `is None` on fields populated by earlier steps
- **IDE autocomplete** — type checker knows `state.branch_name` is `str`, not `str | None`
- **Runtime safety** — if a step forgets to check, type error surfaces at development time

See [Discriminated Union Error Handling](discriminated-union-error-handling.md) for the full pattern.

## When to Use State Threading

**Use state threading when:**

- A workflow has 5+ sequential steps that share and accumulate data
- Steps can fail independently, and failures should stop the pipeline
- You need clear error attribution (which phase failed and why)
- Testing individual steps in isolation is valuable

**Don't use state threading when:**

- 1-3 simple steps that don't accumulate state (inline LBYL checks are simpler)
- Steps are independent and parallelizable (no shared state to thread)
- The workflow is interactive and steps run conditionally based on user input

**Decision test:** If you find yourself passing 4+ arguments to every step function, you probably need state threading.

## Comparison to Other Patterns

### vs. Mutable Context Object

Some codebases use a mutable "context" object that steps modify in-place:

```python
# Anti-pattern: mutable context
ctx.branch_name = get_branch()
ctx.pr_number = create_pr(ctx)
```

**Why state threading is better:**

- Frozen state makes mutations **impossible**, not just discouraged
- `dataclasses.replace()` creates new state, leaving old state unmodified (useful for debugging)
- Type checker enforces that all fields are read-only

### vs. Monad Chains (Result[T, E])

Rust-style `Result` monads achieve similar composability but with more ceremony in Python:

```python
# Generic monad pattern (verbose in Python)
result = (
    validate_branch()
    .and_then(lambda b: create_pr(b))
    .and_then(lambda pr: update_metadata(pr))
)
```

**Why state threading is more pythonic:**

- `isinstance()` checks integrate with Python's type narrowing
- Step signatures are plain functions, not monad wrappers
- Error handling is explicit (return `Error`) rather than hidden in monad machinery

## Related Documentation

- [Linear Pipeline Architecture](linear-pipelines.md) — The broader two-pipeline pattern using state threading
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The `State | Error` union pattern
- [Optional Field Propagation](optional-field-propagation.md) — How to add new fields to existing pipeline state
- [Land State Threading](land-state-threading.md) — Land-specific state threading patterns
