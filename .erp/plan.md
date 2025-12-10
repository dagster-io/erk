<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-body -->
<details>
<summary><strong>📋 Implementation Plan</strong></summary>

# Refactor Uniform Try-Catch Pattern in create_cmd.py

## Current State Analysis

### SystemExit Raises in create_cmd.py
Found **5 instances** of uniform try-catch pattern raising SystemExit(1):

1. **Line 61**: OSError reading file
2. **Line 68**: OSError reading stdin
3. **Line 98**: RuntimeError ensuring label exists
4. **Line 128**: RuntimeError creating issue
5. **Line 141**: RuntimeError adding comment (Warning variant)

### Current Pattern
```python
try:
    # operation
except SomeError as e:
    user_output(click.style("Error: ", fg="red") + f"Message: {e}")
    raise SystemExit(1) from e
```

### Codebase-Wide Scope
This pattern appears **~18 times across 11 files**:
- RuntimeError (most common, 9x) - integration layer failures
- OSError (2x) - file I/O operations
- PermissionError (1x) - config save failures
- CalledProcessError (1x) - subprocess failures

## Three Refactoring Approaches

### Approach 1: Minimal Change (Lambda Wrapper)
Add simple helper methods to Ensure class that wrap operations in callables.

**API Example:**
```python
# Before
try:
    issue = ctx.issues.get_issue(repo_root, issue_number)
except RuntimeError as e:
    user_output(click.style("Error: ", fg="red") + f"Failed to fetch issue: {e}")
    raise SystemExit(1) from e

# After
issue = Ensure.runtime_safe(
    lambda: ctx.issues.get_issue(repo_root, issue_number),
    "Failed to fetch issue"
)
```

**Pros:**
- Most similar to existing Ensure API (static methods returning values)
- Maintains type narrowing (returns T, not T | None)
- Minimal API surface (1-2 new methods)
- Natural fit with existing patterns

**Cons:**
- Lambda syntax may be unfamiliar to some
- Slightly verbose for simple operations
- Adds indentation for wrapped code

### Approach 2: Context Manager
Introduce Pythonic context manager for error boundaries.

**API Example:**
```python
# Before
try:
    issue = ctx.issues.get_issue(repo_root, issue_number)
except RuntimeError as e:
    user_output(click.style("Error: ", fg="red") + f"Failed to fetch issue: {e}")
    raise SystemExit(1) from e

# After
with Ensure.catching(RuntimeError, prefix="Failed to fetch issue"):
    issue = ctx.issues.get_issue(repo_root, issue_number)
```

**Pros:**
- Pythonic and familiar pattern
- Visually clear error boundary scope
- Supports multiple operations in one block
- No lambda syntax needed
- Can support warning mode (non-fatal)

**Cons:**
- Introduces new concept (context manager) to Ensure class
- Adds indentation level to code
- Less similar to existing Ensure static method pattern
- More complex for simple single-line operations

### Approach 3: Domain-Specific Methods
Extend Ensure with specialized methods per exception type.

**API Example:**
```python
# Generic wrapper
result = Ensure.succeeds(
    lambda: operation(),
    "Failed to complete operation",
    exception_type=RuntimeError
)

# Specialized convenience methods
issue = Ensure.integration_call(
    lambda: ctx.issues.get_issue(repo_root, issue_number),
    "Failed to fetch issue"
)

content = Ensure.file_operation(
    lambda: file.read_text(encoding="utf-8"),
    "Failed to read file"
)
```

**Pros:**
- Consistent with existing Ensure domain-specific methods
- Clear intent (integration_call vs file_operation)
- Type-safe return values
- Generic base + specialized convenience methods

**Cons:**
- More API surface area (3+ new methods)
- Still uses lambda syntax
- Proliferation of specialized methods over time

## Comparison Matrix

| Aspect | Lambda Wrapper | Context Manager | Domain-Specific |
|--------|---------------|-----------------|-----------------|
| Similarity to existing Ensure | High | Medium | High |
| Pythonic | Medium | High | Medium |
| API complexity | Low (1-2 methods) | Medium (1 method, multiple params) | High (3+ methods) |
| Learning curve | Low | Low | Low |
| Verbosity | Medium (lambda) | Low (with block) | Medium (lambda) |
| Type safety | Excellent | Good | Excellent |
| Extensibility | Limited | High (parameters) | Medium (new methods) |

## Migration Scope Options

### Option A: Just create_cmd.py (5 instances)
Focus only on the file mentioned by user.

**Pros:**
- Minimal scope, easy to validate
- Quick win
- Test pattern before wider rollout

**Cons:**
- Inconsistency across codebase
- Will need to revisit other files eventually

### Option B: All RuntimeError cases (~15 instances)
Migrate all integration layer error handling.

**Pros:**
- Consistent handling of most common pattern
- Significant boilerplate reduction
- Clear scope (one exception type)

**Cons:**
- Leaves OSError and other patterns unmigrated

### Option C: Complete migration (~18 instances)
Refactor all uniform try-catch patterns.

**Pros:**
- Complete consistency
- Maximum boilerplate reduction
- Single source of truth for error formatting

**Cons:**
- Larger scope, more testing needed
- Mix of exception types to handle

## Special Cases to Preserve

These patterns should NOT be migrated:

1. **Warning variant** (create_cmd.py:134-141) - Uses yellow "Warning:" styling, non-fatal
2. **CalledProcessError with special handling** - Has conditional logic based on return code
3. **ClickException** (implement.py:136) - Uses Click's exception system, not SystemExit
4. **from None** (runs.py:209) - Deliberately suppresses exception chain

## Selected Approach: Domain-Specific Methods

**User choices:**
- ✅ Domain-Specific Methods (specialized methods per exception type)
- ✅ Just create_cmd.py scope (5 instances)

## Implementation Plan

### Phase 1: Add New Methods to Ensure Class

Add three new static methods to `/Users/schrockn/code/erk/src/erk/cli/ensure.py`:

#### 1. Generic Base Method: `Ensure.succeeds()`

```python
from typing import TYPE_CHECKING, Any, Callable

@staticmethod
def succeeds[T](
    operation: Callable[[], T],
    error_message: str,
    *,
    exception_type: type[Exception] = RuntimeError,
) -> T:
    """Execute operation and ensure it succeeds, otherwise output styled error and exit.

    This method provides a generic exception boundary for operations that cannot be
    validated beforehand (network calls, subprocess execution, integration layer calls).

    Args:
        operation: Callable that performs the operation
        error_message: Error message to display if operation fails.
                      "Error: " prefix will be added automatically in red.
                      The original exception message will be appended.
        exception_type: Type of exception to catch (default: RuntimeError)

    Returns:
        The result of the operation if successful (with type T preserved)

    Raises:
        SystemExit: If operation raises the specified exception type

    Example:
        >>> result = Ensure.succeeds(
        >>>     lambda: some_operation(),
        >>>     "Operation failed",
        >>>     exception_type=OSError
        >>> )
    """
    try:
        return operation()
    except exception_type as e:
        user_output(click.style("Error: ", fg="red") + f"{error_message}: {e}")
        raise SystemExit(1) from e
```

#### 2. Convenience Method: `Ensure.integration_call()`

```python
@staticmethod
def integration_call[T](
    operation: Callable[[], T],
    error_message: str,
) -> T:
    """Execute integration layer operation, converting RuntimeError to user-friendly exit.

    This is a specialized version of succeeds() for integration layer calls that
    raise RuntimeError. Integration layer uses RuntimeError to signal business logic
    failures (e.g., GitHub API errors, git command failures).

    Args:
        operation: Callable that performs the integration operation
        error_message: Error message prefix. The exception's message will be appended.
                      "Error: " prefix will be added automatically in red.

    Returns:
        The result of the operation if successful (with type T preserved)

    Raises:
        SystemExit: If operation raises RuntimeError

    Example:
        >>> issue = Ensure.integration_call(
        >>>     lambda: ctx.issues.get_issue(repo_root, issue_number),
        >>>     "Failed to fetch issue"
        >>> )
    """
    return Ensure.succeeds(operation, error_message, exception_type=RuntimeError)
```

#### 3. Convenience Method: `Ensure.file_operation()`

```python
@staticmethod
def file_operation[T](
    operation: Callable[[], T],
    error_message: str,
) -> T:
    """Execute file I/O operation, converting OSError to user-friendly exit.

    This is a specialized version of succeeds() for file operations that
    raise OSError (read, write, filesystem operations).

    Args:
        operation: Callable that performs the file operation
        error_message: Error message prefix. The exception's message will be appended.
                      "Error: " prefix will be added automatically in red.

    Returns:
        The result of the operation if successful (with type T preserved)

    Raises:
        SystemExit: If operation raises OSError

    Example:
        >>> content = Ensure.file_operation(
        >>>     lambda: file.read_text(encoding="utf-8"),
        >>>     "Failed to read file"
        >>> )
    """
    return Ensure.succeeds(operation, error_message, exception_type=OSError)
```

**Import additions:**
```python
from typing import TYPE_CHECKING, Any, Callable  # Add Callable
```

**Module docstring update:**
Add to domain-specific methods list:
```python
"""...
- Exception boundaries (integration calls, file I/O)
"""
```

### Phase 2: Add Unit Tests

Add three test classes to `/Users/schrockn/code/erk/tests/unit/cli/test_ensure.py`:

```python
class TestEnsureSucceeds:
    """Tests for Ensure.succeeds method."""

    def test_returns_value_on_success(self) -> None:
        """Ensure.succeeds returns operation result when no exception."""
        result = Ensure.succeeds(lambda: "success", "Should not fail")
        assert result == "success"

    def test_preserves_return_type(self) -> None:
        """Ensure.succeeds preserves operation return type."""
        result: int = Ensure.succeeds(lambda: 42, "Should not fail")
        assert result == 42

    def test_exits_on_exception(self) -> None:
        """Ensure.succeeds raises SystemExit when operation raises exception."""
        def failing_operation() -> str:
            raise RuntimeError("Network error")

        with pytest.raises(SystemExit) as exc_info:
            Ensure.succeeds(failing_operation, "Failed to connect")
        assert exc_info.value.code == 1

    def test_custom_exception_type(self) -> None:
        """Ensure.succeeds catches specified exception type."""
        def failing_operation() -> str:
            raise OSError("File not found")

        with pytest.raises(SystemExit):
            Ensure.succeeds(failing_operation, "I/O failed", exception_type=OSError)

    def test_does_not_catch_other_exceptions(self) -> None:
        """Ensure.succeeds does not catch exceptions of different type."""
        def failing_operation() -> str:
            raise ValueError("Wrong type")

        # ValueError should propagate, not be caught
        with pytest.raises(ValueError):
            Ensure.succeeds(failing_operation, "Failed", exception_type=RuntimeError)

    def test_error_message_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.succeeds outputs error with red Error prefix."""
        def failing_operation() -> str:
            raise RuntimeError("API timeout")

        with pytest.raises(SystemExit):
            Ensure.succeeds(failing_operation, "API call failed")

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "API call failed" in captured.err
        assert "API timeout" in captured.err

    def test_preserves_exception_chain(self) -> None:
        """Ensure.succeeds maintains exception chain with from e."""
        def failing_operation() -> str:
            raise RuntimeError("Original error")

        with pytest.raises(SystemExit) as exc_info:
            Ensure.succeeds(failing_operation, "Operation failed")

        # Verify exception chaining
        assert exc_info.value.__cause__.__class__.__name__ == "RuntimeError"
        assert str(exc_info.value.__cause__) == "Original error"


class TestEnsureIntegrationCall:
    """Tests for Ensure.integration_call convenience method."""

    def test_returns_value_on_success(self) -> None:
        """Ensure.integration_call returns result on success."""
        result = Ensure.integration_call(
            lambda: {"key": "value"},
            "Should not fail"
        )
        assert result == {"key": "value"}

    def test_catches_runtime_error(self) -> None:
        """Ensure.integration_call catches RuntimeError from integration layer."""
        def failing_operation() -> str:
            raise RuntimeError("API error")

        with pytest.raises(SystemExit):
            Ensure.integration_call(failing_operation, "Integration failed")


class TestEnsureFileOperation:
    """Tests for Ensure.file_operation convenience method."""

    def test_returns_value_on_success(self) -> None:
        """Ensure.file_operation returns result on success."""
        result = Ensure.file_operation(
            lambda: "file content",
            "Should not fail"
        )
        assert result == "file content"

    def test_catches_os_error(self) -> None:
        """Ensure.file_operation catches OSError from file operations."""
        def failing_operation() -> str:
            raise OSError("Permission denied")

        with pytest.raises(SystemExit):
            Ensure.file_operation(failing_operation, "File read failed")
```

### Phase 3: Migrate create_cmd.py

Convert 5 instances in `/Users/schrockn/code/erk/src/erk/cli/commands/plan/create_cmd.py`:

#### Migration 1: Line 57-61 (OSError reading file)

**Before:**
```python
try:
    content = file.read_text(encoding="utf-8")
except OSError as e:
    user_output(click.style("Error: ", fg="red") + f"Failed to read file: {e}")
    raise SystemExit(1) from e
```

**After:**
```python
content = Ensure.file_operation(
    lambda: file.read_text(encoding="utf-8"),
    "Failed to read file"
)
```

#### Migration 2: Line 64-68 (OSError reading stdin)

**Before:**
```python
try:
    content = sys.stdin.read()
except OSError as e:
    user_output(click.style("Error: ", fg="red") + f"Failed to read stdin: {e}")
    raise SystemExit(1) from e
```

**After:**
```python
content = Ensure.file_operation(
    lambda: sys.stdin.read(),
    "Failed to read stdin"
)
```

#### Migration 3: Line 89-98 (RuntimeError ensuring label exists)

**Before:**
```python
try:
    ctx.issues.ensure_label_exists(
        repo_root,
        label="erk-plan",
        description="Implementation plan tracked by erk",
        color="0E8A16",  # Green
    )
except RuntimeError as e:
    user_output(click.style("Error: ", fg="red") + f"Failed to ensure label exists: {e}")
    raise SystemExit(1) from e
```

**After:**
```python
Ensure.integration_call(
    lambda: ctx.issues.ensure_label_exists(
        repo_root,
        label="erk-plan",
        description="Implementation plan tracked by erk",
        color="0E8A16",  # Green
    ),
    "Failed to ensure label exists"
)
```

#### Migration 4: Line 119-128 (RuntimeError creating issue)

**Before:**
```python
try:
    result = ctx.issues.create_issue(
        repo_root=repo_root,
        title=title,
        body=issue_body,
        labels=labels,
    )
except RuntimeError as e:
    user_output(click.style("Error: ", fg="red") + f"Failed to create issue: {e}")
    raise SystemExit(1) from e
```

**After:**
```python
result = Ensure.integration_call(
    lambda: ctx.issues.create_issue(
        repo_root=repo_root,
        title=title,
        body=issue_body,
        labels=labels,
    ),
    "Failed to create issue"
)
```

#### Migration 5: Line 131-141 (RuntimeError adding comment - WARNING VARIANT)

**SPECIAL CASE - DO NOT MIGRATE**

This uses yellow "Warning:" styling and is non-fatal (continues execution after error). This is NOT a candidate for the standard pattern:

```python
try:
    comment_body = format_plan_content_comment(content)
    ctx.issues.add_comment(repo_root, result.number, comment_body)
except RuntimeError as e:
    user_output(
        click.style("Warning: ", fg="yellow")
        + f"Issue created but failed to add plan comment: {e}"
    )
    user_output(f"Issue #{result.number} created but incomplete.")
    user_output(f"URL: {result.url}")
    raise SystemExit(1) from e
```

**Keep this as-is** - different styling and error handling behavior.

**Actual migrations: 4 out of 5 instances**

### Phase 4: Validation

#### Run Tests
```bash
# Unit tests for new Ensure methods
uv run pytest tests/unit/cli/test_ensure.py -v

# Command tests for create_cmd.py
uv run pytest tests/commands/plan/test_create.py -v

# Type checking
uv run pyright src/erk/cli/ensure.py src/erk/cli/commands/plan/create_cmd.py
```

#### Manual Validation
```bash
# Test file input
echo "# Test Plan" > /tmp/test.md
erk create --file /tmp/test.md

# Test stdin input
echo "# Test Plan" | erk create

# Test error cases
erk create --file /nonexistent/file.md  # Should show "Failed to read file" error
```

### Files Modified

1. `/Users/schrockn/code/erk/src/erk/cli/ensure.py` - Add 3 new methods
2. `/Users/schrockn/code/erk/tests/unit/cli/test_ensure.py` - Add 3 test classes
3. `/Users/schrockn/code/erk/src/erk/cli/commands/plan/create_cmd.py` - Migrate 4 instances

### Success Criteria

- ✅ All 3 new methods added to Ensure class
- ✅ All 13+ unit tests pass
- ✅ 4 try-catch blocks converted (5th is special case)
- ✅ Existing command tests pass without modification
- ✅ Pyright reports zero new errors
- ✅ Error output format unchanged (user experience identical)

### Benefits

**Code Reduction:** ~20 lines removed (4 blocks × 5 lines each)

**Consistency:** Single source of truth for:
- Error message formatting
- Exception chaining
- Exit code handling

**Type Safety:**
- Generic type preservation `[T]`
- Type-narrowed return values
- Better IDE autocomplete

**Maintainability:**
- Change error format in 1 place, not 18
- Clear intent with domain-specific methods
- Extensible pattern for future exception types

### Future Considerations

After validating this approach with create_cmd.py, consider:
- Migrating other files with RuntimeError patterns
- Adding more domain-specific methods as patterns emerge
- Documenting pattern in AGENTS.md for consistency

</details>
<!-- /erk:metadata-block:plan-body -->

---

## Execution Commands

**Submit to Erk Queue:**
```bash
erk submit 1280
```

---

### Local Execution

**Standard mode (interactive):**
```bash
erk implement 1280
```

**Yolo mode (fully automated, skips confirmation):**
```bash
erk implement 1280 --yolo
```

**Dangerous mode (auto-submit PR after implementation):**
```bash
erk implement 1280 --dangerous
```