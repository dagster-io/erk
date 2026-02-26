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

### Example: get_all_branch_heads Tests

See `tests/integration/test_real_git_branch_ops.py`:

- `test_get_all_branch_heads_returns_all_branches` - Multiple branches
- `test_get_all_branch_heads_returns_empty_on_non_repo` - Error case

## Related Topics

- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) - Gateway testing patterns
- [Testing Documentation](index.md) - General testing patterns
