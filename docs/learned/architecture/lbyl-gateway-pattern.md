---
title: LBYL Gateway Pattern
read_when:
  - "implementing existence checks before gateway operations"
  - "adding LBYL validation to CLI commands"
  - "understanding issue_exists() and similar methods"
---

# LBYL Gateway Pattern

Look Before You Leap (LBYL) is a defensive programming pattern where you check preconditions before performing operations. For gateway methods, this means checking resource existence before fetching or mutating.

## The Problem

Gateway `get_X()` methods may return sentinels (e.g., `PRNotFound`) or raise exceptions when resources don't exist. Without existence checks, callers must handle these cases inline, leading to:

- Cryptic error messages ("Unexpected response format")
- Complex control flow with sentinel checks
- Repeated validation logic across callers

## The Solution: Existence Methods

Add lightweight existence-check methods to gateway ABCs:

```python
class GitHubIssues(ABC):
    @abstractmethod
    def issue_exists(self, repo_root: Path, number: int) -> bool:
        """Check if an issue exists (read-only)."""
        ...

    @abstractmethod
    def get_issue(self, repo_root: Path, number: int) -> IssueInfo:
        """Fetch issue details. Raises if not found."""
        ...
```

## Implementation Pattern

### Real Gateway

Implement a lightweight check that avoids fetching the full resource:

```python
# real.py
def issue_exists(self, repo_root: Path, number: int) -> bool:
    cmd = ["gh", "issue", "view", str(number), "--json", "number"]
    result = subprocess.run(cmd, cwd=repo_root, capture_output=True)
    return result.returncode == 0
```

### Fake Gateway

Return based on test data:

```python
# fake.py
def issue_exists(self, repo_root: Path, number: int) -> bool:
    return any(issue.number == number for issue in self._issues)
```

### Dry-Run and Printing Gateways

Delegate to wrapped (existence checks are read-only):

```python
# dry_run.py / printing.py
def issue_exists(self, repo_root: Path, number: int) -> bool:
    return self._wrapped.issue_exists(repo_root, number)
```

## Usage in CLI Commands

The LBYL pattern enables clear, early validation:

```python
from erk.cli.ensure import Ensure

def my_command(ctx: ErkContext, issue_number: int) -> None:
    # LBYL: Check existence before operating
    if not ctx.github.issues.issue_exists(repo.root, issue_number):
        user_output(f"Error: Issue #{issue_number} not found")
        raise SystemExit(1)

    # Safe to fetch - we know it exists
    issue = ctx.github.issues.get_issue(repo.root, issue_number)

    # Additional validation
    if "erk-objective" not in issue.labels:
        user_output(f"Error: Issue #{issue_number} is not an erk-objective")
        raise SystemExit(1)
```

## When to Use LBYL

**Use LBYL when:**

- Resource existence is the first validation step
- Error messages should be user-friendly
- You need to check multiple conditions on the resource
- The existence check is cheap relative to full fetch

**Skip LBYL when:**

- You need the resource data anyway (just handle NotFound inline)
- The operation is *already* idempotent (e.g., `git fetch` always succeeds)
- Performance is critical and you want to avoid extra API calls

**Use LBYL to *implement* idempotency when:**

- The operation would fail on missing resources (e.g., `git branch -D` fails if branch doesn't exist)
- You want to make it idempotent by checking first and returning early if missing
- Example: `delete_branch()` checks if branch exists, returns early if not, proceeds with deletion if yes

**Decision tree:**

1. Does the operation fail if resource is missing? **NO** → Skip LBYL (already idempotent)
2. Does the operation fail if resource is missing? **YES** → Should it be idempotent?
   - **YES** → Use LBYL to check existence and return early
   - **NO** → Let it fail (error is appropriate)

## Existing Implementations

| Gateway      | Method         | Location                                            |
| ------------ | -------------- | --------------------------------------------------- |
| GitHubIssues | `issue_exists` | `packages/erk-shared/src/erk_shared/github/issues/` |

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full gateway pattern
- [Erk Architecture Patterns](erk-architecture.md) - LBYL philosophy
- [Objective Commands](../cli/objective-commands.md) - Example usage
