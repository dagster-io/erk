# Testing Fake Implementations

## Directory Structure

**Important:** This directory is nested under `tests/unit/` which has its own `__init__.py`. This structure prevents Python from treating the directory as a namespace package, which would break absolute imports.

When adding new test directories under `tests/`, always ensure:

1. The parent directory has `__init__.py` (e.g., `tests/unit/__init__.py`)
2. The new directory itself has `__init__.py` (e.g., `tests/unit/fakes/__init__.py`)

This ensures `from erk_shared.git.fake import FakeGit` works correctly from any test file.

## Purpose

These tests verify that fake implementations correctly simulate real behavior.
This directory tests the **test infrastructure itself**, not production code.

## What Goes Here

Tests OF the fakes themselves:

- `test_fake_git.py` - Verifies FakeGit mutation tracking, state management
- `test_fake_config_store.py` - Verifies FakeConfigStore config storage
- `test_fake_graphite.py` - Verifies FakeGraphite stack tracking
- `test_fake_github.py` - Verifies FakeGitHub PR simulation
- `test_fake_shell.py` - Verifies FakeShell command tracking

## What DOESN'T Go Here

❌ Tests that USE fakes to test production code
→ Go in `tests/commands/` or `tests/core/`

❌ Tests of real implementations with subprocess/filesystem
→ Go in `tests/integration/`

## Testing Pattern

```python
def test_fake_tracks_mutation() -> None:
    """Test that FakeGit tracks worktree additions."""
    git = FakeGit()

    # Perform operation on fake
    git.add_worktree(Path("/repo"), Path("/worktree"), branch="feature")

    # Verify fake tracked the mutation
    assert (Path("/worktree"), "feature") in git.added_worktrees
    assert len(git.list_worktrees(Path("/repo"))) == 1
```

## Key Principle

These tests ensure fakes are **reliable test doubles** for production code tests.
If fakes don't work correctly, all tests ABOVE the fakes layer are unreliable.

## Maintenance Guidelines

### When to Add or Update Tests

**Add tests when:**

- Creating a new fake implementation
- Adding a new method to an existing fake
- Discovering drift between fake and real behavior
- Adding mutation tracking properties

**Update tests when:**

- Modifying fake implementation behavior
- Changing method signatures
- Fixing bugs in fakes
- Modifying corresponding real implementation

### Process: Keeping Fakes in Sync

When modifying ANY real operations implementation:

1. **Check** if corresponding fake implements the same method
2. **Verify** tests exist for that method in `tests/unit/fakes/`
3. **Add tests** BEFORE merging if missing
4. **Run tests** - both unit tests (fakes) AND integration tests (real)

**Checklist:**

- [ ] Modified real implementation method
- [ ] Checked fake has matching method
- [ ] Verified fake tests exist
- [ ] Added/updated fake tests if needed
- [ ] All tests pass (unit + integration)

### High-Risk Methods Needing Extra Attention

Methods with >30 LOC in real implementation need comprehensive testing:

- **Complex parsing methods** (e.g., `get_file_status`, `list_worktrees`)
- **Stateful operations** that modify internal state
- **Methods with >50 LOC** in real implementation
- **User-visible behavior** (status display, command output)

## See Also

- `tests/fakes/` - Fake implementations being tested
- `tests/commands/` - Tests that USE these fakes
- `tests/integration/` - Tests of real implementations
