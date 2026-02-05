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
last_audited: "2026-02-05"
audit_result: edited
---

# Exec Script Batch Testing

Batch exec commands require comprehensive test coverage across four categories: success cases, partial failures, validation errors, and JSON structure verification. This document outlines the test organization pattern and FakeGateway failure injection techniques.

## Test Organization Categories

Organize batch command tests into these four groups. See the reference implementation at `tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py` for a working example.

### 1. Success Cases

Test scenarios where all items in the batch succeed.

**What to cover:**

- Empty batch (no items)
- Single item batch
- Multiple items batch (typical: 2-3 items)
- Items with optional fields present/absent (e.g., explicit null comment vs omitted comment)

### 2. Partial Failure

Test scenarios where some items succeed and some fail.

**What to cover:**

- One item fails, rest succeed
- All items fail
- Mixed success/failure patterns

Top-level `success` field uses AND semantics: false if any item failed. Each individual result carries its own `success`, `error_type`, and `message` fields on failure.

### 3. Input Validation

Test scenarios where input is rejected before processing.

**What to cover:**

- Non-array JSON input (object instead of array)
- Non-object items in array (string instead of dict)
- Missing required fields (e.g., `thread_id`)
- Type mismatches (integer instead of string)
- Invalid JSON (parse failure)

Validation errors return a top-level error response with `success: false`, `error_type`, and `message`. No `results` array is present in validation error responses.

**Critical check:** Ensure no items were processed when validation fails (no side effects).

### 4. JSON Structure Verification

Test that output conforms to the expected schema for both success and error cases. Verify field presence, types, and nested structure correctness.

## FakeGateway Failure Injection Pattern

To test partial failures, inject failures into fake gateways via a failure set parameter.

### Pattern: Constructor-Injected Failure Set

`FakeGitHub` accepts a `resolve_thread_failures` parameter (type `set[str] | None`) in its constructor. When `resolve_review_thread()` is called with a thread ID in this set, it returns `False` to simulate failure. See the implementation in `packages/erk-shared/src/erk_shared/gateway/github/fake.py`.

Usage in tests:

```python
# Configure fake to fail on specific thread IDs
fake_github = FakeGitHub(resolve_thread_failures={"PRRT_2"})
```

### Why Set-Based Injection

**Advantages:**

- **Explicit**: Clear which items should fail
- **Flexible**: Can test any failure pattern (first, last, middle, scattered)
- **Type-safe**: Compile-time checking for thread ID typos
- **Testable**: Easy to verify the fake itself

**Alternative (anti-pattern): Stateful injection**

Do not use stateful approaches like `_should_fail_next` flags. These are order-dependent, brittle, and unclear about which item will fail. Set-based injection makes the failure configuration declarative and independent of processing order.

## Test File Organization

Batch command tests use plain functions (not test classes) organized with section comment headers. This follows the project convention of preferring `def test_*()` over `class Test*`. See the actual structure in `tests/unit/cli/commands/exec/scripts/test_resolve_review_threads.py`.

Tests use `CliRunner.invoke()` with `ErkContext.for_test()` for dependency injection -- never `monkeypatch` or `run_batch_command()` helpers. The fake gateway tracks mutations via read-only properties (e.g., `fake_github.resolved_thread_ids`, `fake_github.thread_replies`) for test assertions.

## Related Documentation

- [batch-exec-commands.md](../cli/batch-exec-commands.md) - Batch command design contract
- [testing.md](testing.md) - General testing patterns for erk
- [exec-script-schema-patterns.md](../cli/exec-script-schema-patterns.md) - TypedDict vs dataclass for batch results
