---
title: EnsureIdeal Pattern for Type Narrowing
read_when:
  - "handling discriminated union returns in CLI commands"
  - "narrowing types from T | NonIdealState or T | ErrorType"
  - "working with PR lookups, branch detection, or API calls that return union types"
  - "seeing EnsureIdeal in code and wondering when to use it vs Ensure"
tripwires:
  - action: "using EnsureIdeal for discriminated union narrowing"
    warning: "Only use when the error type implements NonIdealState protocol OR provides a message field. For custom error types without standard fields, add a specific EnsureIdeal method."
  - action: "choosing between Ensure and EnsureIdeal"
    warning: "Ensure is for invariant checks (preconditions). EnsureIdeal is for type narrowing (handling operations that can return non-ideal states). If the value comes from an operation that returns T | ErrorType, use EnsureIdeal."
last_audited: "2026-02-05"
audit_result: edited
---

# EnsureIdeal Pattern for Type Narrowing

The `EnsureIdeal` class provides type-safe narrowing for discriminated union returns from gateway operations. It complements `Ensure` (invariant checks) by handling expected failure cases from I/O operations.

For the full method catalog and type signatures, see `EnsureIdeal` in `src/erk/cli/ensure_ideal.py`.

## Semantic Distinction

| Class         | Purpose                       | Use Case                                             | Example                                                          |
| ------------- | ----------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------- |
| `Ensure`      | Invariant/precondition checks | Asserting program invariants, validating arguments   | `Ensure.invariant(len(args) == 1, "Expected 1 argument")`        |
| `EnsureIdeal` | Type narrowing from unions    | Handling operations that return `T \| NonIdealState` | `pr = EnsureIdeal.unwrap_pr(github.get_pr(...), "PR not found")` |

**Key Difference**: `Ensure` checks conditions that should never be false in correct code. `EnsureIdeal` handles expected failure cases from external operations (API calls, git commands, file reads).

## Decision Tree

```
Is this value from an operation that can fail?
├─ NO → Use Ensure.invariant() or Ensure.truthy()
│        (e.g., validating CLI arguments, checking config values)
│
└─ YES → Does it return T | ErrorType?
         ├─ YES → Use EnsureIdeal
         │        (e.g., github.get_pr(), git.branch(), api.fetch())
         │
         └─ NO → Use try/except (for exceptions)
                  or handle inline (for bool returns)
```

## Why Two PR Methods?

`EnsureIdeal` has both `pr()` and `unwrap_pr()` because the codebase has two different "PR not found" types:

- **`PRNotFound`** (in `erk_shared.gateway.github.types`): A sentinel dataclass without a `message` property. Used by low-level gateway methods like `github.get_pr()` and `github.get_pr_for_branch()`. Requires the caller to supply an error message, so use `EnsureIdeal.unwrap_pr(result, "custom message")`.

- **`NoPRForBranch` / `PRNotFoundError`** (in `erk_shared.non_ideal_state`): Implement the `NonIdealState` protocol with built-in `message` properties. Used by `GitHubChecks` methods (in `erk_shared.gateway.github.checks`). Use `EnsureIdeal.pr(result)` -- no custom message needed.

In practice, `unwrap_pr()` is the most commonly used variant. See usage in `src/erk/cli/commands/land_cmd.py` and `src/erk/cli/commands/land_pipeline.py`.

## When to Add New Methods

Add a new `EnsureIdeal` method when:

1. A gateway operation returns a new discriminated union type
2. The error type implements `NonIdealState` OR has a `message` field
3. The union is used in multiple CLI commands (reusable pattern)

Follow the existing method pattern in `src/erk/cli/ensure_ideal.py` -- each method checks `isinstance()`, outputs a styled error, and raises `SystemExit(1)`.

## Related Documentation

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Pattern for defining discriminated union types
- [Two-Phase Validation Model](two-phase-validation-model.md) - CLI validation architecture
- [CLI Error Handling](../testing/cli-error-handling.md) - Ensure class for invariant checks
