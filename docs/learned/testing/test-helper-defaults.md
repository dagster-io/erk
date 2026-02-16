---
title: Test Helper Default Values
description: Avoiding test helper defaults that overlap with test data queries
read_when:
  - adding defaults to test helper functions
  - test failures after adding new filterable fields
  - query matching multiple fields unexpectedly
tripwires:
  - action: "adding defaults to test helper functions"
    warning: "Verify default doesn't overlap with common test data patterns. Use distinct values like 'helper-default-author' not 'test-user'."
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
---

# Test Helper Default Values

## The Anti-Pattern

Test helper defaults should not overlap with common test queries.

**Bad**: `make_plan_row(author="test-user")` - querying "user" now matches both title and author fields

**Good**: `make_plan_row(author="helper-default-author")` - distinct value won't accidentally match test data

## Why This Matters

When adding a new filterable field (like author), existing tests may break:

1. Test queries "user" expecting to match title "Add USER Authentication"
2. After adding author field with default "test-user", query matches both
3. Test expects 1 result, gets 2

## Prevention

When adding defaults to test helpers:

1. Check existing test data patterns in the test file
2. Verify default won't overlap with common test queries
3. Use fully distinct values that describe their purpose

## Example

<!-- Source: tests/unit/tui/providers/test_provider.py, make_plan_row -->

See `make_plan_row()` in `tests/unit/tui/providers/test_provider.py` - the `author` default should be distinguishable from any title content used in tests.
