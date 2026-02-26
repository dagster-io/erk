---
title: Subprocess check Parameter Patterns
read_when:
  - "writing subprocess.run calls"
  - "reviewing code with check=False"
  - "deciding between check=True and check=False"
---

# Subprocess check Parameter Patterns

## When check=True is Required

Use `check=True` for commands that MUST succeed for the operation to be valid:

- Destructive operations (git checkout, file writes)
- State-changing commands (git commit, API mutations)
- Commands where failure indicates a bug

## When check=False is Legitimate

Use `check=False` for query operations where failure is a valid outcome:

- Checking if a branch exists (non-zero = doesn't exist)
- Querying git state that may not be present
- Operations that handle their own error cases

**Pattern:**

```python
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
if result.returncode != 0:
    return {}  # Graceful degradation for query operations
```

## Automated Reviewer False Positives

Automated reviewers may flag `check=False` as a security concern. This is a false positive when:

1. The command is a query operation (read-only)
2. The code handles non-zero return codes explicitly
3. Graceful degradation is the intended behavior

Document the intent with a comment when using `check=False` to prevent repeated review comments.

## Related Topics

- [Subprocess Wrappers](subprocess-wrappers.md) - Wrapper functions for subprocess calls
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - Gateway patterns for subprocess usage
