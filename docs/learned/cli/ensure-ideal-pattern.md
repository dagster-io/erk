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
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# EnsureIdeal Pattern for Type Narrowing

`EnsureIdeal` provides CLI-level type narrowing for gateway operations that return discriminated unions. It's a specialized tool for the validation phase of CLI commands, converting `T | ErrorType` into `T` or terminating with styled error output.

## Why Two Classes?

The separation between `Ensure` and `EnsureIdeal` reflects two distinct validation concerns:

| Class         | Validates                    | Source of Values               | Failure Meaning                       |
| ------------- | ---------------------------- | ------------------------------ | ------------------------------------- |
| `Ensure`      | Invariants and preconditions | Arguments, config, local state | Programming error or user input error |
| `EnsureIdeal` | Gateway operation results    | I/O operations, API calls      | Expected external failure             |

**Decision rule**: If the value originates from a gateway method returning `T | ErrorType`, use `EnsureIdeal`. If it's an argument check, config validation, or state assertion, use `Ensure`.

### Why This Matters

`Ensure.invariant(not isinstance(result, PRNotFound), "...")` mixes type checking with error handling, bypassing the type narrowing that Python's `isinstance()` provides. `EnsureIdeal` methods explicitly handle the error type and return the narrowed success type, giving you both error handling AND type safety.

## The Two PR Methods Explained

<!-- Source: src/erk/cli/ensure_ideal.py, EnsureIdeal.pr, EnsureIdeal.unwrap_pr -->

`EnsureIdeal` has two PR-narrowing methods because erk has two different "PR not found" representations:

### `unwrap_pr(result, message)` — For Low-Level Gateway Calls

Use with gateway methods returning `PRDetails | PRNotFound`. Call `EnsureIdeal.unwrap_pr(result, message)` where you supply the error message because `PRNotFound` is a minimal sentinel without a `message` field.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, PRNotFound -->

See `PRNotFound` in `packages/erk-shared/src/erk_shared/gateway/github/types.py`.

### `pr(result)` — For GitHubChecks Methods

Use with `GitHubChecks` methods returning `PRDetails | NoPRForBranch | PRNotFoundError`. Call `EnsureIdeal.pr(result)` with no message parameter — the error types implement `NonIdealState` protocol which includes a `message` property.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/checks.py, GitHubChecks.pr_for_branch -->

See `GitHubChecks.pr_for_branch()` in `packages/erk-shared/src/erk_shared/gateway/github/checks.py`.

### Usage Frequency

In practice, `unwrap_pr()` appears far more often because CLI commands work directly with the GitHub gateway ABC, not the `GitHubChecks` wrapper. The `pr()` method exists for specialized contexts where the NonIdealState types are already in play.

## When to Add New EnsureIdeal Methods

Add a new narrowing method when ALL of these conditions hold:

1. **Gateway returns a discriminated union** — not an exception, not a boolean
2. **Multiple CLI commands use this union** — if only one caller exists, inline the narrowing
3. **Error type has a `message` field or implements `NonIdealState`** — otherwise the pattern doesn't fit

### What Not to Add

Don't add EnsureIdeal methods for:

- **One-off unions** used by a single command — inline the narrowing
- **Exception-based errors** — those bypass type narrowing entirely
- **Boolean returns** — use `Ensure.truthy()` or inline checks
- **Error types without messages** — either add `unwrap_*` pattern (like PR) or refactor the error type

## Relationship to Two-Phase Validation

`EnsureIdeal` is a Phase 1 (validation) tool. It terminates on failure, so it must run _before_ any mutations occur.

**WRONG** — Mutation before narrowing:

```python
ctx.git.merge_pr(pr_number)  # Mutation!
pr = EnsureIdeal.unwrap_pr(ctx.github.get_pr(...), "...")  # May terminate!
```

**CORRECT** — Narrow types first, mutate after:

```python
pr = EnsureIdeal.unwrap_pr(ctx.github.get_pr(...), "...")  # Narrowing first
# ... other validations ...
ctx.git.merge_pr(pr.number)  # Safe: pr is guaranteed valid
```

## Implementation Pattern

<!-- Source: src/erk/cli/ensure_ideal.py, EnsureIdeal class structure -->

All `EnsureIdeal` methods follow the same 3-step pattern:

1. **Type check**: `isinstance(result, ErrorType)`
2. **Styled output**: `user_output(click.style("Error: ", fg="red") + message)`
3. **Exit**: `raise SystemExit(1)`

See the method implementations in `src/erk/cli/ensure_ideal.py`.

Why `SystemExit`? It exits immediately without stack traces, which is appropriate for expected failures like "PR not found". These aren't bugs — they're operational conditions that should present cleanly to users.

## Related Documentation

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — When to use unions vs exceptions
- [Two-Phase Validation Model](two-phase-validation-model.md) — Where EnsureIdeal fits in command structure
