---
title: Gateway Testing Patterns
read_when:
  - "writing tests for gateway implementations"
  - "testing code that uses FakeGit"
  - "debugging test failures with gateway fakes"
---

# Gateway Testing Patterns

## FakeGit Property Access

### Subgateway Delegation Pattern

FakeGit delegates to subgateways, mirroring the real implementation structure. Properties must be accessed through their subgateway, not at the top level.

**Correct:**

```python
# Access staged_files through commit_ops subgateway
assert "myfile.md" in git.commit_ops.staged_files
```

**Incorrect:**

```python
# This will fail silently (empty list or AttributeError)
assert "myfile.md" in git.staged_files  # Wrong!
```

**Why this matters:**

- FakeGit mirrors real Git gateway architecture
- Accessing at wrong level gives empty results, causing confusing test failures
- Silent failure (empty list) is worse than AttributeError

**How to find the right path:**

1. Look at the method being called in implementation code
2. Find which subgateway (branch_ops, commit_ops, remote_ops) owns that method
3. Access the property via that same subgateway in tests

**Subgateway mapping:**

- `commit_ops` - staging, commits, `staged_files`
- `branch_ops` - branch creation, listing, current branch
- `remote_ops` - fetch, push, remote operations

## Related Topics

- [Fake-Driven Testing](../architecture/fake-driven-testing.md) - Overall fake architecture
- [Exec Script Testing](exec-script-testing.md) - Testing exec commands
