# Core Component Testing Patterns

## Overview

This directory contains unit tests for core erk components - the business logic layer that sits below CLI commands. Tests here focus on pure logic without CLI integration.

## Subdirectory Organization

| Directory     | Focus                            | When to Load                   |
| ------------- | -------------------------------- | ------------------------------ |
| `config/`     | Configuration management         | Config loading and environment |
| `operations/` | Git, Graphite, GitHub operations | Operations layer with fakes    |
| `detection/`  | Auto-detection logic             | Dagster, branch detection      |
| `utils/`      | Utility functions                | File utils, naming conventions |
| `foundation/` | Core infrastructure              | Context, templates             |

## Core vs Command Tests

**Core tests** focus on:

- Business logic without CLI concerns
- Direct function/class testing
- Pure unit tests with minimal setup
- Algorithm and data structure testing

**Command tests** focus on:

- CLI interface (Click commands)
- User-facing output formatting
- Command-line argument parsing
- Integration via CliRunner

## Standard Core Test Pattern

```python
from erk.core.integration.git import Git
from tests.fakes.fake_git import FakeGit

def test_core_logic() -> None:
    # Arrange: Set up fakes
    git = FakeGit(
        current_branch="main",
        all_branches=["main", "feature"]
    )

    # Act: Call core function directly
    result = some_core_function(git)

    # Assert: Verify behavior
    assert result == expected_value
    assert "feature" in git.created_branches
```

## Dependency Injection at Core Layer

Core components use constructor injection:

```python
from dataclasses import dataclass
from erk.core.integration.git import Git

@dataclass(frozen=True)
class WorkspaceManager:
    git: Git

    def create_workspace(self, name: str) -> None:
        self.git.create_branch(name)

def test_workspace_manager() -> None:
    git = FakeGit(current_branch="main")
    manager = WorkspaceManager(git=git)

    manager.create_workspace("new-branch")

    assert "new-branch" in git.created_branches
```

## Testing Without CLI

Core tests don't use `CliRunner`:

```python
# ❌ DON'T: Use CliRunner for core tests
from click.testing import CliRunner

# ✅ DO: Call functions directly
from erk.core.naming import sanitize_branch_name

def test_sanitize_branch_name() -> None:
    result = sanitize_branch_name("Feature/Test Branch")
    assert result == "feature/test-branch"
```

## Common Core Test Patterns

### Pure Functions

```python
def test_pure_function() -> None:
    # Pure functions are easiest to test
    input_value = "test-input"
    expected = "expected-output"

    result = pure_function(input_value)

    assert result == expected
```

### Stateful Classes

```python
def test_stateful_class() -> None:
    # Use fakes for dependencies
    git = FakeGit(current_branch="main")

    # Construct with dependencies
    instance = MyClass(git=git)

    # Exercise behavior
    instance.do_something()

    # Assert via fake's read-only properties
    assert len(git.created_branches) == 1
```

### Algorithm Testing

```python
def test_algorithm() -> None:
    # Test edge cases
    assert algorithm([]) == []
    assert algorithm([1]) == [1]
    assert algorithm([1, 2, 3]) == [3, 2, 1]

    # Test error conditions
    with pytest.raises(ValueError):
        algorithm(None)
```

## Subdirectory-Specific Guidance

### Config Tests

See `config/` - Testing configuration loading, validation, and environment variable handling.

### Operations Tests

See `operations/CLAUDE.md` - Testing git, Graphite, and GitHub operations with fakes. **Critical for understanding mutation tracking.**

### Detection Tests

See `detection/` - Testing auto-detection logic for Dagster projects, default branches, etc.

### Utils Tests

See `utils/` - Testing utility functions like file operations, naming conventions.

### Foundation Tests

See `foundation/` - Testing core infrastructure like ErkContext, setup templates.

## Testing Strategies

### LBYL Pattern Testing

Core code follows LBYL (Look Before You Leap):

```python
def test_lbyl_pattern() -> None:
    git = FakeGit(
        current_branch="main",
        all_branches=["main"]
    )

    # Function checks existence before acting
    if "feature" in git.all_branches:
        result = switch_to_branch(git, "feature")
    else:
        result = None

    assert result is None  # Branch doesn't exist
```

### Mutation Tracking

Never use mocks - track mutations via read-only properties:

```python
def test_mutation_tracking() -> None:
    git = FakeGit(current_branch="main")

    create_branch(git, "new-branch")

    # ❌ DON'T: mock.assert_called_with(...)
    # ✅ DO: Check read-only property
    assert "new-branch" in git.created_branches
```

## Test File Organization

**Use plain functions, not test classes.** Test classes should only be used when testing a class or dataclass itself.

**Pattern for core tests:**

```python
# ✅ CORRECT: Plain functions
def test_calculate_stack_range() -> None: ...
def test_identify_removable_worktrees() -> None: ...
def test_create_consolidation_plan() -> None: ...

# ❌ WRONG: Test classes for grouping
class TestConsolidationUtils:
    def test_calculate_stack_range(self) -> None: ...
```

**One-function-per-file pattern with subdirectories:**

When a test file has 7+ test classes for different functions (~450 lines), split into:

```
tests/core/utils/worktree/
├── __init__.py
├── test_find_worktree_containing_path.py
├── test_find_current_worktree.py
└── test_is_root_worktree.py
```

Each file contains plain test functions (no classes) testing one utility function.

**Exception:** Test classes ARE appropriate when testing a class or dataclass:

```python
# ✅ CORRECT: Testing a dataclass
class TestDeletableWorktree:
    def test_equality(self) -> None: ...
    def test_frozen(self) -> None: ...
```

**See [docs/learned/testing.md#test-organization-principles](../../docs/learned/testing.md#test-organization-principles) for detailed guidance.**

## See Also

- [operations/CLAUDE.md](operations/CLAUDE.md) - Operations testing patterns (critical)
- [../CLAUDE.md](../CLAUDE.md) - Overall test structure
- [../docs/TESTING.md](../../docs/TESTING.md) - Complete testing guide
