---
title: Discriminated Union Error Handling
last_audited: "2026-02-03"
audit_result: edited
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
---

# Discriminated Union Error Handling

A LBYL-compliant pattern for handling expected failures without exceptions. Return types are unions of success and error types, allowing callers to use `isinstance()` checks.

## Source References

Examples in this document reference actual type definitions. See canonical sources:

- **GitHub operations**: `packages/erk-shared/src/erk_shared/gateway/github/types.py`
- **Git branch operations**: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py`
- **Git remote operations**: `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`
- **NonIdealState protocol**: `packages/erk-shared/src/erk_shared/non_ideal_state.py`

## The Pattern

Instead of:

```python
def fetch_data() -> Data:
    """Raises DataNotFoundError if not found."""
    ...
```

Use:

```python
def fetch_data() -> Data | DataNotFound:
    """Returns DataNotFound if not found."""
    ...
```

## Core Principle

Operations that can fail for **expected, recoverable reasons** return a discriminated union:

```python
Result = SuccessType | ErrorType
```

Callers use `isinstance()` to check which variant they received.

## When to Use

The key question is: **does the caller continue after the failure?**

Use discriminated unions when:

- The caller has **branching business logic** that continues after the failure
- The error type carries **domain-meaningful structure** (e.g., `pr_number`, `branch_name`) that callers inspect
- Multiple distinct error variants require **different handling paths**

Use exceptions when:

- All callers **terminate the operation** on failure — the error just surfaces as a message
- The error type is a **structureless `message: str` wrapper** with no domain variants
- The error propagates to a **generic error boundary** (CLI handler, top-level catch)
- No caller branches on error content beyond extracting the message

### When Exceptions Are Preferred: Worktree Operations

Worktree add/remove failures are _expected_ — but they're still better as exceptions because no caller does anything meaningful with the error beyond terminating:

```python
# All callers do the same thing: extract message and stop
try:
    git.worktree.add_worktree(repo_root, path, branch)
except RuntimeError as e:
    raise UserFacingCliError(str(e))
```

The exception pattern is simpler here: no caller inspects the error type, no caller branches on the error content, and every caller terminates identically.

Contrast with `submit_branch` and `create_branch`, where callers _do_ branch:

```python
result = branch_mgr.submit_branch(...)
if isinstance(result, BranchAlreadyExists):
    # Continue: offer to check out the existing branch
    handle_existing_branch(result.branch_name)
elif isinstance(result, SubmitError):
    # Continue: retry with different options
    retry_submit(result)

# Git branch creation
result = git_ops.create_branch(cwd, "feature", "main", force=False)
if isinstance(result, BranchAlreadyExists):
    # Continue: use existing branch or prompt for new name
    logger.info(f"Branch {result.branch_name} already exists, using it")
    return result.branch_name

# Type narrowing: result is now BranchCreated (empty marker type)
```

## Concrete Examples

### Example 1: `merge_pr` - `bool | str` to Discriminated Union

**Before** (ambiguous return type):

```python
# ABC definition
def merge_pr(self, repo_root: Path, pr_number: int, ...) -> bool | str:
    """Returns True on success, error message string on failure."""

# Caller pattern (type-unsafe)
merge_result = ops.github.merge_pr(repo_root, pr_number, ...)
if merge_result is not True:
    error_detail = merge_result if isinstance(merge_result, str) else "Unknown error"
    return f"Failed to merge: {error_detail}"
```

**After** (explicit types):

See `MergeResult` and `MergeError` type definitions in `packages/erk-shared/src/erk_shared/gateway/github/types.py`.

Example caller pattern:

```python
# ABC definition
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

**Migration Checklist**:

1. Define types in appropriate `types.py` module
2. Update ABC signature
3. Update all 5 implementations:
   - `real.py` - Return ErrorType for subprocess/API errors
   - `fake.py` - Return union types in test implementation
   - `dry_run.py` - Return SuccessType for no-op
   - `printing.py` - Update signature
4. Update all call sites
5. Update tests to check `isinstance(result, ErrorType)`

### Example 2: BranchCreated/BranchAlreadyExists - create_branch Gateway

See `BranchCreated` and `BranchAlreadyExists` type definitions in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/types.py`.

ABC signature:

```python
# ABC definition (gateway/git/branch_ops/abc.py)
def create_branch(self, cwd: Path, branch_name: str, start_point: str, *, force: bool) -> BranchCreated | BranchAlreadyExists:
    """Returns BranchCreated on success, BranchAlreadyExists if branch exists."""
```

Note: `BranchCreated` is an empty marker dataclass (no fields). `BranchAlreadyExists` carries `branch_name: str` and `message: str`.

**Call site pattern**:

```python
result = git_ops.create_branch(repo_root, name, "main", force=False)
if isinstance(result, BranchAlreadyExists):
    # Continue: use existing branch or prompt for new name
    logger.info(f"Branch {result.branch_name} already exists")
    return result.branch_name

# Type narrowing: result is now BranchCreated
```

### Example 3: LandError - Structured Pipeline Error

The land command pipeline uses a structured error type that extends the discriminated union pattern with pipeline-specific metadata.

**LandError definition** (`land_pipeline.py`):

```python
@dataclass(frozen=True)
class LandError:
    """Error result from land pipeline."""
    phase: str              # Which pipeline stage failed ('validation' or 'execution')
    error_type: str         # Machine-readable error classification
    message: str            # Human-readable description
    details: dict[str, str] # Structured context (note: NOT dict[str, Any] | None)
```

**Pipeline step signature**:

```python
LandStep = Callable[[ErkContext, LandState], LandState | LandError]
```

Each pipeline step returns either:

- Updated `LandState` to pass to next step
- `LandError` to short-circuit pipeline and propagate error to caller

**Consumer pattern in validation pipeline**:

```python
def run_validation_pipeline(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Run all validation steps, short-circuit on first error."""
    for step in [resolve_target, validate_checks, check_no_conflicts, ...]:
        result = step(ctx, state)
        if isinstance(result, LandError):
            return result  # Short-circuit pipeline
        state = result  # Update state for next step
    return state
```

**Benefits of structured error**:

1. **Phase tracking**: Caller knows if error occurred in validation vs execution
2. **Machine-readable error_type**: Enables specific error handling (e.g., "pr-checks-failing" vs "merge-conflict")
3. **Structured details**: Dict for additional context (PR number, check names, etc.)
4. **Pipeline composition**: Each step has same signature, enabling functional composition

## Consumer Pattern

### CLI Layer Pattern

For CLI commands consuming discriminated unions, use `UserFacingCliError`:

```python
from erk.cli.ensure import UserFacingCliError

# Check error case first and raise UserFacingCliError
push_result = ctx.git.remote.push_to_remote(repo.root, "origin", branch)
if isinstance(push_result, PushError):
    raise UserFacingCliError(push_result.message)

# Type narrowing: push_result is now PushResult
user_output(click.style("✓", fg="green") + " Branch pushed successfully")
```

**Why UserFacingCliError:**

- Caught at CLI entry point (`main()`) with consistent error styling
- Exits with code 1 automatically
- One-line pattern: `raise UserFacingCliError(error.message)`
- Replaces verbose two-line pattern: `user_output(error) + raise SystemExit(1)`

### Library Layer Pattern

For library code (non-CLI), check the error case and return or propagate:

```python
result = some_operation(...)

if isinstance(result, OperationError):
    return result  # Propagate error to caller

# Type narrowing: result is now SuccessType
return process_result(result)
```

## Design Guidelines

### Error Types Should Be Frozen Dataclasses

```python
@dataclass(frozen=True)
class MyOperationError:
    message: str
    context: str | None = None  # Optional context fields
```

### Include Useful Context

Error types should include enough information for callers to handle them appropriately:

```python
@dataclass(frozen=True)
class PRNotFound:
    pr_number: int | None = None  # Set when looking up by number
    branch: str | None = None     # Set when looking up by branch
```

### Naming Conventions

| Convention           | Example                       |
| -------------------- | ----------------------------- |
| `<Operation>Error`   | `SubmitError`, `MergeError`   |
| `<Resource>NotFound` | `PRNotFound`, `IssueNotFound` |
| `<Operation>Result`  | `MergeResult`, `PushResult`   |
| `<Resource>Created`  | `BranchCreated`               |
| `<Resource>Exists`   | `BranchAlreadyExists`         |

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

Some languages use `Result[T, E]` generics. Python's union syntax achieves the same with less ceremony:

```python
# Instead of Result[Data, Error]
def fetch() -> Data | Error:
    ...
```

## Gateway Discriminated Unions: PushResult/PushError

Git remote operations return discriminated unions at the gateway boundary:

```python
@dataclass(frozen=True)
class PushResult:
    """Success: push completed."""

@dataclass(frozen=True)
class PushError:
    message: str

    @property
    def error_type(self) -> str:
        ...

# Return type
def push_to_remote(...) -> PushResult | PushError: ...
def pull_rebase(...) -> PullRebaseResult | PullRebaseError: ...
```

Success variants are empty marker types. Error variants contain `message` and a read-only `error_type` property for classification. See `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`.

## Pipeline Discriminated Unions: SubmitState/SubmitError

The submit pipeline threads an immutable `SubmitState` through 8 steps, where each step returns `SubmitState | SubmitError`:

```python
@dataclass(frozen=True)
class SubmitError:
    phase: str       # Which pipeline step failed
    error_type: str  # Machine-readable error classification
    message: str     # Human-readable description
    details: dict[str, str]
```

The pipeline runner short-circuits on the first `isinstance(result, SubmitError)` check. See `src/erk/cli/commands/pr/submit_pipeline.py`.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Gateways often use this pattern
- **NonIdealState protocol**: `packages/erk-shared/src/erk_shared/non_ideal_state.py` - Protocol for error types
