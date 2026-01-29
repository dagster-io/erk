---
title: Discriminated Union Error Handling
read_when:
  - "designing return types for operations that may fail"
  - "implementing T | ErrorType patterns"
  - "handling errors without exceptions"
  - "working with GeneratedPlan, PlanGenerationError, or similar types"
tripwires:
  - action: "raising exceptions for expected failure cases in business logic"
    warning: "Use discriminated unions (T | ErrorType) instead. Exceptions are for truly exceptional conditions, not business logic failures."
---

# Discriminated Union Error Handling

A LBYL-compliant pattern for handling expected failures without exceptions. Return types are unions of success and error types, allowing callers to use `isinstance()` checks.

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

Use discriminated unions when:

- Failure is a **normal, expected case** (not exceptional)
- Callers need to handle the failure case explicitly
- You want type-safe error handling with IDE support
- You're following LBYL principles

Use exceptions when:

- Failure indicates a **programming error** or system failure
- The error should propagate up the call stack
- Recovery at the immediate call site is unlikely

## Examples in the Codebase

### Plan Generation

```python
@dataclass(frozen=True)
class GeneratedPlan:
    content: str
    title: str

@dataclass(frozen=True)
class PlanGenerationError:
    message: str

def generate_plan_for_step(...) -> GeneratedPlan | PlanGenerationError:
    result = executor.execute_prompt(prompt, model="haiku")
    if not result.success:
        return PlanGenerationError(message=result.error or "Unknown error")
    return GeneratedPlan(content=..., title=...)
```

### Roadmap Updates

```python
@dataclass(frozen=True)
class RoadmapUpdateResult:
    success: bool
    updated_body: str | None
    error: str | None

def update_roadmap_with_plan(...) -> RoadmapUpdateResult:
    if not result.success:
        return RoadmapUpdateResult(success=False, updated_body=None, error=...)
    return RoadmapUpdateResult(success=True, updated_body=..., error=None)
```

### Next Step Inference

```python
@dataclass(frozen=True)
class NextStepResult:
    has_next_step: bool
    step_id: str | None
    step_description: str | None
    ...

@dataclass(frozen=True)
class InferenceError:
    message: str

def infer_next_step(...) -> NextStepResult | InferenceError:
    ...
```

## Consumer Pattern

Always check the error case first:

```python
result = generate_plan_for_step(executor, ...)

if isinstance(result, PlanGenerationError):
    click.echo(f"Error: {result.message}")
    return 1

# Type narrowing: result is now GeneratedPlan
click.echo(f"Created plan: {result.title}")
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
    branch: str | None = None    # What was looked up
    pr_number: int | None = None
```

### Naming Conventions

| Convention           | Example                                   |
| -------------------- | ----------------------------------------- |
| `<Operation>Error`   | `PlanGenerationError`                     |
| `<Resource>NotFound` | `PRNotFound`, `ResourceNotFound`          |
| `<Operation>Result`  | `RoadmapUpdateResult` (with success bool) |

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

## Exec Command Error Pattern

Exec commands (scripts in `src/erk/cli/commands/exec/scripts/`) MUST use frozen dataclass discriminated unions for their JSON output. This ensures callers get a clear contract for success and error cases.

### The Pattern

Exec commands use a three-layer approach:

1. **Custom exception type** for internal error propagation
2. **Frozen dataclass discriminated unions** for the JSON contract (Success | Error)
3. **CLI boundary conversion** that catches exceptions and converts to JSON

### Implementation Template

```python
# 1. Define the success and error dataclasses
@dataclass(frozen=True)
class MyCommandSuccess:
    """Success response for my-command."""
    success: bool
    result_field1: str
    result_field2: int
    # Include all relevant success data

@dataclass(frozen=True)
class MyCommandError:
    """Error response for my-command."""
    success: bool
    error: str      # Machine-readable error type
    message: str    # Human-readable error message

# 2. Define custom exception for internal use
class MyCommandException(Exception):
    """Exception raised during my-command execution."""

    def __init__(self, error: str, message: str) -> None:
        super().__init__(message)
        self.error = error
        self.message = message

# 3. Implementation function raises exceptions
def _my_command_impl(...) -> MyCommandSuccess:
    if something_wrong:
        raise MyCommandException(
            error="resource-not-found",
            message="The resource could not be found"
        )

    return MyCommandSuccess(
        success=True,
        result_field1="value",
        result_field2=42
    )

# 4. CLI command converts exceptions to JSON at boundary
@click.command()
def my_command(...) -> None:
    try:
        result = _my_command_impl(...)
        click.echo(json.dumps(asdict(result)))
    except MyCommandException as e:
        error = MyCommandError(
            success=False,
            error=e.error,
            message=e.message
        )
        click.echo(json.dumps(asdict(error)))
        raise SystemExit(1) from None
```

### Why This Hybrid Approach?

This pattern combines **exceptions internally** with **discriminated unions externally**:

- **Internal exceptions**: Simplify control flow within implementation (can propagate through helper functions)
- **External discriminated unions**: Provide clear JSON contract for callers (LBYL-compliant)
- **CLI boundary conversion**: Single point where exceptions become JSON errors

Benefits:

1. **Internal code simplicity**: Helper functions can raise exceptions without needing to thread error types through
2. **Clear JSON contract**: Callers get typed `Success | Error` discriminated union via JSON
3. **LBYL for callers**: Calling code can check `success` field before accessing result fields
4. **Type safety**: Both success and error cases are frozen dataclasses with explicit fields

### Exemplar: plan_review_complete

The `plan_review_complete.py` script demonstrates this pattern:

**Success fields:**

```python
@dataclass(frozen=True)
class PlanReviewCompleteSuccess:
    success: bool
    issue_number: int
    pr_number: int
    branch_name: str
    branch_deleted: bool
    local_branch_deleted: bool
```

**Error fields:**

```python
@dataclass(frozen=True)
class PlanReviewCompleteError:
    success: bool
    error: str
    message: str
```

**CLI boundary conversion** (lines 183-191):

```python
try:
    result = _plan_review_complete_impl(...)
    click.echo(json.dumps(asdict(result)))
except PlanReviewCompleteException as e:
    error_response = PlanReviewCompleteError(
        success=False,
        error=e.error,
        message=e.message,
    )
    click.echo(json.dumps(asdict(error_response)))
    raise SystemExit(1) from None
```

### Success Field Guidelines

Success dataclasses should include all relevant data the caller needs:

- **Resource identifiers**: issue_number, pr_number, branch_name
- **Operation results**: branch_deleted, local_branch_deleted
- **Generated content**: URLs, file paths, computed values

The `success: bool` field allows generic checking before parsing specific fields.

### Error Field Guidelines

Error dataclasses should include:

- **success: bool**: Always `False`, allows generic success checking
- **error: str**: Machine-readable error type (e.g., "pr-not-found", "branch-exists")
- **message: str**: Human-readable error message for display
- **Optional context fields**: Additional data for specific error types

### Related Exec Commands

This pattern is used in:

- `plan_review_complete.py` (lines 37-64, 183-191)
- `plan_create_review_pr.py` (lines 32-57)
- Other exec scripts that need structured JSON output

## Related Documentation

- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Specific pattern for lookup operations
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Gateways often use this pattern
