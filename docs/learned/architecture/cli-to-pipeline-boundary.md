---
title: CLI-to-Pipeline Boundary Pattern
read_when:
  - "refactoring complex CLI commands"
  - "separating business logic from Click layer"
  - "deciding when to extract pipeline from CLI command"
tripwires:
  - action: "writing complex business logic directly in Click command functions"
    warning: "Extract to pipeline layer when command has >3 distinct steps or complex state management. CLI layer should handle: Click decorators, parameter parsing, output formatting. Pipeline layer should handle: business logic, state management, error types."
last_audited: "2026-02-03"
audit_result: edited
---

# CLI-to-Pipeline Boundary Pattern

Complex CLI commands benefit from clear separation between Click layer (UI concerns) and pipeline layer (business logic).

## Two-Layer Architecture

### CLI Layer

- Click decorators, parameter parsing, output formatting
- Context creation and dependency injection
- No business logic — delegates to pipeline layer

### Pipeline Layer

- Business logic, validation, execution steps
- State management (frozen dataclasses)
- Discriminated union return types (`State | Error`)
- No Click imports — framework-agnostic

## Decision Threshold: When to Extract Pipeline

Extract when the command meets ANY of:

- **>3 distinct steps** that could fail independently
- **Complex state management** (>5 fields tracking progress)
- **Multiple error types** that need structured handling
- **Hard to test** without invoking full CLI
- **Logic needed outside CLI** (exec scripts, TUI, API)

## When NOT to Extract

Keep CLI layer only if:

- **≤3 steps** with no complex state
- **Single error type** (just success/failure)
- **No reusability** needed outside CLI
- **Fast tests** possible with Click runner

## Reference Implementation: Land Command

- **CLI**: `src/erk/cli/commands/land_cmd.py` — Click decorators, output, context creation
- **Pipeline**: `src/erk/cli/commands/land_pipeline.py` — validation/execution pipelines
- **Tests**: `tests/commands/test_land_pipeline.py` — pipeline unit tests (no Click runner needed)
- **PR**: #6333

## Related Documentation

- [Linear Pipelines](linear-pipelines.md) - Two-pipeline pattern architecture
- [Land State Threading](land-state-threading.md) - Immutable state management
- [Two-Phase Validation Model](../cli/two-phase-validation-model.md) - Foundation pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Error type design
