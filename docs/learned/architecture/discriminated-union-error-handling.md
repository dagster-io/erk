---
title: Discriminated Union Error Handling
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "designing return types for operations that may fail"
  - "implementing T | ErrorType patterns"
  - "handling errors without exceptions"
tripwires:
  - action: "choosing between exceptions and discriminated unions for operation failures"
    warning: "If callers branch on the error and continue the operation, use discriminated unions. If all callers just terminate and surface the message, use exceptions. Read the 'When to Use' section."
  - action: "migrating a gateway method to return discriminated union"
    warning: "Update ALL 5 implementations (ABC, real, fake, dry_run, printing) AND all call sites AND tests. Incomplete migrations break type safety."
  - action: "accessing properties on a discriminated union result without isinstance() check"
    warning: "Always check isinstance(result, ErrorType) before accessing success-variant properties. Without type narrowing, you may access .message on a success type or .data on an error type."
  - action: "using None as a success return value in a validation function (ErrorType | None where None = success)"
    warning: "None-as-success is counterintuitive — None typically signals absence/failure, not success. Use ValidThing | InvalidThing so both outcomes are explicit named types."
  - action: "using if/else on a discriminated union without isinstance() for type narrowing"
    warning: "Type checkers require isinstance() for narrowing. 'if result.is_error' or 'if not result' does not narrow. Use 'if isinstance(result, ErrorType):' for correct narrowing in both branches."
  - action: "returning a collection (list, tuple, str) directly from a function with NonIdealState return type"
    warning: "Raw built-ins can't inherit EnsurableResult. Wrap in a named frozen dataclass that inherits EnsurableResult and implements __iter__ if needed. See 'The Wrapping Rule' section."
---

# Discriminated Union Error Handling

Erk uses discriminated unions (`SuccessType | ErrorType`) for LBYL-compliant error handling at gateway and pipeline boundaries. This pattern makes failure modes explicit in type signatures and enables callers to branch on specific error types.

## The Core Trade-off: Unions vs Exceptions

**Use discriminated unions when the caller continues after failure** — branching logic, multiple error types, or inspection of error fields (like `pr_number`, `branch_name`).

**Use exceptions when all callers terminate identically** — error just surfaces as a message, no branching logic, no meaningful field inspection.

### When Exceptions Are Better: The Worktree Operations Case

Worktree add/remove failures are _expected_ (path collisions, missing branches), but they're still better as exceptions because no caller does anything beyond extracting the message and terminating:

```python
# All callers do the same thing: extract message and exit
try:
    git.worktree.add_worktree(repo_root, path, branch)
except RuntimeError as e:
    raise UserFacingCliError(str(e))
```

The exception pattern is simpler here: no caller branches on error content, no caller inspects error structure, and every call site terminates identically. A discriminated union would add ceremony without value.

### When Unions Are Better: Branch Operations

Contrast with `create_branch` and `submit_branch`, where callers _do_ branch on error types:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py, BranchCreated, BranchAlreadyExists -->

See `BranchCreated` and `BranchAlreadyExists` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py`.

```python
# Branch creation
result = git_ops.create_branch(cwd, "feature", "main", force=False)
if isinstance(result, BranchAlreadyExists):
    # Continue: use existing branch or prompt for new name
    logger.info(f"Branch {result.branch_name} already exists, using it")
    return result.branch_name
# Type narrowing: result is now BranchCreated (empty marker)
```

The discriminated union enables:

1. **Branching logic** — different handling for "already exists" vs other failures
2. **Field inspection** — accessing `result.branch_name` to construct user messages
3. **Type-safe continuation** — caller keeps running after handling the error

## Pattern Structure

Gateway methods return `SuccessType | ErrorType` where:

- **Success types** are empty marker dataclasses (e.g., `PushResult`, `BranchCreated`)
- **Error types** are frozen dataclasses with `message: str` and `error_type` property

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py, PushResult, PushError -->

See `PushResult` and `PushError` in `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`.

```python
# Caller pattern with type narrowing
push_result = ctx.git.remote.push_to_remote(repo_root, "origin", branch)
if isinstance(push_result, PushError):
    raise UserFacingCliError(push_result.message)
# Type narrowing: push_result is now PushResult
```

Why empty success types? Because the operation itself (push succeeded, branch created) is the success signal. Additional data (like branch names or PR numbers) lives in the pipeline state, not the result type.

## The Ensure Pattern: Uniform Unwrapping

Both sides of a `T | NonIdealState` union implement `.ensure()`, enabling callers to unwrap the result in a single chained call:

- **Error types** (`NonIdealState`): `.ensure()` raises `NonIdealStateError`
- **Success types** (`EnsurableResult`): `.ensure()` returns `self` unchanged

```python
# One-liner: raises if error, returns the value if success
pr_details = GitHubChecks.pr_by_number(github, repo_root, pr).ensure()

# Chained from a future:
comments = comments_future.result().ensure()
```

This replaces the old helper-function pattern:

```python
# Old: per-type helper functions
def _ensure_comments(result: list[IssueComment] | GitHubAPIFailed) -> list[IssueComment]:
    if isinstance(result, GitHubAPIFailed):
        exit_with_error(result.error_type, result.message)
    assert not isinstance(result, GitHubAPIFailed)
    return result

comments = _ensure_comments(GitHubChecks.issue_comments(...))
```

### The Wrapping Rule

**Success types must be named classes, never raw built-ins.** Raw built-ins (`list`, `str`, `int`) cannot inherit from `EnsurableResult`, which breaks the uniform `.ensure()` pattern.

```python
# ❌ Wrong: raw built-in — can't call .ensure()
def issue_comments(...) -> list[IssueComment] | GitHubAPIFailed: ...
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/issues/types.py, IssueComments -->

See `IssueComments` in `packages/erk-shared/src/erk_shared/gateway/github/issues/types.py` for the canonical implementation. The wrapper class:

1. Inherits from `EnsurableResult` → gains `.ensure()` that returns `self`
2. Uses `tuple[T, ...]` not `list[T]` — frozen dataclasses require immutable fields
3. Implements `__iter__` so callers iterate it just like a list

### When to Use `.ensure()` vs `isinstance()`

| Scenario                                            | Use                            |
| --------------------------------------------------- | ------------------------------ |
| All error paths should raise (caller can't recover) | `.ensure()` one-liner          |
| Caller branches on success vs error                 | `isinstance()` check           |
| Caller branches on multiple error types             | `isinstance()` checks per type |

```python
# .ensure() — propagates to handle_non_ideal_exit decorator or test harness
pr_details = GitHubChecks.pr_by_number(github, repo_root, pr).ensure()

# isinstance() — when caller handles the error path explicitly
result = GitHubChecks.issue_comments(issues, root, number)
if isinstance(result, GitHubAPIFailed):
    log_warning(result.message)
    return default_comments
for comment in result:
    ...
```

### Implementation Reference

<!-- Source: packages/erk-shared/src/erk_shared/non_ideal_state.py, EnsurableResult, NonIdealStateMixin -->

See `EnsurableResult` and `NonIdealStateMixin` in `packages/erk-shared/src/erk_shared/non_ideal_state.py`.

- **`EnsurableResult`**: Base class for success types. `.ensure()` returns `self`.
- **`NonIdealStateMixin`**: Provides `.ensure()` for error types that use `message: str` as a field (frozen dataclass field conflicts with `NonIdealState` protocol's `@property message`). Used by `GitHubAPIFailed`.
- **`NonIdealState`**: Protocol for error types with computed `message` properties. `.ensure()` raises `NonIdealStateError`.

## CLI Layer Consumption Pattern

<!-- Source: src/erk/cli/ensure.py, UserFacingCliError -->

CLI commands use `UserFacingCliError` for error propagation. See `UserFacingCliError` in `src/erk/cli/ensure.py`.

```python
# Check error case first and raise
result = ctx.git.remote.push_to_remote(repo.root, "origin", branch)
if isinstance(result, PushError):
    raise UserFacingCliError(result.message)
# Type narrowing: result is now PushResult
```

**Why `UserFacingCliError`:**

- Caught at CLI entry point (`main()`) with consistent error styling
- Exits with code 1 automatically
- One-line pattern replaces verbose `user_output(error) + raise SystemExit(1)`

## Pipeline Discriminated Unions: Structured Error Propagation

Both submit and land pipelines use discriminated unions to thread errors through multi-step operations:

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, SubmitState, SubmitError -->
<!-- Source: src/erk/cli/commands/land_pipeline.py, LandState, LandError -->

See `SubmitError` in `src/erk/cli/commands/pr/submit_pipeline.py` and `LandError` in `src/erk/cli/commands/land_pipeline.py`.

Pipeline steps have signature:

```python
PipelineStep = Callable[[ErkContext, State], State | Error]
```

Each step returns either:

- Updated `State` to pass to next step
- `Error` to short-circuit pipeline

**Why structured error types?**

1. **Phase tracking** — caller knows if error occurred in validation vs execution
2. **Machine-readable `error_type`** — enables specific error handling (e.g., "pr-checks-failing" vs "merge-conflict")
3. **Structured `details: dict[str, str]`** — additional context for debugging (PR number, check names)
4. **Pipeline composition** — uniform signature enables functional composition

**Why `dict[str, str]` for details?** Not `dict[str, Any]` or `dict[str, str] | None`. Every error has details (even if empty `{}`), and string values enable consistent serialization/logging without type uncertainty.

```python
# Pipeline runner pattern
def run_validation_pipeline(ctx: ErkContext, state: State) -> State | Error:
    """Run all validation steps, short-circuit on first error."""
    for step in [resolve_target, validate_checks, check_conflicts, ...]:
        result = step(ctx, state)
        if isinstance(result, Error):
            return result  # Short-circuit
        state = result  # Update state for next step
    return state
```

## Gateway Migration: bool | str → Discriminated Union

The `merge_pr` evolution demonstrates why discriminated unions are better than ad-hoc bool/string patterns:

**Before** (ambiguous return type):

```python
def merge_pr(self, repo_root: Path, pr_number: int, ...) -> bool | str:
    """Returns True on success, error message string on failure."""

# Caller pattern (type-unsafe)
merge_result = ops.github.merge_pr(repo_root, pr_number, ...)
if merge_result is not True:
    error_detail = merge_result if isinstance(merge_result, str) else "Unknown"
    return f"Failed to merge: {error_detail}"
```

**After** (explicit types):

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, MergeResult, MergeError -->

See `MergeResult` and `MergeError` in `packages/erk-shared/src/erk_shared/gateway/github/types.py`.

```python
def merge_pr(self, repo_root: Path, pr_number: int, ...) -> MergeResult | MergeError:
    """Returns MergeResult on success, MergeError on failure."""

# Caller pattern (type-safe)
merge_result = ops.github.merge_pr(repo_root, pr_number, ...)
if isinstance(merge_result, MergeError):
    return LandError(
        phase="execution",
        error_type="merge-failed",
        message=f"Failed to merge PR #{pr_number}\n\n{merge_result.message}",
        details={"pr_number": str(pr_number)}
    )
# Type narrowing: merge_result is now MergeResult
```

**Migration checklist:**

1. Define types in appropriate `types.py` module
2. Update ABC signature
3. Update all 5 implementations (real, fake, dry_run, printing, and any subclass)
4. Update all call sites to use `isinstance()` checks
5. Update tests to check `isinstance(result, ErrorType)`

Incomplete migrations break type safety — mypy won't catch missing checks if you only update the ABC.

## NonIdealState Protocol

<!-- Source: packages/erk-shared/src/erk_shared/non_ideal_state.py, NonIdealState -->

Error types implement the `NonIdealState` protocol. See `packages/erk-shared/src/erk_shared/non_ideal_state.py`.

The protocol requires:

- `error_type` property (read-only, machine-readable classification)
- `message` property (human-readable description)

This enables generic error handling without coupling to specific error types:

```python
def handle_error(result: Any) -> str:
    if isinstance(result, NonIdealState):
        return result.message
    # Handle success case
```

## Design Guidelines

### Error Types Are Frozen Dataclasses

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py, PushError -->

All error types use `@dataclass(frozen=True)` for immutability. See `PushError` in `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py` for the canonical pattern: a single `message: str` field and an `error_type` property returning a kebab-case string like `"push-failed"`.

### Include Domain Context

Error types should carry domain-meaningful fields for caller inspection:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, PRNotFound -->

See `PRNotFound` in `packages/erk-shared/src/erk_shared/gateway/github/types.py`. It carries `pr_number: int | None` (set when looking up by number) and `branch: str | None` (set when looking up by branch), enabling callers to construct better error messages or branch on specific failure modes.

### Naming Conventions

| Convention           | Example                       | When to Use                    |
| -------------------- | ----------------------------- | ------------------------------ |
| `<Operation>Error`   | `SubmitError`, `MergeError`   | Operation failed               |
| `<Resource>NotFound` | `PRNotFound`, `IssueNotFound` | Lookup returned nothing        |
| `<Operation>Result`  | `MergeResult`, `PushResult`   | Operation succeeded            |
| `<Resource>Created`  | `BranchCreated`               | Resource created successfully  |
| `<Resource>Exists`   | `BranchAlreadyExists`         | Resource already exists (LBYL) |

## Comparison with Other Patterns

### vs. Exceptions

| Discriminated Unions        | Exceptions              |
| --------------------------- | ----------------------- |
| Explicit in type signature  | Hidden control flow     |
| Caller must handle          | Can be silently ignored |
| LBYL-compliant              | EAFP approach           |
| IDE shows possible failures | Requires doc reading    |

### vs. None Return

| Discriminated Unions          | Return None          |
| ----------------------------- | -------------------- |
| Preserves error context       | Loses information    |
| Type-specific handling        | Generic "not found"  |
| Multiple error types possible | Single failure state |

### vs. Result[T, E] Generic

Python's union syntax achieves the same goal with less ceremony:

```python
# Python union (what erk uses)
def fetch() -> Data | Error: ...

# Generic Result type (what Rust uses)
def fetch() -> Result[Data, Error]: ...
```

The union syntax is more pythonic and integrates better with isinstance checks and type narrowing.

## When isinstance() Is NOT Required: Plain Optionals

For return types like `T | None`, isinstance() is not needed. A simple `if result is None:` check suffices because None is not a class that could be confused with a success type. The isinstance() requirement applies specifically to discriminated unions where both variants are named types (e.g., `Data | DataNotFound`).

```python
# T | None: simple None check is fine
result = find_next_node(graph, phases)
if result is None:
    return  # No next node

# T | ErrorType: isinstance() required for type narrowing
result = fetch_data()
if isinstance(result, FetchError):
    handle_error(result.message)
    return
# result is now narrowed to T
```

## Anti-Pattern: None-as-Success in Validation Functions

**Anti-pattern:** `validate_thing() -> ErrorType | None` where `None` means success.

This is counterintuitive because `None` typically signals absence or failure, not success. Callers end up writing `if result is not None:` to check for errors, which reads backwards.

```python
# ❌ Anti-pattern: None = success
def validate_slug(slug: str) -> InvalidSlug | None:
    if not valid:
        return InvalidSlug(reason="bad")
    return None  # Success... but None?

# Caller: confusing
error = validate_slug(slug)
if error is not None:  # "if not nothing" = error?
    handle_error(error)
```

**Correct pattern:** Both outcomes are explicit named types.

```python
# ✅ Correct: both outcomes are named types
def validate_slug(slug: str) -> ValidSlug | InvalidSlug:
    if not valid:
        return InvalidSlug(reason="bad")
    return ValidSlug(slug=slug)

# Caller: clear isinstance dispatch
result = validate_slug(slug)
if isinstance(result, InvalidSlug):
    handle_error(result)
# result is now narrowed to ValidSlug
```

This pattern was corrected in `validate_objective_slug()` in `naming.py` — previously returned `InvalidObjectiveSlug | None`, now returns `ValidObjectiveSlug | InvalidObjectiveSlug`.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - 5-place implementation pattern for gateway methods
- [Erk Architecture Patterns](erk-architecture.md) - Broader architectural context for this pattern
