# Python 3.12 Context

## New in 3.12

- PEP 695: Type Parameter Syntax (`def func[T](x: T) -> T`)
- Per-Interpreter GIL (subinterpreter improvements)
- Improved error messages with more precise locations
- F-string improvements (can now include debug expressions)
- Performance improvements continue

## Type Annotation Features

Python 3.12 includes all 3.11 type features plus:

- PEP 695 type parameter syntax for functions and classes
- Cleaner generic syntax without explicit `TypeVar` in most cases
- Type parameter bounds and constraints in new syntax

### PEP 695 Type Parameter Syntax

Instead of:

```python
from typing import TypeVar
T = TypeVar("T")

def func(x: T) -> T:
    return x
```

Use:

```python
def func[T](x: T) -> T:
    return x
```

For classes:

```python
# Old way:
from typing import Generic, TypeVar
T = TypeVar("T")

class Stack(Generic[T]):
    def push(self, item: T) -> None: ...

# New way:
class Stack[T]:
    def push(self, item: T) -> None: ...
```

## When to Still Use TypeVar

Use TypeVar for:

- Constrained type variables: `TypeVar("T", str, bytes)`
- Bound type variables with complex bounds
- Contra/covariant type variables

## Migrating from 3.11

Changes from 3.11 to 3.12:

- All 3.11 type syntax continues to work
- Can now use PEP 695 syntax for cleaner generic code
- Consider migrating simple generics to new syntax

## References

- [PEP 695: Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [Python 3.12 What's New](https://docs.python.org/3.12/whatsnew/3.12.html)
