---
title: Land State Threading Pattern
read_when:
  - "implementing pipelines with immutable state"
  - "using dataclasses.replace() for state updates"
  - "designing stateful workflows with frozen dataclasses"
tripwires:
  - action: "threading state through pipeline steps with mutable dataclasses"
    warning: "Use frozen dataclasses (@dataclass(frozen=True)) for pipeline state. Update fields with dataclasses.replace() to create new instances. Immutability enables caching, testability, and replay."
last_audited: "2026-02-07 20:43 PT"
audit_result: edited
---

# Land State Threading Pattern

Pipeline steps thread immutable state through functional transformations. This document explains **why** erk uses frozen dataclasses for pipeline state, not **what** the implementation looks like (the code already shows that).

## Why Immutability for Pipeline State

The land command demonstrates three critical benefits of immutable state threading that generalize to any multi-step pipeline:

### 1. Shell Script Serialization Boundary

<!-- Source: src/erk/cli/commands/land_pipeline.py, two-pipeline pattern -->

The land command splits into two pipelines separated by a shell script boundary. See `run_validation_pipeline()` and `run_execution_pipeline()` in `src/erk/cli/commands/land_pipeline.py`.

**The problem**: After validation completes, the user must approve execution by sourcing a shell script. This creates a serialization boundary—all state must encode as CLI flags and arguments.

**Why immutability matters**:

- Validation pipeline populates state fields progressively (branch name, PR details, objective number)
- Shell script generator reads these fields to construct the `erk exec land-execute` command
- If state were mutable, there's no guarantee the shell script captures the exact state validation produced
- Immutable state means validation output = shell script input (no hidden mutations)

Without immutability, a bug could mutate state after validation but before script generation, causing the execution pipeline to run with different state than validation checked.

### 2. Progressive Field Population Without Initialization Complexity

<!-- Source: src/erk/cli/commands/land_pipeline.py, LandState dataclass -->

The `LandState` dataclass has 21 fields organized into three lifecycle stages (matching the source code comments). See the `LandState` definition in `src/erk/cli/commands/land_pipeline.py`.

**CLI inputs** (8 fields): `cwd`, `force`, `script`, `pull_flag`, `no_delete`, `up_flag`, `dry_run`, `target_arg`

**Resolved target** (9 fields, populated by `resolve_target()`): `repo_root`, `main_repo_root`, `branch`, `pr_number`, `pr_details`, `worktree_path`, `is_current_branch`, `use_graphite`, `target_child_branch`

**Derived** (4 fields, populated by later pipeline steps): `objective_number`, `plan_issue_number`, `cleanup_confirmed`, `merged_pr_number`

**Why frozen dataclasses work**: Each validation step populates the fields it discovers using `dataclasses.replace()`, leaving others unchanged. The pattern scales to any number of discovery stages without complex initialization logic.

**Alternative approaches considered**:

- **Builder pattern**: Requires separate builder class, more verbose, no type safety until build()
- **Mutable dataclass**: Easy to accidentally mutate in the wrong place, no replay capability
- **Multiple state classes**: Loses continuity across pipeline stages, duplicates fields

Frozen dataclasses with progressive population hit the sweet spot: type-safe at every stage, explicit about what changed, minimal boilerplate.

### 3. Two-Pipeline Replay Without Re-Execution

<!-- Source: src/erk/cli/commands/land_pipeline.py, make_execution_state() -->

The execution pipeline must reconstruct state from shell script arguments without re-running validation. See `make_execution_state()` in `src/erk/cli/commands/land_pipeline.py`.

**The problem**: Validation ran in the CLI process. Execution runs in a separate `erk exec land-execute` process. The exec script passes validated state as CLI flags (`--pr-number 123 --branch feature-x --objective 456`).

**Why immutability enables this**:

- Validation's final state is deterministic (same inputs + same context → same state)
- Shell script encodes state as flags: `--branch`, `--pr-number`, `--objective-number`, `--use-graphite`
- Execution pipeline reconstructs state from these flags using `make_execution_state()`
- Reconstructed state is **semantically equivalent** to validation's output (all relevant fields match)

If state were mutable, validation could have accumulated hidden mutations not visible in the shell script. Immutability guarantees: if flags match, state matches.

## When Mutable State Is Acceptable

Not every pipeline needs frozen dataclasses. Use mutable state when:

- **Single-process execution**: No serialization boundary, no replay requirements
- **Short-lived state**: Object used immediately then discarded
- **Performance-critical**: Allocation overhead matters (rare in CLI tools)

The land command has none of these properties—it crosses process boundaries, requires replay, and runs once per user action (allocation cost negligible).

## The dataclasses.replace() Pattern

<!-- Source: src/erk/cli/commands/land_pipeline.py, resolve_target() -->

**Pattern**: Each step returns `dataclasses.replace(state, field=new_value, ...)` with only the discovered fields. See `resolve_target()` in `src/erk/cli/commands/land_pipeline.py` for the canonical example -- the return statement lists exactly which fields changed.

**Why this pattern works**:

- Type-safe: IDE autocomplete for field names, compiler catches typos
- Explicit: Reading the code shows exactly which fields changed
- Composable: Output of one step becomes input to next step
- Debuggable: Print `state` before/after to see exact diff

**Anti-pattern to avoid**:

```python
# WRONG: Mutable state mutation
state.branch = discovered_branch  # Compiler error with frozen=True
return state
```

This anti-pattern loses all the benefits above—no type safety, no explicitness, no replay capability.

## Type Narrowing Caveat

After validation completes, certain fields are guaranteed populated (`pr_details`, `branch`, `pr_number`). Python's type system doesn't track this narrowing—types still show `int | None`.

**Workaround**: Use assertions in execution steps that depend on validated fields.

```python
def merge_pr(ctx: ErkContext, state: LandState) -> LandState | LandError:
    assert state.pr_details is not None  # Validated in prior pipeline
    # ... use state.pr_details safely
```

This is safe because execution only runs after validation succeeds. The assertion documents the validation pipeline's guarantee.

## Reference Implementation

<!-- Source: src/erk/cli/commands/land_pipeline.py -->

See `src/erk/cli/commands/land_pipeline.py` for:

- `LandState` dataclass (frozen, 21 fields)
- Pipeline step signature: `(ErkContext, LandState) -> LandState | LandError`
- State update pattern: `dataclasses.replace(state, field=new_value)`
- State factories: `make_initial_state()`, `make_execution_state()`

Test coverage in `tests/unit/cli/commands/land/pipeline/` demonstrates state threading across multiple steps.

## Related Documentation

- [Linear Pipelines](linear-pipelines.md) - Two-pipeline pattern with validation and execution
- [Pipeline Transformation Patterns](pipeline-transformation-patterns.md) - Functional composition principles
- [Erk Architecture Patterns](erk-architecture.md) - Immutable dataclass patterns across erk
