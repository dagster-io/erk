# Python 3.13 Context

## New in 3.13

- PEP 649: Deferred Evaluation of Annotations (built-in behavior)
- `from __future__ import annotations` is unnecessary and should NOT be used
- All modern type syntax works natively without future imports
- Further improved error messages and debugging support

## Type Annotation Changes

In Python 3.13, annotation evaluation is deferred by default. This means:

- No need for `from __future__ import annotations`
- Forward references work naturally
- Circular import issues with types are resolved

## Migrating from 3.12

If your code currently uses `from __future__ import annotations`:

- Remove the import statement
- All type syntax continues to work identically
- No other changes needed

## References

- [PEP 649: Deferred Evaluation of Annotations](https://peps.python.org/pep-0649/)
- [Python 3.13 What's New](https://docs.python.org/3.13/whatsnew/3.13.html)
