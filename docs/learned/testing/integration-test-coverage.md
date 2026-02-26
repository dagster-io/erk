---
title: Integration Test Scale Requirements
read_when:
  - "writing integration tests for batch operations"
  - "testing gateway methods that handle collections"
---

# Integration Test Scale Requirements

## Batch Operation Testing

When testing methods that operate on collections:

### Minimum Test Cases

1. **Empty case:** Zero items -> empty result
2. **Single item:** One item -> correct handling
3. **Multiple items:** 3-5 items -> batch behavior verified
4. **Edge cases:** Invalid items mixed with valid

### Why Multiple Items Matter

Batch operations may have bugs that only manifest with multiple items:

- Off-by-one errors in loop bounds
- Incorrect aggregation logic
- Race conditions in parallel processing

### Example: Batch Operation Tests

Tests for batch operations should cover at minimum:

- **Multiple items** — verifies correct aggregation with more than one entry
- **Error case** — verifies graceful handling when input is invalid

> **Source pointer:** See `get_all_branch_heads` tests in `tests/integration/test_real_git_branch_ops.py` for a canonical example.

## Related Topics

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) - Gateway testing patterns
- [Testing Documentation](index.md) - General testing patterns
