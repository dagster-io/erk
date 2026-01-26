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

## Related Documentation

- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Specific pattern for lookup operations
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Gateways often use this pattern
