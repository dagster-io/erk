---
title: Result Pattern for Error Handling
read_when:
  - "implementing operations that can fail"
  - "choosing between Result types and exceptions"
  - "understanding LBYL error handling"
---

# Result Pattern for Error Handling

Erk uses **frozen dataclasses** to represent operation results, following a Look-Before-You-Leap (LBYL) pattern that makes success/failure explicit at the type level.

## Core Principle

> **Exceptions are for exceptional conditions. Expected failures are data.**

When an operation has **multiple known failure modes**, use Result types instead of exceptions. The caller gets an explicit success/failure value to inspect before proceeding.

## When to Use Result Types

### ✅ Use Result Types When:

- **Multiple failure modes**: Operation can fail in 3+ distinct ways (auth, validation, network)
- **Caller needs details**: Failure type and context matter for recovery/reporting
- **Expected failures**: Failure is a normal outcome (e.g., PR not found, branch has no commits)
- **LBYL pattern**: Caller checks result type before using data

**Examples**:
- PR submission (auth failed, squash conflict, submit timeout)
- PR landing (not open, merge conflict, parent not trunk)
- Preflight checks (no commits, restack failed, not authenticated)

### ❌ Don't Use Result Types When:

- **Single failure mode**: Operation either succeeds or fails (no distinct failure types)
- **Truly exceptional**: Failure is rare and caller can't recover (e.g., disk full, OOM)
- **Pass-through failures**: Subprocess fails and you just propagate (use exceptions)

**Examples**:
- File I/O (use `Path.read_text()` exceptions)
- Subprocess calls at CLI boundaries (let `CalledProcessError` bubble)
- Assertion failures (programming errors, not runtime failures)

## Pattern Structure

### Success + Error Dataclasses

```python
from dataclasses import dataclass
from typing import Literal

# Define error types as Literal union
PreflightErrorType = Literal[
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_commits",
    "squash_conflict",
]

@dataclass
class PreflightSuccess:
    """Success result from preflight phase."""
    success: Literal[True]  # Discriminator field
    pr_number: int
    pr_url: str
    diff_file: str
    message: str

@dataclass
class PreflightError:
    """Error result from preflight phase."""
    success: Literal[False]  # Discriminator field
    error_type: PreflightErrorType
    message: str  # Human-readable error for CLI
    details: dict[str, str | bool]  # Structured data for debugging
```

### Key Fields

| Field        | Purpose                                  | Required |
| ------------ | ---------------------------------------- | -------- |
| `success`    | Discriminator (True/False)               | Yes      |
| `error_type` | Literal union of failure modes (errors)  | Errors   |
| `message`    | Human-readable description               | Both     |
| `details`    | Structured debug data (dict)             | Errors   |

## Caller Pattern

### Type Narrowing with isinstance

```python
def submit_pr(ctx: ErkContext) -> None:
    result = execute_preflight(ctx)

    # Type narrowing: check discriminator
    if isinstance(result, PreflightError):
        # result is now PreflightError (narrowed)
        click.echo(f"❌ {result.message}")
        if result.error_type == "gt_not_authenticated":
            click.echo("Run: gt auth")
        return

    # result is now PreflightSuccess (narrowed)
    click.echo(f"✅ PR #{result.pr_number} created")
    click.echo(result.pr_url)
```

### Union Return Type

```python
def execute_preflight(
    ctx: ErkContext,
) -> PreflightSuccess | PreflightError:
    # Check auth first (LBYL)
    if not is_gt_authenticated():
        return PreflightError(
            success=False,
            error_type="gt_not_authenticated",
            message="Graphite not authenticated",
            details={"remedy": "gt auth"},
        )

    # Proceed with operation
    ...
    return PreflightSuccess(
        success=True,
        pr_number=123,
        pr_url="https://github.com/...",
        diff_file="/tmp/diff.txt",
        message="PR created successfully",
    )
```

## Anti-Patterns

### ❌ Boolean Success Flags

```python
# BAD: Boolean flag with optional fields
@dataclass
class Result:
    success: bool
    pr_number: int | None = None  # None means error? What error?
    error: str | None = None       # String error? No structure
```

**Problems**:
- Caller must check both `success` and field presence
- No type narrowing (always `int | None`)
- Error details unstructured (string message only)

### ❌ Exception-Heavy Code

```python
# BAD: Using exceptions for expected failures
def submit_pr(ctx: ErkContext) -> int:
    if not is_gt_authenticated():
        raise ValueError("gt not authenticated")  # Expected failure as exception

    if not has_commits():
        raise ValueError("no commits")  # Expected failure as exception

    return create_pr()
```

**Problems**:
- Caller must catch multiple exception types
- No structured error data
- Exceptions used for control flow (slow, hard to test)

### ❌ None for Errors

```python
# BAD: None represents failure
def get_pr_number(branch: str) -> int | None:
    try:
        return find_pr(branch)
    except NotFoundError:
        return None  # Why None? No error details
```

**Problems**:
- Caller can't distinguish failure modes (not found vs auth failed)
- No error message or details
- Silent failures (easy to ignore None)

## Pattern Variations

### Partial Success

Some operations have **partial success** states (e.g., some files processed, others failed):

```python
@dataclass
class BatchResult:
    success: bool  # True if ALL succeeded
    processed: list[str]  # Files processed successfully
    failed: dict[str, str]  # Filename -> error message
    message: str
```

**Use when**: Operation processes multiple items and you want to report partial progress.

### Frozen Dataclasses

For immutability and hashability:

```python
@dataclass(frozen=True)
class PreflightResult:
    success: bool
    pr_number: int
    ...
```

**Use when**: Result is passed through multiple functions and shouldn't be mutated.

### Literal Discriminators

For type narrowing without runtime checks:

```python
@dataclass
class Success:
    success: Literal[True]  # Type system knows success=True
    data: str

@dataclass
class Error:
    success: Literal[False]  # Type system knows success=False
    error: str
```

**Use when**: You want static type checking to enforce success/error handling.

## Implementation Checklist

When adding a new Result type:

1. [ ] Define error types as `Literal` union
2. [ ] Create `SuccessResult` dataclass with `success: Literal[True]`
3. [ ] Create `ErrorResult` dataclass with `success: Literal[False]` and `error_type`
4. [ ] Add `message: str` to both for CLI output
5. [ ] Add `details: dict` to error for structured debugging
6. [ ] Return union type `SuccessResult | ErrorResult` from operation
7. [ ] Use `isinstance()` for type narrowing at call site
8. [ ] Add unit tests for each error type

## Examples in Codebase

### GT Operations

**File**: `packages/erk-shared/src/erk_shared/integrations/gt/types.py`

```python
PreAnalysisErrorType = Literal[
    "gt_not_authenticated",
    "gh_not_authenticated",
    "no_branch",
    "no_commits",
    "squash_conflict",
]

@dataclass
class PreAnalysisResult:
    success: bool
    branch_name: str
    parent_branch: str
    commit_count: int
    squashed: bool
    message: str

@dataclass
class PreAnalysisError:
    success: bool
    error_type: PreAnalysisErrorType
    message: str
    details: dict[str, str | bool]
```

### GitHub Operations

**File**: `packages/erk-shared/src/erk_shared/github/types.py`

```python
@dataclass(frozen=True)
class PRNotFound:
    """Result when a PR lookup finds no matching PR."""
    pr_number: int | None = None  # Set when looking up by number
    branch: str | None = None      # Set when looking up by branch
```

**Usage**:
```python
result = github.get_pr(repo_root, pr_number=123)

if isinstance(result, PRNotFound):
    click.echo(f"PR #{result.pr_number} not found")
    return

# result is now PRDetails (narrowed)
click.echo(f"PR: {result.title}")
```

## Comparison with Other Patterns

### Result Types vs Exceptions

| Aspect          | Result Types                      | Exceptions                    |
| --------------- | --------------------------------- | ----------------------------- |
| **Performance** | Fast (no stack unwinding)         | Slow (stack unwinding)        |
| **Testability** | Easy (return value)               | Harder (catch in test)        |
| **Visibility**  | Explicit in return type           | Implicit (docstring only)     |
| **Recovery**    | Caller gets structured data       | Catch block gets exception    |
| **Type Safety** | Type narrowing with isinstance    | No type narrowing             |

### Result Types vs Optional

| Aspect          | Result Types                      | Optional (T \| None)          |
| --------------- | --------------------------------- | ----------------------------- |
| **Error Info**  | Full context (error_type, details)| No info (just None)           |
| **Multiple**    | Multiple error types              | Single failure mode           |
| **Failure**     | Distinguishable failures          | Generic failure (None)        |

## Related Documentation

- [Two-Phase Operations](two-phase-operations.md) - Preflight/Finalize use Result types
- [Erk Architecture Patterns](erk-architecture.md) - LBYL principle
- [Not-Found Sentinel Pattern](not-found-sentinel.md) - PRNotFound as sentinel
- [Subprocess Wrappers](subprocess-wrappers.md) - When to use exceptions vs Results
