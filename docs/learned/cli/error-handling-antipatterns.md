---
title: CLI Error Handling Anti-Patterns
last_audited: "2026-02-13"
audit_result: clean
read_when:
  - "handling expected CLI failures"
  - "deciding between RuntimeError and UserFacingCliError"
  - "converting exception-based error handling to UserFacingCliError"
  - "writing actionable error messages for pipeline failures"
tripwires:
  - score: 7
    action: "Using RuntimeError for expected CLI failures"
    warning: "RuntimeError signals a programmer error (bug in the code), NOT expected user-facing failures. Use UserFacingCliError for expected conditions (missing files, invalid input, precondition violations) that should exit cleanly with an actionable message."
    context: "Expected failures are part of normal CLI operation. RuntimeError implies something impossible happened; UserFacingCliError implies the user needs to fix their input or environment."
  - action: "converting RuntimeError catch blocks to UserFacingCliError"
    warning: "Always preserve exception chain with 'from e'. Pattern: raise UserFacingCliError(str(e)) from e"
---

# CLI Error Handling Anti-Patterns

## The Core Problem: Semantic Mismatch

**RuntimeError communicates the wrong thing.** When a CLI command raises `RuntimeError("Branch name is required")`, it signals "a programmer forgot to validate inputs" rather than "the user forgot to provide a required argument."

This semantic confusion creates three failure modes:

1. **Misleading stack traces** — Users see Python internals for expected failures like missing files or invalid arguments
2. **Hard to catch selectively** — Generic `RuntimeError` can't distinguish between "user error" and "actual bug"
3. **Inconsistent UX** — Some errors are styled, others are raw Python exceptions

## The Solution: Exception Types That Match Intent

<!-- Source: src/erk/cli/ensure.py, UserFacingCliError -->

Use `UserFacingCliError` for expected CLI failures. See the class definition in `src/erk/cli/ensure.py:33-53`.

**Why it exists:**

- Extends `click.ClickException` so Click automatically intercepts it at all command levels
- Provides styled error output (`Error: ` prefix in red) through `.show()` method
- Works identically in production CLI and `CliRunner` tests
- Caught at CLI entry point for consistent exit handling

## Decision Table: Which Exception Type?

| Use This             | When                                   | Example Scenario                                          |
| -------------------- | -------------------------------------- | --------------------------------------------------------- |
| `UserFacingCliError` | Expected user-facing failures          | Missing config, invalid input, precondition violations    |
| `RuntimeError`       | Programmer errors (impossible states)  | Assertion violations, logic bugs, unreachable branches    |
| Gateway error types  | Internal operation failures (consumed) | `PushError`, `GitOperationError` (converted to CLI error) |

**The bright line:** If a user can trigger the error through normal CLI usage (wrong flag, missing file, invalid state), it's `UserFacingCliError`. If it indicates a bug in erk's code, it's `RuntimeError`.

## Migration Pattern from PR #6353

PR #6353 converted 8 files from `RuntimeError` to `UserFacingCliError`. The pattern:

**Before:**

```python
if not branch_name:
    raise RuntimeError("Branch name is required")
```

**After:**

```python
if not branch_name:
    raise UserFacingCliError("Branch name is required")
```

**What improved:**

- Correct semantic signal (user error, not code bug)
- Consistent error styling through Click's exception handling
- Type-based error handling in tests
- No stack trace for expected failures

## Anti-Pattern Examples

**WRONG** — RuntimeError for expected validation failure:

```python
def get_plan_folder() -> Path:
    impl_path = Path(".impl")
    if not impl_path.exists():
        raise RuntimeError("No .impl/ folder found in current directory")
    return impl_path
```

**CORRECT** — UserFacingCliError with actionable guidance:

```python
def get_plan_folder() -> Path:
    impl_path = Path(".impl")
    if not impl_path.exists():
        raise UserFacingCliError(
            "No .impl/ folder found in current directory\n\n"
            "Run 'erk plan-implement' to set up an implementation environment"
        )
    return impl_path
```

Notice the corrected version includes:

1. Multiline error message with blank line separator
2. Actionable remediation command
3. Exception type that signals "user needs to act" not "code is broken"

## The `Ensure` Pattern

<!-- Source: src/erk/cli/ensure.py, Ensure class methods -->

The `Ensure` class provides domain-specific assertion methods that all raise `UserFacingCliError`. See methods like `Ensure.invariant()`, `Ensure.path_exists()`, `Ensure.git_branch_exists()` in `src/erk/cli/ensure.py:55-556`.

These methods:

- Standardize precondition checking across commands
- Provide type narrowing (e.g., `Ensure.not_none()` converts `T | None` to `T`)
- Include default error messages with remediation hints
- Enable LBYL pattern enforcement (check before operation, not exception recovery)

**Usage pattern:**

```python
# Type narrowing + validation in one call
safe_path: Path = Ensure.not_none(path, "Worktree path not found")

# Domain-specific precondition
Ensure.git_branch_exists(ctx, repo.root, branch)

# External tool availability (LBYL check before subprocess calls)
Ensure.gh_authenticated(ctx)
```

## When RuntimeError Is Correct

RuntimeError is **appropriate** for:

1. **Assertion failures** — Internal invariants violated (`assert len(branches) > 0` with RuntimeError in handler)
2. **Impossible states** — Logic branches that should never execute ("unreachable code reached")
3. **Developer configuration errors** — Mistakes in erk's own code/config (not user input)

Example of correct RuntimeError usage:

```python
if error_type not in {"validation", "execution"}:
    raise RuntimeError(f"Unknown error_type: {error_type}")  # Code bug if this executes
```

This signals "the programmer who wrote this code made a mistake in their enum handling" rather than "the user provided invalid input."

## Current Migration Status

As of PR #6860:

- PR #6353: 8 files converted from RuntimeError → UserFacingCliError
- PR #6860: admin.py converted — 8 error patterns migrated (4 `Ensure.not_none`, 1 `Ensure.invariant`, 3 RuntimeError-to-UserFacingCliError with exception chaining)
- Cumulative: ~16 files/patterns converted across PRs #6353 and #6860
- Remaining: Audit remaining CLI commands for RuntimeError instances that should be UserFacingCliError
- Ongoing migration: Convert anti-pattern RuntimeErrors when editing affected code

When you encounter `RuntimeError` in CLI command code, ask: "Can a user trigger this through normal CLI usage?" If yes, migrate to `UserFacingCliError`.

### Exception Chaining with `from e`

When converting `RuntimeError` catch blocks to `UserFacingCliError`, always preserve the exception chain:

```python
except RuntimeError as e:
    raise UserFacingCliError(str(e)) from e
```

The `from e` preserves the causal chain for debugging while presenting a clean user-facing error message. This pattern was established in PR #6860.

## Actionable Error Messages in Pipelines

The same principle applies within pipeline error types like `SubmitError`. Even though these are consumed by the CLI layer (not raised as exceptions), the `message` field should tell the user what happened and what to do.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _graphite_first_flow -->

**Format pattern** (established in PR #6885):

1. First line: clear problem statement (what happened)
2. Blank line separator
3. Explicit command sequence with inline comments
4. Final command shows "what to do next" (re-run original command)

See the `graphite_restack_required` message in `_graphite_first_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py` for the reference implementation.

**Anti-pattern:** Wrapping raw subprocess stderr directly into the error message. The user sees internal tool output without context or remediation guidance.

## Multi-Layer Error Wrapping Without Semantic Interpretation

When subprocess calls fail, the error passes through multiple layers:

1. `CalledProcessError` (subprocess) with raw stderr
2. `RuntimeError` (gateway layer) wrapping the subprocess error
3. `SubmitError` (pipeline layer) wrapping the RuntimeError
4. `ClickException` (CLI layer) presenting the SubmitError message

Each layer adds wrapping but, without pattern detection, none adds semantic value. The user sees nested error messages that read like internal debugging output.

**Solution:** At the pipeline boundary (where RuntimeError is caught), detect known error patterns and convert to semantic error types with actionable guidance. The pipeline layer is the right place because it has domain context (what operation was attempted) that the gateway layer lacks.

See `_graphite_first_flow()` in `src/erk/cli/commands/pr/submit_pipeline.py` for the pattern of catching RuntimeError and routing to specific SubmitError error_types based on keyword detection.

## Case Study: Bypass Flag vs Actionable Error (PR #6885)

**Initial approach:** Add `--no-restack` flag to bypass the restack requirement when `gt submit` detects divergence.

**User correction:** Don't offer a bypass. Help users understand they have conflicts and how to resolve them.

**Why bypass was wrong:** The restack isn't optional -- the stack genuinely has conflicts. A `--no-restack` flag would let users push diverged stacks, creating worse problems downstream. The correct response is an actionable error message explaining how to resolve the actual issue.

**Principle:** When a subprocess failure requires user intervention, the error message should guide users through resolution, not offer a flag to skip the problem. Technical bypasses hide issues; actionable errors solve them.

## Related Patterns

- **Discriminated union error handling** — `docs/learned/architecture/discriminated-union-error-handling.md` explains when to use `T | ErrorType` instead of exceptions
- **Output styling** — `docs/learned/cli/output-styling.md` documents the `Error: ` prefix convention and Click styling patterns
- **LBYL enforcement** — `dignified-python` skill covers the broader LBYL vs EAFP philosophy (check conditions first, never try/except for control flow)
- **Error detection patterns** — `docs/learned/cli/error-detection-patterns.md` documents keyword-based error classification for subprocess failures

## Why This Matters

Correct exception types make error handling predictable:

- Test assertions can catch specific exception types
- Agents reading stack traces understand whether they hit a bug or user error
- CLI error output is consistently styled
- Users know whether to file a bug report or fix their command

Semantic precision in exception types is semantic precision in program behavior.
