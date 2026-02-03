---
title: ABC Convenience Method Pattern
read_when:
  - "adding non-abstract methods to gateway ABCs"
  - "composing primitive gateway operations into higher-level methods"
  - "handling exception type differences between real and fake implementations"
last_audited: "2026-02-01 20:34 PT"
audit_result: edited
---

# ABC Convenience Method Pattern

Gateway ABCs can include **concrete (non-abstract) convenience methods** that compose primitive operations. These methods are defined once in the ABC and inherited by all implementations.

## When to Use

Use this pattern when:

- A common operation composes multiple primitive methods
- Error handling logic is complex and should be centralized
- You want to provide an ergonomic API without adding abstract methods

## Canonical Example

See `squash_branch_idempotent()` in `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py`. This wraps the primitive `squash_branch()` with idempotent error handling, returning a discriminated union (`SquashSuccess | SquashError`) instead of raising.

## Exception Type Compatibility

Real and fake implementations may raise different exception types:

| Implementation | Exception Type                  | Source                          |
| -------------- | ------------------------------- | ------------------------------- |
| Real           | `RuntimeError`                  | `run_subprocess_with_context()` |
| Fake           | `subprocess.CalledProcessError` | Direct raise for testing        |

**Solution**: Catch both types in the convenience method. See the `except` clause in `squash_branch_idempotent()` for the pattern.

## Benefits Over Abstract Methods

| Aspect         | Abstract Method (5 files)       | Convenience Method (1 file) |
| -------------- | ------------------------------- | --------------------------- |
| Implementation | abc, real, fake, dry_run, print | abc only                    |
| Maintenance    | High (5 places to update)       | Low (1 place)               |
| Testing        | Needs fake behavior             | Uses existing primitives    |
| Use case       | New primitive operation         | Composing existing ops      |

## When NOT to Use

Don't use convenience methods when:

- The operation requires implementation-specific behavior
- Performance characteristics differ between real/fake
- The operation needs dry-run/printing wrapper behavior

In those cases, add an abstract method following the [Gateway ABC Implementation Checklist](gateway-abc-implementation.md).

## Git vs Graphite View Divergence

Git commit counts (against trunk) can differ from Graphite's view (against parent branch) when local master hasn't been updated. The idempotent pattern handles this gracefully — "nothing to squash" is treated as success.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Adding abstract methods
- [Subprocess Wrappers](subprocess-wrappers.md) - Why real implementations raise RuntimeError
