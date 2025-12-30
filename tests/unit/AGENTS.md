# Unit Tests: Testing Test Infrastructure

## Purpose

This directory contains unit tests of the **test infrastructure itself** - the fake implementations that other tests rely on.

Tests in this layer verify that fakes are correct and reliable test doubles. If fakes are broken, all higher-layer tests become unreliable.

## Directory Structure

**Important:** The `tests/unit/` directory itself must have `__init__.py` to ensure Python recognizes it as a regular package, not a namespace package.

Without `__init__.py`, Python 3.3+ treats this as a namespace package, which breaks absolute imports like `from tests.fakes.git import FakeGit`.

## Subdirectories

### `tests/unit/fakes/` - Tests OF Fake Implementations

Tests that verify fake implementations work correctly:

- `test_fake_git.py` - Verifies FakeGit mutation tracking and state management
- `test_fake_config_store.py` - Verifies FakeConfigStore config storage
- `test_fake_graphite.py` - Verifies FakeGraphite stack tracking (if exists)
- `test_fake_github.py` - Verifies FakeGitHub PR simulation (if exists)
- `test_fake_shell.py` - Verifies FakeShell command tracking (if exists)

**See:** [fakes/CLAUDE.md](fakes/CLAUDE.md) for testing patterns.

## What Goes in tests/unit/

✅ Tests OF fake implementations
✅ Tests of test utilities and helpers
✅ Tests of test fixtures

## What DOESN'T Go Here

❌ Tests that USE fakes to test production code
→ Go in `tests/commands/` or `tests/core/`

❌ Tests of real implementations with subprocess/filesystem
→ Go in `tests/integration/`

## Testing Pattern

```python
from pathlib import Path
from tests.fakes.fake_git import FakeGit
from erk.core.integration import WorktreeInfo

def test_fake_git_tracks_mutations() -> None:
    """Test that FakeGit correctly tracks state changes."""
    # Arrange: Create a fake
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature"]
    )

    # Act: Perform operations on the fake
    git.create_branch("new-branch")
    git.checkout("new-branch")

    # Assert: Verify the fake tracked mutations correctly
    assert "new-branch" in git.created_branches
    assert git.current_branch == "new-branch"
```

## Key Principle: Reliability of Test Doubles

These tests ensure fakes are **reliable test doubles** for all higher-layer tests:

```
If FakeGit is broken
  → All tests in tests/commands/ that use it are unreliable
  → All tests in tests/core/ that use it are unreliable
```

Therefore, tests/unit/ serves as the foundation:

```
tests/unit/fakes/
  ↑
  └─── ensures fakes are correct
        ├─→ tests/commands/ can trust FakeGit
        ├─→ tests/core/ can trust FakeGit
        └─→ All higher-layer tests are reliable
```

## When to Add Tests to tests/unit/

1. **Adding a new fake implementation**
   - Create corresponding test file in `tests/unit/fakes/`
   - Test the fake's mutation tracking and state management

2. **Modifying an existing fake**
   - Add tests to verify new behavior works correctly
   - Ensure existing tests still pass

3. **Adding test utilities or fixtures**
   - Consider adding tests to verify they work as expected

## Test File Organization

**Use plain functions, not test classes.** Test classes should only be used when testing a class or dataclass itself.

**Pattern for unit tests:**

```python
# ✅ CORRECT: Plain functions testing fake implementations
def test_fake_git_tracks_branch_creation() -> None: ...
def test_fake_git_tracks_branch_deletion() -> None: ...
def test_fake_git_handles_checkout() -> None: ...

# ❌ WRONG: Test classes for grouping
class TestFakeGit:
    def test_tracks_branch_creation(self) -> None: ...
```

**Exception:** When testing a dataclass or class behavior itself:

```python
# ✅ CORRECT: Testing dataclass methods
class TestDeletableWorktree:
    def test_equality(self) -> None: ...
    def test_frozen(self) -> None: ...
```

**See [docs/learned/testing.md#test-organization-principles](../../docs/learned/testing.md#test-organization-principles) for detailed guidance.**

## See Also

- [../CLAUDE.md](../CLAUDE.md) - Overall test structure and directory requirements
- [fakes/CLAUDE.md](fakes/CLAUDE.md) - Testing fake implementations
- [../commands/CLAUDE.md](../commands/CLAUDE.md) - CLI command tests (uses fakes)
- [../core/CLAUDE.md](../core/CLAUDE.md) - Core tests (uses fakes)
- [../../docs/TESTING.md](../../docs/TESTING.md) - Complete testing guide
