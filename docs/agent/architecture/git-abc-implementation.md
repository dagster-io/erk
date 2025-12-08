---
title: Git ABC Implementation Checklist
read_when:
  - "adding a new method to Git ABC"
  - "implementing Git interface methods"
tripwire: "**CRITICAL: Before adding a new method to Git ABC** → Read [Git ABC Implementation](architecture/git-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
---

# Git ABC Implementation Checklist

When adding a new method to the Git ABC interface, you must implement it in **5 places**. Missing any of these will cause runtime errors or test failures.

## The Five Implementations

| Implementation | Location                           | Purpose                                                 |
| -------------- | ---------------------------------- | ------------------------------------------------------- |
| `abc.py`       | `erk/integrations/git/abc.py`      | Abstract method definition (contract)                   |
| `real.py`      | `erk/integrations/git/real.py`     | Actual git subprocess calls (production)                |
| `fake.py`      | `erk/integrations/git/fake.py`     | Constructor-injected test data (unit tests)             |
| `dry_run.py`   | `erk/integrations/git/dry_run.py`  | Delegates to wrapped (read-only) or logs (mutations)    |
| `printing.py`  | `erk/integrations/git/printing.py` | Delegates to wrapped, prints mutations (verbose output) |

## Implementation Checklist

When adding a new Git method, follow these steps:

1. [ ] Add abstract method to `abc.py` with docstring
2. [ ] Implement in `real.py` using subprocess
3. [ ] Implement in `fake.py` with constructor parameter for test data
4. [ ] Implement in `dry_run.py` (delegate if read-only, log if mutation)
5. [ ] Implement in `printing.py` (delegate, print if mutation)
6. [ ] Add unit tests for FakeGit behavior
7. [ ] Add integration tests for RealGit (if feasible)

## Example: Adding get_commit_messages_since()

### Step 1: Abstract method in abc.py

```python
from abc import ABC, abstractmethod

class Git(ABC):
    @abstractmethod
    def get_commit_messages_since(self, cwd: Path, parent_branch: str) -> list[str]:
        """Get commit messages from parent_branch to current HEAD.

        Args:
            cwd: Repository directory
            parent_branch: Branch to compare against

        Returns:
            List of commit messages (subject + body)
        """
```

### Step 2: Real implementation in real.py

```python
from pathlib import Path
import subprocess

class RealGit(Git):
    def get_commit_messages_since(self, cwd: Path, parent_branch: str) -> list[str]:
        """Get commit messages from parent_branch to current HEAD."""
        result = subprocess.run(
            ["git", "log", f"{parent_branch}..HEAD", "--format=%B%n---COMMIT---"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )

        commits = result.stdout.strip().split("---COMMIT---")
        return [c.strip() for c in commits if c.strip()]
```

### Step 3: Fake implementation in fake.py

```python
from pathlib import Path

class FakeGit(Git):
    def __init__(
        self,
        # ... existing parameters ...
        commit_messages_since: dict[tuple[Path, str], list[str]] | None = None,
    ) -> None:
        # ... existing initialization ...
        self._commit_messages_since = commit_messages_since or {}

    def get_commit_messages_since(self, cwd: Path, parent_branch: str) -> list[str]:
        """Get commit messages from constructor data."""
        key = (cwd, parent_branch)
        if key not in self._commit_messages_since:
            return []
        return self._commit_messages_since[key]
```

### Step 4: Dry-run implementation in dry_run.py

```python
from pathlib import Path

class DryRunGit(Git):
    def __init__(self, wrapped: Git) -> None:
        self._wrapped = wrapped

    def get_commit_messages_since(self, cwd: Path, parent_branch: str) -> list[str]:
        """Read-only operation: delegate to wrapped implementation."""
        return self._wrapped.get_commit_messages_since(cwd, parent_branch)
```

### Step 5: Printing implementation in printing.py

```python
from pathlib import Path
import click

class PrintingGit(Git):
    def __init__(self, wrapped: Git) -> None:
        self._wrapped = wrapped

    def get_commit_messages_since(self, cwd: Path, parent_branch: str) -> list[str]:
        """Read-only operation: delegate without printing."""
        return self._wrapped.get_commit_messages_since(cwd, parent_branch)
```

### Step 6: Unit tests for FakeGit

```python
from pathlib import Path
from erk.integrations.git.fake import FakeGit

def test_fake_git_commit_messages_since():
    """Test FakeGit returns configured commit messages."""
    cwd = Path("/repo")
    parent = "main"
    messages = ["feat: add feature", "fix: bug fix"]

    fake_git = FakeGit(
        commit_messages_since={
            (cwd, parent): messages,
        }
    )

    result = fake_git.get_commit_messages_since(cwd, parent)
    assert result == messages

def test_fake_git_commit_messages_since_missing():
    """Test FakeGit returns empty list for unconfigured paths."""
    fake_git = FakeGit()
    result = fake_git.get_commit_messages_since(Path("/other"), "main")
    assert result == []
```

### Step 7: Integration tests for RealGit

```python
import subprocess
from pathlib import Path
from erk.integrations.git.real import RealGit

def test_real_git_commit_messages_since(tmp_path: Path):
    """Test RealGit retrieves actual commit messages."""
    # Setup: Create git repo with commits
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)

    (tmp_path / "file.txt").write_text("initial", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)
    subprocess.run(["git", "branch", "main"], cwd=tmp_path, check=True)

    (tmp_path / "file.txt").write_text("change", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "feat: new feature"], cwd=tmp_path, check=True)

    # Test
    real_git = RealGit()
    messages = real_git.get_commit_messages_since(tmp_path, "main")

    assert len(messages) == 1
    assert "feat: new feature" in messages[0]
```

## Classification: Read-Only vs Mutation

**Read-only methods** (delegate in dry_run.py, silent in printing.py):

- `get_current_branch()`
- `list_worktrees()`
- `get_commit_messages_since()`
- Methods that query state without changing it

**Mutation methods** (log/simulate in dry_run.py, print in printing.py):

- `create_worktree()`
- `delete_worktree()`
- `checkout_branch()`
- Methods that modify git state

## Common Pitfall: PrintingGit Falls Behind

**PrintingGit is the most commonly forgotten implementation.** When you add a method and tests fail with:

```
AttributeError: 'PrintingGit' object has no attribute 'get_commit_messages_since'
```

This means you forgot to implement the method in `printing.py`.

**Fix**: Implement the method in PrintingGit (Step 5 above).

## Design Principle: Keep Methods Simple

Git ABC methods should be **thin wrappers** around git commands:

✅ **Good**: `get_commit_messages_since(cwd, parent)` - one git command
✅ **Good**: `create_worktree(path, branch)` - one git command

❌ **Bad**: `sync_worktree_with_stack()` - complex orchestration (belongs in business logic)
❌ **Bad**: `validate_and_create_worktree()` - validation + mutation (separate concerns)

**Rule of thumb**: If the method needs more than 10 lines in RealGit, it probably belongs in a service/command instead.

## Related Documentation

- [Erk Architecture](erk-architecture.md) - Dependency injection patterns
- [Subprocess Wrappers](subprocess-wrappers.md) - How to wrap subprocess calls safely
- [Protocol vs ABC](protocol-vs-abc.md) - Why we use ABC for interfaces
