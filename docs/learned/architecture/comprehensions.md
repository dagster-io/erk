---
title: Comprehension Readability Guidelines
read_when:
  - "writing dictionary or list comprehensions"
  - "reviewing code with complex comprehensions"
---

# Comprehension Readability Guidelines

## The One-Second Rule

If a comprehension takes more than one second to understand, extract intermediate variables.

## Pattern: Extract for Clarity

**Before (complex):**

```python
git_branch_heads = {
    branch_name: all_heads[branch_name]
    for branch_name, _ in branches_data
    if isinstance(branch_name, str) and branch_name in all_heads
}
```

**After (clearer):**

```python
tracked_branch_names = {name for name, _ in branches_data if isinstance(name, str)}
git_branch_heads = {
    name: all_heads[name]
    for name in tracked_branch_names
    if name in all_heads
}
```

## When to Use Single Comprehension

- Simple transformations: `{k: v.upper() for k, v in items.items()}`
- Single filter: `[x for x in items if x > 0]`
- No nested conditions

## When to Extract

- Multiple filters combined with `and`
- Type guards (`isinstance` checks)
- Nested comprehensions
- Accessing nested attributes

## Related Topics

- [Erk Architecture Patterns](erk-architecture.md) - General coding patterns
