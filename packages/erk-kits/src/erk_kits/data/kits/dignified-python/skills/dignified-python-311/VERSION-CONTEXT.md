# Python 3.11 Context

## New in 3.11

- `Self` type available from `typing` module (PEP 673)
- Variadic generics with `TypeVarTuple` (PEP 646)
- Exception groups and `except*` syntax (PEP 654)
- Significantly improved error messages with better tracebacks
- Performance improvements (10-25% faster than 3.10)

## Type Annotation Features

Python 3.11 includes all 3.10 type features plus:

- `Self` type for methods returning instance of the class
- Better support for variadic generics (advanced use case)
- More precise type narrowing in control flow

### Self Type Example

Instead of:

```python
from typing import TypeVar
T = TypeVar("T", bound="MyClass")

class MyClass:
    def method(self: T) -> T:
        return self
```

Use:

```python
from typing import Self

class MyClass:
    def method(self) -> Self:
        return self
```

## Migrating from 3.10

Changes from 3.10 to 3.11:

- All 3.10 type syntax continues to work
- Can now use `Self` instead of bound TypeVar for self-returning methods
- Enjoy significantly better error messages

## References

- [PEP 673: Self Type](https://peps.python.org/pep-0673/)
- [Python 3.11 What's New](https://docs.python.org/3.11/whatsnew/3.11.html)
