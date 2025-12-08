---
title: NonIdealState Pattern
read_when:
  - "handling operations that can fail gracefully"
  - "returning errors without throwing exceptions"
  - "type narrowing for error handling"
  - "working with GitHubChecks class"
---

# NonIdealState Pattern

Pattern for handling operations that can fail gracefully by returning `T | NonIdealState` instead of throwing exceptions.

## Overview

The NonIdealState pattern separates **error detection** from **error handling**:

- Operations return `T | NonIdealState` (never throw)
- Callers inspect results and decide how to handle errors
- Type narrowing works naturally with `isinstance()` checks

## Core Types

**Location**: `packages/erk-shared/src/erk_shared/non_ideal_state.py`

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class NonIdealState(Protocol):
    """Marker interface for non-ideal states."""
    @property
    def error_type(self) -> str: ...

    @property
    def message(self) -> str: ...
```

**Concrete implementations**:
- `BranchDetectionFailed` - Branch could not be detected
- `NoPRForBranch` - No PR exists for the specified branch
- `PRNotFoundError` - PR with specified number does not exist
- `GitHubAPIFailed` - GitHub API call failed

## Usage Pattern

```python
from erk_shared.non_ideal_state import NonIdealState, BranchDetectionFailed

# Function returns T | NonIdealState
result = GitHubChecks.branch(get_current_branch())

# Check and handle error
if isinstance(result, BranchDetectionFailed):
    # Handle error case
    ...
branch = result  # Type narrowed to str
```

## Integration with Ensure Class

For erk CLI commands, use `Ensure` methods for type narrowing with styled error output:

```python
from erk.cli.ensure import Ensure
from erk_shared.non_ideal_state import GitHubChecks

# Exits with styled error + code 1 if NonIdealState
branch = Ensure.branch(GitHubChecks.branch(raw_branch))
pr = Ensure.pr(GitHubChecks.pr_for_branch(github, repo_root, branch))
```

## When to Use

- Operations that can fail due to external state (GitHub API, git state)
- When callers need flexibility in how to handle errors
- When you want type narrowing to work naturally

## When NOT to Use

- Programming errors (use exceptions)
- Validation that should fail fast (use `Ensure.invariant()`)
- Simple boolean checks
