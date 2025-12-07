---
title: GitHub ABC Extension Guide
read_when:
  - "adding new GitHub API methods"
  - "extending GitHub ABC interface"
  - "implementing FakeGitHub or DryRunGitHub"
  - "understanding GitHub integration layer"
---

# GitHub ABC Extension Guide

This document provides a step-by-step workflow for adding new methods to the GitHub integration layer.

## Overview

The GitHub integration uses a 4-layer architecture:

| Layer         | File                | Purpose                                  |
| ------------- | ------------------- | ---------------------------------------- |
| ABC Interface | `github/abc.py`     | Abstract method definitions              |
| Real          | `github/real.py`    | Production implementation via `gh`       |
| Fake          | `github/fake.py`    | In-memory test implementation            |
| DryRun        | `github/dry_run.py` | No-op wrapper for writes, delegate reads |
| Types         | `github/types.py`   | Frozen dataclasses for return values     |

All files are in `packages/erk-shared/src/erk_shared/github/`.

## Step-by-Step Workflow

### Step 1: Define Types (if needed)

If your method returns structured data, add frozen dataclasses to `types.py`:

```python
# github/types.py

@dataclass(frozen=True)
class PRReviewThread:
    """A review thread on a PR.

    Attributes:
        id: GraphQL node ID (needed for resolution mutation)
        path: File path the thread is on
        line: Line number in the file (None for file-level comments)
        is_resolved: Whether the thread has been resolved
        is_outdated: Whether the thread is outdated (code changed)
        comments: Tuple of comments in this thread
    """

    id: str  # GraphQL node ID (needed for resolution mutation)
    path: str
    line: int | None
    is_resolved: bool
    is_outdated: bool
    comments: tuple[PRReviewComment, ...]
```

**Key patterns:**

- Use `@dataclass(frozen=True)` for immutability
- Use `tuple[...]` not `list[...]` for immutable collections
- Document what each field means, especially IDs

### Step 2: Add Abstract Method to ABC

Add the method signature to `abc.py`:

```python
# github/abc.py

@abstractmethod
def get_pr_review_threads(
    self,
    repo_root: Path,
    pr_number: int,
    *,
    include_resolved: bool = False,
) -> list[PRReviewThread]:
    """Get review threads for a pull request.

    Uses GraphQL API (reviewThreads connection) since REST API
    doesn't expose resolution status.

    Args:
        repo_root: Repository root directory
        pr_number: PR number to query
        include_resolved: If True, include resolved threads (default: False)

    Returns:
        List of PRReviewThread sorted by (path, line)
    """
    ...
```

**Key patterns:**

- Document why you're using REST vs GraphQL
- Use keyword-only arguments (`*,`) for boolean flags
- Specify return type sorting/ordering if applicable

### Step 3: Implement in RealGitHub

Add the production implementation to `real.py`:

```python
# github/real.py

def get_pr_review_threads(
    self,
    repo_root: Path,
    pr_number: int,
    *,
    include_resolved: bool = False,
) -> list[PRReviewThread]:
    """Get review threads for a pull request via GraphQL."""
    repo_info = self.get_repo_info(repo_root)

    query = """query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          reviewThreads(first: 100) {
            nodes { id isResolved isOutdated path line ... }
          }
        }
      }
    }"""

    variables = json.dumps({
        "owner": repo_info.owner,
        "repo": repo_info.name,
        "number": pr_number
    })

    cmd = [
        "gh", "api", "graphql",
        "-f", f"query={query}",
        "-f", f"variables={variables}",
    ]
    stdout = execute_gh_command(cmd, repo_root)
    response = json.loads(stdout)

    return self._parse_review_threads_response(response, include_resolved)
```

**Key patterns:**

- Use helper methods for response parsing (`_parse_*`)
- Use `execute_gh_command()` for subprocess execution
- Follow REST vs GraphQL decision guide

### Step 4: Implement in FakeGitHub

Add the fake implementation to `fake.py`:

```python
# github/fake.py

class FakeGitHub(GitHub):
    def __init__(
        self,
        *,
        # ... existing params ...
        pr_review_threads: dict[int, list[PRReviewThread]] | None = None,
    ) -> None:
        # ... existing init ...
        self._pr_review_threads = pr_review_threads or {}
        self._resolved_thread_ids: set[str] = set()

    def get_pr_review_threads(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        include_resolved: bool = False,
    ) -> list[PRReviewThread]:
        """Return pre-configured review threads for testing."""
        threads = self._pr_review_threads.get(pr_number, [])
        if include_resolved:
            return threads
        return [t for t in threads if not t.is_resolved]
```

**Key patterns:**

- Accept test data via constructor (`__init__`)
- Store state in private attributes (`self._*`)
- Track mutations in lists for test assertions (`self._resolved_*`)

### Step 5: Implement in DryRunGitHub

Add to `dry_run.py` - delegate reads, no-op writes:

```python
# github/dry_run.py

def get_pr_review_threads(
    self,
    repo_root: Path,
    pr_number: int,
    *,
    include_resolved: bool = False,
) -> list[PRReviewThread]:
    """Delegate read operation to wrapped implementation."""
    return self._wrapped.get_pr_review_threads(
        repo_root, pr_number, include_resolved=include_resolved
    )

def resolve_review_thread(
    self,
    repo_root: Path,
    thread_id: str,
) -> bool:
    """No-op for resolving review thread in dry-run mode."""
    return True  # Pretend success
```

**Key patterns:**

- Read operations: delegate to `self._wrapped`
- Write operations: return success without executing

### Step 6: Update Imports

If you added new types, ensure they're imported where needed:

```python
# In abc.py, real.py, fake.py, dry_run.py
from erk_shared.github.types import (
    # ... existing imports ...
    PRReviewThread,
)
```

### Step 7: Write Tests

Write tests using `FakeGitHub`:

```python
# tests/unit/test_pr_review_threads.py

def test_get_pr_review_threads_filters_resolved() -> None:
    """Test that resolved threads are filtered by default."""
    threads = [
        PRReviewThread(id="1", path="a.py", line=1, is_resolved=False, ...),
        PRReviewThread(id="2", path="b.py", line=2, is_resolved=True, ...),
    ]
    github = FakeGitHub(pr_review_threads={123: threads})

    result = github.get_pr_review_threads(Path("/repo"), 123)

    assert len(result) == 1
    assert result[0].id == "1"
```

## Checklist

Use this checklist when adding a new GitHub method:

- [ ] **Types**: Add frozen dataclass to `types.py` if returning structured data
- [ ] **ABC**: Add abstract method with docstring explaining REST vs GraphQL choice
- [ ] **Real**: Implement using `gh api` (REST) or `gh api graphql` (GraphQL)
- [ ] **Fake**: Add constructor parameter and return pre-configured data
- [ ] **DryRun**: Delegate reads to wrapped, no-op writes
- [ ] **Imports**: Update imports in all affected files
- [ ] **Tests**: Write unit tests using FakeGitHub

## Common Patterns

### Read vs Write Classification

| Type  | DryRun Behavior | Examples                           |
| ----- | --------------- | ---------------------------------- |
| Read  | Delegate        | `get_pr()`, `list_workflow_runs()` |
| Write | No-op           | `merge_pr()`, `update_pr_body()`   |

### Mutation Tracking in FakeGitHub

For write operations, track calls for test assertions:

```python
# In __init__
self._resolved_thread_ids: set[str] = set()

# In method
def resolve_review_thread(self, repo_root: Path, thread_id: str) -> bool:
    self._resolved_thread_ids.add(thread_id)
    return True

# Expose for tests
@property
def resolved_thread_ids(self) -> set[str]:
    return self._resolved_thread_ids
```

### Error Handling

- **RealGitHub**: Use try/except at error boundaries, document in docstring
- **FakeGitHub**: Return configured success/failure state
- **DryRunGitHub**: Return success values without executing

## Related Topics

- [GitHub Interface Patterns](github-interface-patterns.md) - REST vs GraphQL API patterns
- [Protocol vs ABC](protocol-vs-abc.md) - When to use ABC vs Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - Running `gh` commands safely
