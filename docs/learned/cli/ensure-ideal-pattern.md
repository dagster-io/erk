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
---

# EnsureIdeal Pattern for Type Narrowing

The `EnsureIdeal` class provides type-safe narrowing for discriminated union returns from gateway operations. It complements `Ensure` (invariant checks) by handling expected failure cases from I/O operations.

## Semantic Distinction

| Class        | Purpose                        | Use Case                                            | Example                                                      |
| ------------ | ------------------------------ | --------------------------------------------------- | ------------------------------------------------------------ |
| `Ensure`     | Invariant/precondition checks  | Asserting program invariants, validating arguments  | `Ensure.invariant(len(args) == 1, "Expected 1 argument")`    |
| `EnsureIdeal`| Type narrowing from unions     | Handling operations that return `T \| NonIdealState`| `pr = EnsureIdeal.unwrap_pr(github.get_pr(...), "PR not found")` |

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

## Available Methods

### 1. `ideal_state(result: T | NonIdealState) -> T`

Generic method for any type implementing `NonIdealState` protocol.

```python
from erk_shared.non_ideal_state import GitHubChecks

branch = EnsureIdeal.ideal_state(GitHubChecks.branch(raw_branch))
# Type narrowed: str | BranchDetectionFailed → str
```

### 2. `branch(result: str | BranchDetectionFailed) -> str`

Specialized for branch detection.

```python
current_branch = EnsureIdeal.branch(
    GitHubChecks.branch(ops.git.get_current_branch(repo.root))
)
```

**Input**: `str | BranchDetectionFailed`
**Output**: `str`

### 3. `pr(result: PRDetails | NoPRForBranch | PRNotFoundError) -> PRDetails`

Specialized for PR lookups that return `NonIdealState` error types.

```python
pr_details = EnsureIdeal.pr(ctx.github.get_pr_for_branch(...))
```

**Input**: `PRDetails | NoPRForBranch | PRNotFoundError`
**Output**: `PRDetails`

### 4. `unwrap_pr(result: PRDetails | PRNotFound, message: str) -> PRDetails`

Specialized for PR lookups that return sentinel `PRNotFound` (not `NonIdealState`).

**Unlike `EnsureIdeal.pr()`**, this works with `PRNotFound` from `gateway/github/types.py` which lacks a built-in message, so the caller must provide one.

```python
pr_details = EnsureIdeal.unwrap_pr(
    ctx.github.get_pr_for_branch(main_repo_root, current_branch),
    f"No pull request found for branch '{current_branch}'.",
)
```

**Input**: `PRDetails | PRNotFound`, custom message
**Output**: `PRDetails`

**Why two PR methods?**: `PRNotFound` is a sentinel type (frozen dataclass with `pr_number: None`), while `NoPRForBranch`/`PRNotFoundError` implement `NonIdealState` with built-in messages.

### 5. `comments(result: list | GitHubAPIFailed) -> list`

Specialized for GitHub API operations returning comment lists.

```python
comments = EnsureIdeal.comments(ctx.github.get_comments(...))
```

**Input**: `list | GitHubAPIFailed`
**Output**: `list`

### 6. `void_op(result: None | GitHubAPIFailed) -> None`

Specialized for void operations (mutations with no return value).

```python
EnsureIdeal.void_op(ctx.github.post_comment(...))
```

**Input**: `None | GitHubAPIFailed`
**Output**: `None`

### 7. `session(result: T | SessionNotFound) -> T`

Specialized for session lookups.

```python
session_data = EnsureIdeal.session(session_store.lookup(...))
```

**Input**: `T | SessionNotFound`
**Output**: `T`

## Code Examples

### Example 1: Landing a PR (from `land_cmd.py`)

```python
# Gateway returns PRDetails | PRNotFound
pr_details = EnsureIdeal.unwrap_pr(
    ctx.github.get_pr_for_branch(main_repo_root, current_branch),
    f"No pull request found for branch '{current_branch}'.",
)
# Type narrowed: pr_details is now PRDetails

# Can safely access PRDetails fields
print(f"Landing PR #{pr_details.number}: {pr_details.title}")
```

### Example 2: Branch Detection (from `show_cmd.py`)

```python
# Git operation returns str | BranchDetectionFailed
raw_branch = ops.git.get_current_branch(repo.root)
current_branch = EnsureIdeal.branch(GitHubChecks.branch(raw_branch))
# Type narrowed: current_branch is now str

# Can safely use as string
print(f"Current branch: {current_branch}")
```

### Example 3: Generic Non-Ideal State

```python
# Any operation returning T | NonIdealState
result = EnsureIdeal.ideal_state(some_operation())
# Type narrowed: result is now T (not T | NonIdealState)
```

## Implementation Details

All methods follow the same pattern:

1. Check if result is the error type using `isinstance()`
2. If error: output styled error message and `raise SystemExit(1)`
3. If success: return the value (now type-narrowed)

**Error Format**: All errors use `click.style("Error: ", fg="red")` prefix for consistency.

**Exit Code**: Always 1 for user-facing errors (non-ideal states are expected failures, not bugs).

## When to Add New Methods

Add a new `EnsureIdeal` method when:

1. A gateway operation returns a new discriminated union type
2. The error type implements `NonIdealState` OR has a `message` field
3. The union is used in multiple CLI commands (reusable pattern)

**Example**: If adding `get_workflow_run() -> WorkflowRun | RunNotFound`, add:

```python
@staticmethod
def workflow_run(result: WorkflowRun | RunNotFound) -> WorkflowRun:
    if isinstance(result, RunNotFound):
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1)
    return result
```

## Related Documentation

- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Pattern for defining discriminated union types
- [Two-Phase Validation Model](two-phase-validation-model.md) - CLI validation architecture
- [CLI Error Handling](../testing/cli-error-handling.md) - Ensure class for invariant checks
