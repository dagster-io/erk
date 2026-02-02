---
title: Exec Script Batch Testing
read_when:
  - writing tests for batch exec commands
  - organizing test cases for JSON stdin/stdout commands
  - implementing fake gateway failure injection for batch operations
tripwires:
  - action: "Test only success cases for batch commands"
    warning: "Cover: all success, partial failure, validation errors, and JSON structure. See test organization categories."
    score: 7
---

# Exec Script Batch Testing

Batch exec commands require comprehensive test coverage across four categories: success cases, partial failures, validation errors, and JSON structure verification. This document outlines the test organization pattern and FakeGateway failure injection techniques.

## Test Organization Categories

Organize batch command tests into these four groups:

### 1. Success Cases

Test scenarios where all items in the batch succeed.

**What to cover:**

- Empty batch (no items)
- Single item batch
- Multiple items batch (typical: 3-5 items)
- Maximum reasonable batch size (if applicable)
- Items with optional fields present/absent

**Example test names:**

- `test_resolve_threads_all_success`
- `test_resolve_threads_single_item`
- `test_resolve_threads_with_comments`
- `test_resolve_threads_empty_batch`

**Assertions:**

```python
assert result["success"] is True  # Top-level AND semantics
assert len(result["results"]) == expected_count
assert all(item["success"] for item in result["results"])
```

### 2. Partial Failure

Test scenarios where some items succeed and some fail.

**What to cover:**

- First item fails, rest succeed
- Last item fails, rest succeed
- Middle item fails
- Multiple scattered failures
- All items fail

**Example test names:**

- `test_resolve_threads_first_item_fails`
- `test_resolve_threads_multiple_failures`
- `test_resolve_threads_all_items_fail`

**Assertions:**

```python
assert result["success"] is False  # Top-level false if any item failed
assert result["results"][0]["success"] is True   # First succeeded
assert result["results"][1]["success"] is False  # Second failed
assert "error" in result["results"][1]
assert "error_type" in result["results"][1]
```

### 3. Input Validation

Test scenarios where input is rejected before processing.

**What to cover:**

- Invalid item identifiers (malformed thread IDs, etc.)
- Missing required fields
- Type mismatches (string instead of int)
- Constraint violations (negative numbers, out-of-range values)

**Example test names:**

- `test_resolve_threads_invalid_thread_id_format`
- `test_resolve_threads_missing_thread_id`
- `test_resolve_threads_multiple_validation_errors`

**Assertions:**

```python
assert result["success"] is False
assert "validation_errors" in result
assert "results" not in result  # No processing occurred
assert len(result["validation_errors"]) == expected_count
```

**Critical check:** Ensure no items were processed when validation fails (no side effects).

### 4. JSON Structure Verification

Test that output conforms to the expected schema.

**What to cover:**

- Required fields present in success response
- Required fields present in error response
- Optional fields absent when not applicable
- Field types match spec (bool, string, int, list)
- Nested structure correctness

**Example test names:**

- `test_resolve_threads_output_schema_success`
- `test_resolve_threads_output_schema_partial_failure`
- `test_resolve_threads_output_schema_validation_error`

**Assertions:**

```python
# Success case schema
assert isinstance(result["success"], bool)
assert isinstance(result["results"], list)
for item in result["results"]:
    assert isinstance(item["success"], bool)
    assert isinstance(item["thread_id"], str)
    if not item["success"]:
        assert isinstance(item["error"], str)
        assert isinstance(item["error_type"], str)
```

## FakeGateway Failure Injection Pattern

To test partial failures, inject failures into fake gateways via a failure set parameter.

### Pattern: resolve_thread_failures Parameter

```python
class FakeGitHub(GitHub):
    def __init__(
        self,
        *,
        resolve_thread_failures: set[str] | None = None,
        # ... other fake config
    ):
        self._resolve_thread_failures = resolve_thread_failures or set()

    def resolve_pr_review_thread(
        self,
        *,
        thread_id: str,
        comment: str | None = None,
    ) -> bool:
        if thread_id in self._resolve_thread_failures:
            return False  # Simulate failure for this thread
        # Normal success logic
        return True
```

### Usage in Tests

```python
def test_resolve_threads_partial_failure(tmp_path):
    # Inject failures for specific thread IDs
    fake_github = FakeGitHub(
        resolve_thread_failures={"PRRT_fail1", "PRRT_fail2"}
    )

    # Prepare batch input
    items = [
        {"thread_id": "PRRT_success"},
        {"thread_id": "PRRT_fail1"},    # Will fail
        {"thread_id": "PRRT_fail2"},    # Will fail
    ]

    # Run batch command
    result = run_batch_command(items, fake_github)

    # Verify partial failure
    assert result["success"] is False
    assert result["results"][0]["success"] is True
    assert result["results"][1]["success"] is False
    assert result["results"][2]["success"] is False
```

### Why Set-Based Injection

**Advantages:**

- **Explicit**: Clear which items should fail
- **Flexible**: Can test any failure pattern (first, last, middle, scattered)
- **Type-safe**: Compile-time checking for thread ID typos
- **Testable**: Easy to verify the fake itself

**Alternative (anti-pattern): Exception-based injection**

```python
# DON'T DO THIS
def resolve_pr_review_thread(self, *, thread_id: str) -> bool:
    if self._should_fail_next:
        raise RuntimeError("Simulated failure")
    # ...
```

**Why this is worse:**

- Stateful (must track "next" operation)
- Brittle (order-dependent)
- Unclear (which item will fail?)
- Hard to test multiple failures in one batch

## Complete Test File Structure

```python
# tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py

class TestResolveReviewThreadsSuccess:
    """Success cases - all items succeed."""

    def test_all_items_succeed(self): ...
    def test_single_item(self): ...
    def test_empty_batch(self): ...
    def test_with_comments(self): ...

class TestResolveReviewThreadsPartialFailure:
    """Partial failure cases - some items fail."""

    def test_first_item_fails(self): ...
    def test_last_item_fails(self): ...
    def test_multiple_failures(self): ...
    def test_all_items_fail(self): ...

class TestResolveReviewThreadsValidation:
    """Validation error cases - input rejected upfront."""

    def test_invalid_thread_id_format(self): ...
    def test_missing_thread_id(self): ...
    def test_multiple_validation_errors(self): ...

class TestResolveReviewThreadsSchema:
    """JSON structure verification."""

    def test_success_schema(self): ...
    def test_partial_failure_schema(self): ...
    def test_validation_error_schema(self): ...
```

**Test count estimate:** 15 tests minimum for comprehensive batch command coverage.

## Parametrized Testing for Failure Patterns

Use `pytest.mark.parametrize` to cover failure pattern variations:

```python
@pytest.mark.parametrize(
    "failures, expected_success_count, expected_failure_count",
    [
        ({"PRRT_2"}, 2, 1),           # Middle fails
        ({"PRRT_1", "PRRT_3"}, 1, 2), # First and last fail
        (set(), 3, 0),                # None fail (all success)
        ({"PRRT_1", "PRRT_2", "PRRT_3"}, 0, 3),  # All fail
    ],
)
def test_resolve_threads_failure_patterns(failures, expected_success_count, expected_failure_count):
    fake_github = FakeGitHub(resolve_thread_failures=failures)
    items = [
        {"thread_id": "PRRT_1"},
        {"thread_id": "PRRT_2"},
        {"thread_id": "PRRT_3"},
    ]
    result = run_batch_command(items, fake_github)

    success_count = sum(1 for r in result["results"] if r["success"])
    failure_count = sum(1 for r in result["results"] if not r["success"])

    assert success_count == expected_success_count
    assert failure_count == expected_failure_count
```

This single test covers 4 failure patterns with minimal duplication.

## Testing Upfront Validation

Critical: verify that validation failures prevent ANY processing.

```python
def test_validation_prevents_processing(monkeypatch):
    # Mock the actual operation to track if it's called
    operation_called = []

    def mock_resolve_thread(thread_id: str) -> bool:
        operation_called.append(thread_id)
        return True

    monkeypatch.setattr(
        "erk.cli.commands.exec.scripts.resolve_review_threads._resolve_thread",
        mock_resolve_thread,
    )

    # Invalid input
    items = [
        {"thread_id": "PRRT_valid"},
        {"thread_id": "invalid"},  # Validation error
    ]

    result = run_batch_command(items)

    # Validation failed
    assert result["success"] is False
    assert "validation_errors" in result

    # CRITICAL: No operations were performed
    assert len(operation_called) == 0
```

## Related Documentation

- [batch-exec-commands.md](../cli/batch-exec-commands.md) - Batch command design contract
- [testing.md](testing.md) - General testing patterns for erk
- [exec-script-schema-patterns.md](../cli/exec-script-schema-patterns.md) - TypedDict vs dataclass for batch results
