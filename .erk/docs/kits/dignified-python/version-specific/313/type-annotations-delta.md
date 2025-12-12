# Type Annotations - Python 3.13 Delta

This document contains type annotation features specific to Python 3.13.

For common type annotation guidance (Basic Collection Types, Union Types, Optional, Callable, etc.), see `type-annotations-common.md`.

## Overview

Python 3.13 implements PEP 649 (Deferred Evaluation of Annotations), fundamentally changing how annotations are evaluated. **The key change: forward references and circular imports work naturally without `from __future__ import annotations`.**

All type features from previous versions (3.10-3.12) continue to work.

**What's new in 3.13:**

- PEP 649 deferred annotation evaluation
- Forward references work naturally (no quotes, no `from __future__`)
- Circular imports no longer cause annotation errors
- **DO NOT use `from __future__ import annotations`**

**Available from 3.12:**

- PEP 695 type parameter syntax: `def func[T](x: T) -> T`
- `type` statement for better type aliases

**Available from 3.11:**

- `Self` type for self-returning methods

## Self Type for Self-Returning Methods (3.11+)

✅ **PREFERRED** - Use Self for methods that return the instance:

```python
from typing import Self

class Builder:
    def set_name(self, name: str) -> Self:
        self.name = name
        return self

    def set_value(self, value: int) -> Self:
        self.value = value
        return self
```

## Generic Functions with PEP 695 (3.12+)

✅ **PREFERRED** - Use PEP 695 type parameter syntax:

```python
def first[T](items: list[T]) -> T | None:
    """Return first item or None if empty."""
    if not items:
        return None
    return items[0]

def identity[T](value: T) -> T:
    """Return value unchanged."""
    return value

# Multiple type parameters
def zip_dicts[K, V](keys: list[K], values: list[V]) -> dict[K, V]:
    """Create dict from separate key and value lists."""
    return dict(zip(keys, values))
```

🟡 **VALID** - TypeVar still works:

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T | None:
    if not items:
        return None
    return items[0]
```

**Note**: Prefer PEP 695 syntax for simple generics. TypeVar is still needed for constraints/bounds.

## Generic Classes with PEP 695 (3.12+)

✅ **PREFERRED** - Use PEP 695 class syntax:

```python
class Stack[T]:
    """A generic stack data structure."""

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> Self:
        self._items.append(item)
        return self

    def pop(self) -> T | None:
        if not self._items:
            return None
        return self._items.pop()

# Usage
int_stack = Stack[int]()
int_stack.push(42).push(43)
```

🟡 **VALID** - Generic with TypeVar still works:

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []
    # ... rest of implementation
```

**Note**: PEP 695 is cleaner - no imports needed, type parameter scope is local to class.

## Type Parameter Bounds (3.12+)

✅ **Use bounds with PEP 695**:

```python
class Comparable:
    def compare(self, other: object) -> int:
        ...

def max_value[T: Comparable](items: list[T]) -> T:
    """Get maximum value from comparable items."""
    return max(items, key=lambda x: x)
```

## Constrained TypeVars (Still Use TypeVar)

✅ **Use TypeVar for specific type constraints**:

```python
from typing import TypeVar

# Constrained to specific types - must use TypeVar
Numeric = TypeVar("Numeric", int, float)

def add(a: Numeric, b: Numeric) -> Numeric:
    return a + b
```

❌ **WRONG** - PEP 695 doesn't support constraints:

```python
# This doesn't constrain to int|float
def add[Numeric](a: Numeric, b: Numeric) -> Numeric:
    return a + b
```

## Type Aliases with type Statement (3.12+)

✅ **PREFERRED** - Use `type` statement:

```python
# Simple alias
type UserId = str
type Config = dict[str, str | int | bool]

# Generic type alias
type Result[T] = tuple[T, str | None]

def process(value: str) -> Result[int]:
    try:
        return (int(value), None)
    except ValueError as e:
        return (0, str(e))
```

🟡 **VALID** - Simple assignment still works:

```python
UserId = str  # Still valid
Config = dict[str, str | int | bool]  # Still valid
```

**Note**: `type` statement is more explicit and works better with generics.

## Forward References and Circular Imports (NEW in 3.13)

✅ **CORRECT** - Just works naturally with PEP 649:

```python
# Forward reference - no quotes needed!
class Node:
    def __init__(self, value: int, parent: Node | None = None):
        self.value = value
        self.parent = parent

# Circular imports - just works!
# a.py
from b import B

class A:
    def method(self) -> B:
        ...

# b.py
from a import A

class B:
    def method(self) -> A:
        ...

# Recursive types - no future needed!
type JsonValue = dict[str, JsonValue] | list[JsonValue] | str | int | float | bool | None
```

❌ **WRONG** - Don't use `from __future__ import annotations`:

```python
from __future__ import annotations  # DON'T DO THIS in Python 3.13

class Node:
    def __init__(self, value: int, parent: Node | None = None):
        ...
```

**Why avoid `from __future__ import annotations` in 3.13:**

- Unnecessary - PEP 649 provides better default behavior
- Can cause confusion
- Masks the native 3.13 deferred evaluation
- Prevents you from leveraging improvements

## Complete Examples

### Tree Structure with Natural Forward References

```python
from typing import Self
from collections.abc import Callable

class Node[T]:
    """Tree node - forward reference works naturally in 3.13!"""

    def __init__(
        self,
        value: T,
        parent: Node[T] | None = None,  # Forward ref, no quotes!
        children: list[Node[T]] | None = None,  # Forward ref, no quotes!
    ) -> None:
        self.value = value
        self.parent = parent
        self.children = children or []

    def add_child(self, child: Node[T]) -> Self:
        """Add child and return self for chaining."""
        self.children.append(child)
        child.parent = self
        return self

    def find(self, predicate: Callable[[T], bool]) -> Node[T] | None:
        """Find first node matching predicate."""
        if predicate(self.value):
            return self

        for child in self.children:
            result = child.find(predicate)
            if result:
                return result

        return None

# Usage - all type-safe with no __future__ import!
root = Node[int](1)
root.add_child(Node[int](2)).add_child(Node[int](3))
```

### Generic Repository with PEP 695

```python
from abc import ABC, abstractmethod
from typing import Self

class Entity[T]:
    """Base class for entities."""

    def __init__(self, id: T) -> None:
        self.id = id

class Repository[T](ABC):
    """Generic repository interface."""

    @abstractmethod
    def get(self, id: str) -> T | None:
        """Get entity by ID."""

    @abstractmethod
    def save(self, entity: T) -> None:
        """Save entity."""

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity, return True if deleted."""

class User(Entity[str]):
    def __init__(self, id: str, name: str) -> None:
        super().__init__(id)
        self.name = name

class UserRepository(Repository[User]):
    def __init__(self) -> None:
        self._users: dict[str, User] = {}

    def get(self, id: str) -> User | None:
        if id not in self._users:
            return None
        return self._users[id]

    def save(self, entity: User) -> None:
        self._users[entity.id] = entity

    def delete(self, id: str) -> bool:
        if id not in self._users:
            return False
        del self._users[id]
        return True
```

## Migration from 3.10/3.11

If migrating from Python 3.10/3.11:

1. **Remove `from __future__ import annotations`** - No longer needed
2. **Consider upgrading to PEP 695 syntax** - Cleaner generics
3. **Use `type` statement for aliases** - More explicit than assignment
4. **Remove quoted forward references** - They work naturally now

```python
# Python 3.10/3.11
from __future__ import annotations
from typing import TypeVar, Generic

T = TypeVar("T")

class Node(Generic[T]):
    def __init__(self, value: T, parent: "Node[T] | None" = None):
        ...

# Python 3.13
from typing import Self

class Node[T]:
    def __init__(self, value: T, parent: Node[T] | None = None):
        ...
```

## What typing imports are still needed?

**Very rare:**

- `TypeVar` - Only for constrained/bounded type variables
- `Any` - Use sparingly when type truly unknown
- `Protocol` - Structural typing (prefer ABC)
- `TYPE_CHECKING` - Conditional imports to avoid circular dependencies

**Never needed:**

- `List`, `Dict`, `Set`, `Tuple` - Use built-in types
- `Union` - Use `|` operator
- `Optional` - Use `X | None`
- `Generic` - Use PEP 695 class syntax
