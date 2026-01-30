---
title: Test Coverage Review Agent
read_when:
  - "modifying test-coverage review agent"
  - "understanding test coverage review logic"
  - "adding legitimately untestable file patterns"
  - "debugging false positives in test coverage review"
tripwires:
  - action: "flagging code as untested in PR review"
    warning: "Check if file is legitimately untestable first. CLI wrappers (only Click decorators), type-only files (TypeVar/Protocol/type aliases), and ABC interfaces (only abstract methods) should be excluded from test coverage requirements."
---

# Test Coverage Review Agent

Automated review agent that analyzes test coverage for Python source files in PRs. Runs via convention-based review system on every PR.

## Purpose

Ensure new production code has test coverage while recognizing legitimately untestable code patterns.

## Source File

- **Definition**: `.github/reviews/test-coverage.md`
- **Model**: `claude-haiku-4-5` (fast categorization)
- **Patterns**: `src/**/*.py`, `packages/**/*.py`, `tests/**/*.py`
- **Marker**: `<!-- test-coverage-review -->`

## File Categorization (6 Buckets)

Every Python file in the PR is categorized into one of 6 buckets:

### Source Buckets

1. **source_added** - New files in `src/` or `packages/` (excluding tests)
2. **source_modified** - Modified files in `src/` or `packages/` with significant changes
   - Excludes: import reordering, type annotation changes, whitespace/formatting, comments only
   - Includes: new functions, classes, methods, meaningful logic changes
3. **source_deleted** - Deleted files in `src/` or `packages/`

### Test Buckets

4. **tests_added** - New files in `tests/`
5. **tests_modified** - Modified files in `tests/`
6. **tests_deleted** - Deleted files in `tests/`

### Excluded Files (Not Categorized)

- `__init__.py`, `conftest.py`, `__main__.py`
- Documentation files (`.md`, `.rst`, `.txt`)
- Configuration files (`.toml`, `.cfg`, `.ini`, `.yaml`, `.yml`, `.json`)
- Type stub files (`.pyi`)
- Data files, fixtures, non-logic files

## Legitimately Untestable File Detection

The agent reads source files to detect patterns that make them legitimately untestable:

### 1. Thin CLI Wrappers

Files containing only Click decorators and delegation to other modules:

```python
import click
from erk.core.logic import do_work

@click.command()
@click.option("--verbose", is_flag=True)
def my_command(*, verbose: bool):
    do_work(verbose=verbose)
```

**Heuristic**: No business logic, only `@click.*` decorators and single function calls.

### 2. Type-Only Files

Files containing only type definitions with no runtime logic:

```python
from typing import TypeVar, Protocol

T = TypeVar("T")

class Comparable(Protocol):
    def __lt__(self, other) -> bool: ...
```

**Heuristic**: Only `TypeVar`, `Protocol`, type aliases, no classes with implementations.

### 3. ABC Definition Files

Files containing only abstract base classes with abstract method signatures:

```python
from abc import ABC, abstractmethod

class MyGateway(ABC):
    @abstractmethod
    def fetch_data(self) -> str:
        ...
```

**Heuristic**: All methods are `@abstractmethod`, no concrete implementations.

### 4. Re-Export/Barrel Files

Files that only import and re-export symbols from other modules:

```python
from .impl import MyClass, my_function

__all__ = ["MyClass", "my_function"]
```

**Heuristic**: Only imports and `__all__` definition, no new logic.

## Test Coverage Matching Logic

For each file in `source_added` and `source_modified`, the agent searches for corresponding test files:

### Pattern 1: Direct Match

```
src/erk/config.py → tests/test_config.py
```

### Pattern 2: Parent Directory Prefix

```
src/erk/cli/commands/land.py → tests/cli/test_commands_land.py
```

### Pattern 3: Import-Based Match

New test files in `tests_added` that import from the source module are considered coverage.

### Test Rename Detection

If `tests_deleted` and `tests_added` contain files with similar names or overlapping content, treat as rename rather than deletion + gap.

## Flagging Conditions

The agent flags these conditions:

### 1. Untested New Source Files

New production code without corresponding tests (excludes legitimately untestable files).

**Flag**: ❌ **N new source file(s) without tests**

### 2. Net Test Reduction

More test files deleted than added, especially when source is also added.

**Flag**: ❌ **Net test reduction: N deleted, M added**

### 3. Source Addition Without Test Effort

Non-trivial source added with zero test files added.

**Flag**: ❌ **Significant source added with no test additions**

## Output Format

### Summary Comment

```markdown
### Source Files

| File | Status | Tests |
|------|--------|-------|
| `src/path/file.py` | Added | ❌ No tests |
| `src/path/other.py` | Modified | ✅ `tests/test_other.py` |
| `src/path/types.py` | Added | ➖ Excluded (type-only) |

### Flags

- ❌ **2 new source file(s) without tests**
- ❌ **Net test reduction: 3 deleted, 1 added**

### Excluded Files

- `src/path/__init__.py` — init file
- `src/path/types.py` — type-only file

### Activity Log

- 2026-01-30 14:23 UTC: Found 2 untested source files (file.py, other.py)
- 2026-01-29 10:15 UTC: All source files have test coverage
- 2026-01-28 16:45 UTC: No source additions or significant modifications
```

### Inline Comments

Posted on first line of each untested file:

```
**Test Coverage**: New source file without corresponding tests. Erk requires Layer 4 business logic tests for all feature code.
```

Posted on deleted test files where source still exists:

```
**Test Coverage**: Test file deleted but corresponding source code still exists. This reduces test coverage.
```

## Early Exit Conditions

The agent skips analysis with a brief summary if:

- PR only touches test files (test-only PR)
- PR only touches docs/config files (no source or test changes)
- No source additions and no significant source modifications

**Early Exit Summary**:

```
### Test Coverage Review
No source additions or significant modifications detected. Skipping coverage analysis.
```

## Marker-Based Deduplication

The `<!-- test-coverage-review -->` marker ensures:

- Only one summary comment per PR
- Updates replace previous comments (not accumulate)
- Activity log preserves history across updates

## Integration with Fake-Driven Testing

The agent's categorization aligns with erk's 5-layer test architecture:

- **Legitimately untestable**: Layers 0-2 (CLI wrappers, type definitions, ABCs)
- **Requires tests**: Layers 3-4 (business logic, operations)

See [Fake-Driven Testing](../testing/fake-driven-testing.md) for the test architecture.

## Related Documentation

- [Convention-Based Reviews](../ci/convention-based-reviews.md) - Review discovery and execution system
- [Fake-Driven Testing](../testing/fake-driven-testing.md) - 5-layer test architecture
- [Testing Tripwires](../testing/tripwires.md) - Test-related constraints
