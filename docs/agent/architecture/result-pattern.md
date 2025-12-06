---
title: Result Pattern for Error Handling
read_when:
  - "designing functions that can partially succeed"
  - "structured error returns"
  - "result dataclasses"
---

# Result Pattern for Error Handling

When business logic functions need to report success/failure states without raising exceptions, use frozen dataclasses with a consistent structure.

## When to Use

- Functions that can partially succeed (e.g., created issue but comment failed)
- Functions called from multiple contexts (CLI, kit commands, other modules)
- When callers need structured error information, not just exception messages

## Pattern Structure

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OperationResult:
    """Result of performing an operation.

    Attributes:
        success: Whether the entire operation completed successfully
        error: Error message if failed, None if success
        # ... operation-specific fields
    """
    success: bool
    error: str | None
    # Additional fields for partial success info
```

## Key Principles

1. **Frozen dataclass**: Immutable results prevent accidental modification
2. **`success` field**: Boolean indicating complete success
3. **`error` field**: Human-readable error message (None when success=True)
4. **Partial success fields**: Include identifiers of partially-created resources

## Example: CreatePlanIssueResult

```python
@dataclass(frozen=True)
class CreatePlanIssueResult:
    success: bool
    issue_number: int | None  # May be set even on failure (partial success)
    issue_url: str | None
    title: str
    error: str | None
```

## Caller Pattern

```python
result = create_plan_issue(github_issues, repo_root, content)

if not result.success:
    if result.issue_number is not None:
        # Partial success - issue created but something else failed
        handle_partial_success(result)
    else:
        # Complete failure
        handle_failure(result.error)
    return

# Full success
use_result(result.issue_number, result.issue_url)
```

## Anti-Patterns

**Don't raise exceptions for expected failure modes**

```python
# Wrong - forces callers to catch exceptions
def create_issue(...) -> IssueInfo:
    if not authenticated:
        raise RuntimeError("Not authenticated")
```

**Return result object instead**

```python
# Correct - structured error handling
def create_issue(...) -> CreateIssueResult:
    if not authenticated:
        return CreateIssueResult(
            success=False,
            error="Not authenticated",
            ...
        )
```

## See Also

- [LBYL Exception Handling](../dignified-python/dignified-python-core.md#exception-handling)
- [CreatePlanIssueResult](../../packages/erk-shared/src/erk_shared/github/plan_issues.py)
