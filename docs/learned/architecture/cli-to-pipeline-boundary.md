---
title: CLI-to-Pipeline Boundary Pattern
read_when:
  - "refactoring complex CLI commands"
  - "separating business logic from Click layer"
  - "deciding when to extract pipeline from CLI command"
tripwires:
  - action: "writing complex business logic directly in Click command functions"
    warning: "Extract to pipeline layer when command has >3 distinct steps or complex state management. CLI layer should handle: Click decorators, parameter parsing, output formatting. Pipeline layer should handle: business logic, state management, error types."
last_audited: "2026-02-07 19:46 PT"
audit_result: edited
---

# CLI-to-Pipeline Boundary Pattern

## The Separation Problem

Click commands naturally accumulate business logic over time. As commands grow, the Click layer becomes tangled with validation, state management, and execution logic. This creates three problems:

1. **Testing difficulty** - Testing requires Click test runners instead of direct function calls
2. **Framework lock-in** - Business logic becomes coupled to Click decorators and context objects
3. **Reusability** - Logic can't be reused outside CLI context (exec scripts, TUI, API)

The CLI-to-pipeline boundary solves this by extracting business logic into a framework-agnostic pipeline layer.

## Two-Layer Architecture

### CLI Layer Responsibilities

- Click decorators (`@click.command`, `@click.option`, etc.)
- Parameter parsing and validation (Click types, ranges, choices)
- Output formatting (`user_output`, `click.style`)
- Context creation (`create_context`, `discover_repo_context`)
- **No business logic** - delegates immediately to pipeline layer

### Pipeline Layer Responsibilities

- Business logic execution (validation, state transitions, operations)
- State management (frozen dataclasses threaded through steps)
- Discriminated union return types (`State | Error`)
- **Minimal framework coupling** - no Click decorators or context objects; minor `click.style()` usage for output formatting is acceptable

## Decision Threshold: When to Extract

Extract to pipeline layer when **ANY** of these apply:

| Threshold                      | Why It Matters                                         |
| ------------------------------ | ------------------------------------------------------ |
| **>3 distinct steps**          | Each step can fail independently → needs structured error handling |
| **Complex state (>5 fields)**  | State management requires immutable threading pattern  |
| **Multiple error types**       | Need discriminated unions for type-safe error handling |
| **Hard to test**               | Click runner overhead makes tests slow and brittle     |
| **Logic needed outside CLI**   | Exec scripts, TUI, API need same logic without Click   |

### When NOT to Extract

Keep CLI layer only if **ALL** of these apply:

- ≤3 steps with no complex state
- Single error type (just success/failure)
- No reusability needed outside CLI
- Fast tests possible with Click runner

## Reference Implementation: Land Command

The land command demonstrates full separation between CLI and pipeline layers:

<!-- Source: src/erk/cli/commands/land_cmd.py -->

**CLI layer** (`land_cmd.py`): Handles Click decorators, argument parsing, context creation, output formatting. The main `land()` function (lines 1624-1716) orchestrates two pipelines: validation followed by execution. It creates initial state via `make_initial_state()`, runs validation pipeline, builds `LandTarget` from results, then delegates to `_land_target()` for script generation.

<!-- Source: src/erk/cli/commands/land_pipeline.py -->

**Pipeline layer** (`land_pipeline.py`): Contains two pipelines with 11 total steps (5 validation, 6 execution). Each step has signature `(ErkContext, LandState) -> LandState | LandError`. The validation pipeline (lines 104-402) resolves targets and gathers confirmations. The execution pipeline (lines 410-555) performs mutations. State factories `make_initial_state()` and `make_execution_state()` (lines 616-706) construct initial states for each pipeline.

**Why this works**:

- CLI layer has zero business logic - just Click ceremony and pipeline orchestration
- Pipeline layer is testable without Click test runners
- Same pipeline logic can be invoked from exec scripts (via `erk exec land-execute`)
- Pipeline steps compose via functional signature
- Discriminated unions provide type-safe error handling

## Architectural Trade-offs

### What You Gain

1. **Testability** - Pipeline steps are pure functions testable without Click runners
2. **Reusability** - Same logic callable from CLI, exec scripts, TUI, API
3. **Type safety** - Discriminated unions (`State | Error`) make error paths explicit
4. **Composability** - Pipeline steps chain via consistent signature

### What You Pay

1. **Indirection** - Two files instead of one (CLI layer + pipeline layer)
2. **State threading** - Must thread immutable state through pipeline steps
3. **Boilerplate** - Need state factories, pipeline runners, error types

**When the cost is worth it**: Commands with >3 steps or complex state management. The land command's 11 steps and 21-field state justify the architectural overhead.

**When it's not**: Simple commands with ≤3 steps. A command that just fetches a value and prints it doesn't need pipeline extraction.

## Historical Context: Why Land Needed This

The land command originally interleaved validation and execution: merge PR, prompt for cleanup confirmation, delete worktree. This created **partial mutation risk** - if the user declined cleanup, the PR was already merged but the worktree remained.

The two-pipeline pattern batched all confirmations upfront (validation phase) before any mutations (execution phase). This eliminated partial state.

The pipeline extraction also enabled shell script serialization - after validation passes, the CLI generates a script that invokes `erk exec land-execute` with validated state as arguments. The user sources the script to complete execution.

## Cross-References

For understanding the patterns used in the pipeline layer:

- [Linear Pipelines](linear-pipelines.md) - Two-pipeline pattern architecture with functional composition
- [Land State Threading](land-state-threading.md) - Immutable state management via `dataclasses.replace()`
- [Two-Phase Validation Model](../cli/two-phase-validation-model.md) - Batching confirmations before mutations
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Type-safe error propagation with `State | Error`

For understanding when to apply this pattern to other commands, see the decision threshold table above. If your command has >3 steps or complex state, follow the land command's structure.
