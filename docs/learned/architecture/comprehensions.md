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
results = {
    key: lookup[key]
    for key, _ in raw_items
    if isinstance(key, str) and key in lookup
}
```

**After (clearer):**

```python
valid_keys = {k for k, _ in raw_items if isinstance(k, str)}
results = {k: lookup[k] for k in valid_keys if k in lookup}
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
