---
title: GitHub ABC Extension Workflow
read_when:
  - "adding new GitHub API methods to erk"
  - "extending GitHub integration layer"
  - "implementing new GitHub functionality across all layers"
---

# GitHub ABC Extension Workflow

This document provides a step-by-step workflow for adding new GitHub API capabilities to the erk codebase. The GitHub integration uses a layered architecture with ABC (Abstract Base Class) interfaces.

## Architecture Overview

The GitHub integration has 4 layers:

| Layer       | File                 | Purpose                                          |
| ----------- | -------------------- | ------------------------------------------------ |
| ABC         | `github/abc.py`      | Abstract interface defining the contract         |
| Real        | `github/real.py`     | Production implementation (calls `gh` CLI)       |
| Fake        | `github/fake.py`     | Test implementation (constructor-injected)       |
| DryRun      | `github/dry_run.py`  | Dry-run wrapper (delegates reads, no-ops writes) |
| Types       | `github/types.py`    | Data types (frozen dataclasses)                  |
| **init**.py | `github/__init__.py` | Public API exports                               |

All code lives in `packages/erk-shared/src/erk_shared/github/`.

## Step-by-Step Workflow

### Step 1: Add Abstract Method to ABC

Define the method signature and docstring in `abc.py`.

**Pattern:**

```python
from abc import ABC, abstractmethod
from pathlib import Path

class GitHub(ABC):
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
            repo_root: Repository root (for gh CLI context)
            pr_number: PR number
            include_resolved: Whether to include resolved threads

        Returns:
            List of review threads sorted by (path, line)
        """
```

**Key points:**

- Use keyword-only arguments (after `*`) for optional parameters
- Provide comprehensive docstring with Args and Returns
- Document which API (REST/GraphQL) the implementation should use

### Step 2: Implement in RealGitHub

Implement the actual functionality in `real.py` using `gh` CLI.

**Pattern for GraphQL query:**

```python
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
        nodes {
          id
          isResolved
          path
          line
        }
      }
    }
  }
}"""

    variables = json.dumps({
        "owner": repo_info.owner,
        "repo": repo_info.name,
        "number": pr_number
    })

    cmd = ["gh", "api", "graphql", "-f", f"query={query}", "-f", f"variables={variables}"]
    stdout = execute_gh_command(cmd, repo_root)
    response = json.loads(stdout)

    return self._parse_review_threads_response(response, include_resolved)
```

**Pattern for REST API:**

```python
def get_pr(self, owner: str, repo: str, pr_number: int) -> PRDetails | PRNotFound:
    """Get PR details via REST API."""
    cmd = ["gh", "api", f"repos/{owner}/{repo}/pulls/{pr_number}"]

    try:
        stdout = execute_gh_command(cmd, Path.cwd())
        data = json.loads(stdout)

        # Transform REST response to internal types
        return PRDetails(
            number=data["number"],
            state=self._parse_pr_state(data),
            title=data["title"],
            # ... other fields
        )
    except subprocess.CalledProcessError as e:
        if "Not Found" in e.stderr:
            return PRNotFound()
        raise
```

**Key points:**

- Use `execute_gh_command()` from subprocess utils (not raw subprocess.run)
- Parse JSON response into typed dataclasses
- Extract parsing logic to helper methods (e.g., `_parse_review_threads_response`)
- Handle API errors appropriately (404 → sentinel, others → raise)

### Step 3: Implement in FakeGitHub

Implement test double in `fake.py` with constructor-injected test data.

**Pattern:**

```python
from dataclasses import dataclass, field

@dataclass
class FakeGitHub(GitHub):
    _pr_review_threads: dict[int, list[PRReviewThread]] = field(default_factory=dict)
    _resolved_thread_ids: set[str] = field(default_factory=set)

    def get_pr_review_threads(
        self,
        repo_root: Path,
        pr_number: int,
        *,
        include_resolved: bool = False,
    ) -> list[PRReviewThread]:
        """Get review threads for a PR from pre-configured data."""
        threads = self._pr_review_threads.get(pr_number, [])

        # Apply any state changes from previous method calls
        result_threads: list[PRReviewThread] = []
        for t in threads:
            is_resolved = t.is_resolved or t.id in self._resolved_thread_ids
            if is_resolved and not include_resolved:
                continue
            result_threads.append(
                PRReviewThread(
                    id=t.id,
                    path=t.path,
                    line=t.line,
                    is_resolved=is_resolved,
                    is_outdated=t.is_outdated,
                    comments=t.comments,
                )
            )

        # Sort by (path, line) to match real implementation
        return sorted(result_threads, key=lambda t: (t.path, t.line or 0))
```

**Key points:**

- Use dataclass fields for injectable test data (default_factory for mutable defaults)
- Return data from constructor-injected dictionaries/collections
- Apply any mutations that occurred during the test (track in instance state)
- Match sorting/filtering behavior of real implementation
- Keep fake logic simple - just return/transform pre-configured data

### Step 4: Implement in DryRunGitHub

Implement dry-run wrapper in `dry_run.py`.

**Pattern for read operation:**

```python
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
```

**Pattern for write operation:**

```python
def resolve_review_thread(
    self,
    repo_root: Path,
    thread_id: str,
) -> bool:
    """No-op write operation in dry-run mode."""
    click.echo(f"[DRY RUN] Would resolve review thread: {thread_id}", err=True)
    return True  # Simulate success
```

**Key points:**

- Read operations: delegate to wrapped implementation
- Write operations: print what would happen, return success
- Use `click.echo(..., err=True)` for dry-run messages
- Preserve method signature exactly

### Step 5: Add Types to types.py

Define frozen dataclasses for new data structures in `types.py`.

**Pattern:**

```python
from dataclasses import dataclass

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

**Key points:**

- Use `@dataclass(frozen=True)` for immutability
- Use tuple for sequences (immutable)
- Document all fields in docstring
- Use `| None` for optional values (not `Optional`)
- Specify what IDs are used for (e.g., "GraphQL node ID")

### Step 6: Export from **init**.py

Add new types and methods to public API in `__init__.py`.

**Pattern:**

```python
from erk_shared.github.abc import GitHub as GitHub
from erk_shared.github.dry_run import DryRunGitHub as DryRunGitHub
from erk_shared.github.fake import FakeGitHub as FakeGitHub
from erk_shared.github.real import RealGitHub as RealGitHub
from erk_shared.github.types import (
    PRDetails as PRDetails,
    PRReviewThread as PRReviewThread,  # Add new type
    PRReviewComment as PRReviewComment,  # Add new type
    # ... other exports
)
```

**Key points:**

- Use `import X as X` syntax for explicit re-exports (avoids F401 lint warnings)
- Export all public types
- Group exports by module (abc, implementations, types)

### Step 7: Write Unit Tests

Create tests in `tests/unit/github/` using FakeGitHub.

**Pattern:**

```python
"""Tests for PR review thread functionality in GitHub layer."""

from pathlib import Path

from erk_shared.github.fake import FakeGitHub
from erk_shared.github.types import PRReviewComment, PRReviewThread


def test_fake_get_pr_review_threads_returns_configured_threads() -> None:
    """Test that FakeGitHub returns pre-configured review threads."""
    comment = PRReviewComment(
        id=1,
        body="This should use LBYL pattern",
        author="reviewer",
        path="src/foo.py",
        line=42,
        created_at="2024-01-01T10:00:00Z",
    )
    thread = PRReviewThread(
        id="PRRT_1",
        path="src/foo.py",
        line=42,
        is_resolved=False,
        is_outdated=False,
        comments=(comment,),
    )

    github = FakeGitHub(pr_review_threads={123: [thread]})

    threads = github.get_pr_review_threads(Path("/repo"), 123)

    assert len(threads) == 1
    assert threads[0].id == "PRRT_1"
    assert threads[0].path == "src/foo.py"
    assert threads[0].line == 42
    assert not threads[0].is_resolved


def test_fake_filters_resolved_threads() -> None:
    """Test that resolved threads are filtered by default."""
    unresolved = PRReviewThread(
        id="PRRT_1", path="a.py", line=10,
        is_resolved=False, is_outdated=False, comments=()
    )
    resolved = PRReviewThread(
        id="PRRT_2", path="b.py", line=20,
        is_resolved=True, is_outdated=False, comments=()
    )

    github = FakeGitHub(pr_review_threads={123: [unresolved, resolved]})

    threads = github.get_pr_review_threads(Path("/repo"), 123)
    assert len(threads) == 1  # Only unresolved

    threads_all = github.get_pr_review_threads(Path("/repo"), 123, include_resolved=True)
    assert len(threads_all) == 2  # Both threads


def test_fake_resolve_thread_updates_state() -> None:
    """Test that resolving a thread updates fake state."""
    thread = PRReviewThread(
        id="PRRT_1", path="a.py", line=10,
        is_resolved=False, is_outdated=False, comments=()
    )

    github = FakeGitHub(pr_review_threads={123: [thread]})

    # Initially unresolved
    threads = github.get_pr_review_threads(Path("/repo"), 123)
    assert len(threads) == 1

    # Resolve the thread
    github.resolve_review_thread(Path("/repo"), "PRRT_1")

    # Now filtered out
    threads = github.get_pr_review_threads(Path("/repo"), 123)
    assert len(threads) == 0
```

**Key points:**

- Test constructor injection pattern
- Test filtering/sorting behavior matches real implementation
- Test state changes (mutations affect subsequent reads)
- Use descriptive test names (what_when_outcome pattern)
- Test both happy path and edge cases

## Verification Checklist

Before submitting PR, verify:

- [ ] ABC method has complete docstring (Args, Returns, Raises if applicable)
- [ ] RealGitHub implementation uses subprocess wrappers (not raw subprocess)
- [ ] FakeGitHub uses constructor injection (not methods that mutate config)
- [ ] DryRunGitHub delegates reads, no-ops writes with echo
- [ ] Types use `@dataclass(frozen=True)` and modern type syntax (`list[X]`, `X | None`)
- [ ] New types exported from `__init__.py` with `as` syntax
- [ ] Unit tests cover happy path, filtering, and state changes
- [ ] Tests use FakeGitHub, not mocks
- [ ] All tests pass (`uv run pytest`)
- [ ] Type checking passes (`uv run pyright`)

## Common Patterns

### Not-Found Sentinel Pattern

For operations that may not find a resource (e.g., PR not found):

```python
# In types.py
@dataclass(frozen=True)
class PRNotFound:
    """Sentinel indicating PR was not found."""
    pass

# In real.py
def get_pr(self, owner: str, repo: str, pr_number: int) -> PRDetails | PRNotFound:
    try:
        # ... fetch PR
        return PRDetails(...)
    except subprocess.CalledProcessError as e:
        if "Not Found" in e.stderr:
            return PRNotFound()
        raise

# Usage
pr = github.get_pr(owner, repo, number)
if isinstance(pr, PRNotFound):
    click.echo("PR not found", err=True)
    raise SystemExit(1)
```

See [Not-Found Sentinel Pattern](not-found-sentinel.md) for details.

### GraphQL Query Pattern

For operations requiring GraphQL:

- Define query with typed variables (`$owner: String!`)
- Pass variables via JSON (`-f variables='...'`)
- Extract parsing to helper method (`_parse_X_response`)
- Use GraphQL `id` field for mutations (not `databaseId`)

See [GitHub Interface Patterns](github-interface-patterns.md#graphql-api-via-gh-api-graphql) for examples.

## Related Topics

- [GitHub Interface Patterns](github-interface-patterns.md) - REST and GraphQL API patterns
- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Handling resource not found
- [Protocol vs ABC](protocol-vs-abc.md) - When to use ABC vs Protocol
- [Subprocess Wrappers](subprocess-wrappers.md) - Safe subprocess execution
