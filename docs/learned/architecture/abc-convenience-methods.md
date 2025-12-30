---
title: ABC Convenience Method Pattern
read_when:
  - "adding non-abstract methods to gateway ABCs"
  - "composing primitive gateway operations into higher-level methods"
  - "handling exception type differences between real and fake implementations"
---

# ABC Convenience Method Pattern

Gateway ABCs can include **concrete (non-abstract) convenience methods** that compose primitive operations. These methods are defined once in the ABC and inherited by all implementations.

## When to Use

Use this pattern when:

- A common operation composes multiple primitive methods
- Error handling logic is complex and should be centralized
- You want to provide an ergonomic API without adding abstract methods

## Pattern: Idempotent Wrappers

The most common use case is wrapping a primitive operation with error handling that treats certain failures as success.

**Example: `squash_branch_idempotent()`**

The primitive `squash_branch()` raises an error when there's nothing to squash. The idempotent wrapper treats this as success:

```python
class Graphite(ABC):
    @abstractmethod
    def squash_branch(self, repo_root: Path, *, quiet: bool = False) -> None:
        """Primitive operation - raises on any failure."""
        ...

    def squash_branch_idempotent(
        self, repo_root: Path, *, quiet: bool = True
    ) -> SquashSuccess | SquashError:
        """Convenience method - handles 'nothing to squash' gracefully."""
        try:
            self.squash_branch(repo_root, quiet=quiet)
            return SquashSuccess(success=True, action="squashed", ...)
        except (RuntimeError, subprocess.CalledProcessError) as e:
            if "nothing to squash" in str(e).lower():
                return SquashSuccess(success=True, action="already_single_commit", ...)
            # Handle other errors...
```

## Exception Type Compatibility

A critical consideration: **real and fake implementations may raise different exception types**.

| Implementation | Exception Type                  | Source                          |
| -------------- | ------------------------------- | ------------------------------- |
| Real           | `RuntimeError`                  | `run_subprocess_with_context()` |
| Fake           | `subprocess.CalledProcessError` | Direct raise for testing        |

**Solution**: Catch both exception types:

```python
except (RuntimeError, subprocess.CalledProcessError) as e:
    # Build error message handling both types
    if isinstance(e, subprocess.CalledProcessError):
        error_msg = (e.stderr or "") + (e.stdout or "")
    else:
        error_msg = str(e)
```

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

A specific case this pattern solves: **git commit counts can differ from Graphite's view**.

- Git counts commits against trunk (master/main)
- Graphite counts commits against the Graphite parent branch
- When local master hasn't been updated, these counts diverge

The idempotent pattern handles this gracefully - if git thinks there are 2 commits but Graphite sees 1, the "nothing to squash" error is treated as success.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Adding abstract methods
- [Subprocess Wrappers](subprocess-wrappers.md) - Why real implementations raise RuntimeError
