# Type Annotations - Python 3.13

This document provides complete, canonical type annotation guidance for Python 3.13.

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

**Available from 3.10:**

- Built-in generic types: `list[T]`, `dict[K, V]`, etc.
- Union types with `|` operator
- Optional with `X | None`

**What you need from typing module:**

- `Self` for self-returning methods
- `TypeVar` only for constrained/bounded generics
- `Protocol` for structural typing (rare - prefer ABC)
- `TYPE_CHECKING` for conditional imports
- `Any` (use sparingly)

## Complete Type Annotation Syntax for Python 3.13

### Basic Collection Types

✅ **PREFERRED** - Use built-in generic types:

```python
names: list[str] = []
mapping: dict[str, int] = {}
unique_ids: set[str] = set()
coordinates: tuple[int, int] = (0, 0)
```

❌ **WRONG** - Don't use typing module equivalents:

```python
from typing import List, Dict, Set, Tuple  # Don't do this
names: List[str] = []
```

### Union Types

✅ **PREFERRED** - Use `|` operator:

```python
def process(value: str | int) -> str:
    return str(value)

def find_config(name: str) -> dict[str, str] | dict[str, int]:
    ...

# Multiple unions
def parse(input: str | int | float) -> str:
    return str(input)
```

❌ **WRONG** - Don't use `typing.Union`:

```python
from typing import Union
def process(value: Union[str, int]) -> str:  # Don't do this
    ...
```

### Optional Types

✅ **PREFERRED** - Use `X | None`:

```python
def find_user(id: str) -> User | None:
    """Returns user or None if not found."""
    if id in users:
        return users[id]
    return None
```

❌ **WRONG** - Don't use `typing.Optional`:

```python
from typing import Optional
def find_user(id: str) -> Optional[User]:  # Don't do this
    ...
```

### Self Type for Self-Returning Methods

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

### Generic Functions with PEP 695

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

### Generic Classes with PEP 695

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

### Type Parameter Bounds

✅ **Use bounds with PEP 695**:

```python
class Comparable:
    def compare(self, other: object) -> int:
        ...

def max_value[T: Comparable](items: list[T]) -> T:
    """Get maximum value from comparable items."""
    return max(items, key=lambda x: x)
```

### Constrained TypeVars (Still Use TypeVar)

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

### Type Aliases with type Statement

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

### Callable Types

✅ **PREFERRED** - Use `collections.abc.Callable`:

```python
from collections.abc import Callable

# Function that takes int, returns str
processor: Callable[[int], str] = str

# Function with no args, returns None
callback: Callable[[], None] = lambda: None

# Function with multiple args
validator: Callable[[str, int], bool] = lambda s, i: len(s) > i
```

### Forward References and Circular Imports (NEW in 3.13)

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

### Interfaces: ABC vs Protocol

✅ **PREFERRED** - Use ABC for interfaces:

```python
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def get(self, id: str) -> User | None:
        """Get user by ID."""

    @abstractmethod
    def save(self, user: User) -> None:
        """Save user."""
```

🟡 **VALID** - Use Protocol only for structural typing:

```python
from typing import Protocol

class Drawable(Protocol):
    def draw(self) -> None: ...

def render(obj: Drawable) -> None:
    obj.draw()
```

**Dignified Python prefers ABC** because it makes inheritance and intent explicit.

## Complete Examples

### Tree Structure with Natural Forward References

```python
from typing import Self

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
        from collections.abc import Callable

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
node = root.find(lambda x: x == 2)  # Type: Node[int] | None
```

### Generic Repository with PEP 695

```python
from abc import ABC, abstractmethod
from typing import Self

class Repository[T]:
    """Abstract repository - generic parameter with PEP 695."""

    @abstractmethod
    def get(self, id: str) -> T | None:
        """Get entity by ID."""

    @abstractmethod
    def save(self, entity: T) -> Self:
        """Save entity, return self for chaining."""

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity, return success."""

    def get_or_fail(self, id: str) -> T:
        """Get entity or raise error."""
        entity = self.get(id)
        if entity is None:
            raise ValueError(f"Entity not found: {id}")
        return entity

class InMemoryRepository[T](Repository[T]):
    """In-memory repository implementation."""

    def __init__(self) -> None:
        self._storage: dict[str, T] = {}

    def get(self, id: str) -> T | None:
        return self._storage.get(id)

    def save(self, entity: T) -> Self:
        entity_id = str(getattr(entity, "id", id(entity)))
        self._storage[entity_id] = entity
        return self

    def delete(self, id: str) -> bool:
        if id in self._storage:
            del self._storage[id]
            return True
        return False

# Usage
from dataclasses import dataclass

@dataclass
class User:
    id: str
    name: str

repo = InMemoryRepository[User]()
repo.save(User("1", "Alice")).save(User("2", "Bob"))
user = repo.get("1")  # Type: User | None
```

### Complex Recursive Types

```python
# Recursive type - works naturally in 3.13!
type JsonValue = dict[str, JsonValue] | list[JsonValue] | str | int | float | bool | None

def parse_json(text: str) -> JsonValue:
    """Parse JSON text to JsonValue."""
    import json
    return json.loads(text)

def validate_config(data: JsonValue) -> bool:
    """Validate configuration data."""
    if not isinstance(data, dict):
        return False
    # Validation logic...
    return True

# Generic result type with recursive structure
type Result[T] = tuple[T, str | None]
type NestedResult[T] = Result[T | NestedResult[T]]

def deep_parse(value: str, depth: int) -> NestedResult[int]:
    """Parse with nested results."""
    if depth == 0:
        try:
            return (int(value), None)
        except ValueError as e:
            return (0, str(e))
    # Recursive parsing...
    return ((int(value), None), None)
```

### Builder Pattern with Self and Generics

```python
from typing import Self

class QueryBuilder[T]:
    """Generic query builder with fluent interface."""

    def __init__(self, result_type: type[T]) -> None:
        self._result_type = result_type
        self._filters: list[str] = []
        self._limit: int | None = None

    def filter(self, condition: str) -> Self:
        """Add filter condition."""
        self._filters.append(condition)
        return self

    def limit(self, n: int) -> Self:
        """Set result limit."""
        self._limit = n
        return self

    def build(self) -> str:
        """Build query string."""
        query = " AND ".join(self._filters)
        if self._limit:
            query += f" LIMIT {self._limit}"
        return query

# Usage
from dataclasses import dataclass

@dataclass
class User:
    name: str
    age: int

builder = QueryBuilder[User](User)
query = (
    builder
    .filter("active = true")
    .filter("age > 18")
    .limit(10)
    .build()
)
```

### Circular Module References

```python
# models/user.py
from models.post import Post  # Import works!

class User:
    """User model with posts."""

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name
        self.posts: list[Post] = []

    def add_post(self, post: Post) -> None:
        """Add post to user."""
        self.posts.append(post)

# models/post.py
from models.user import User  # Circular import works!

class Post:
    """Post model with author."""

    def __init__(self, id: str, title: str, author: User) -> None:
        self.id = id
        self.title = title
        self.author = author

# No __future__ import needed - PEP 649 handles it!
```

## Type Checking Rules

### What to Type

✅ **MUST type**:

- All public function parameters (except `self`, `cls`)
- All public function return values
- All class attributes (public and private)
- Module-level constants

🟡 **SHOULD type**:

- Internal function signatures
- Complex local variables

🟢 **MAY skip**:

- Simple local variables where type is obvious (`count = 0`)
- Lambda parameters in short inline lambdas
- Loop variables in short comprehensions

### Running Type Checker

```bash
uv run pyright
```

All code should pass type checking without errors.

### Type Checking Configuration

Use strict mode in `pyproject.toml`:

```toml
[tool.pyright]
strict = true
```

## Common Patterns

### Checking for None

✅ **CORRECT** - Check before use:

```python
def process_user(user: User | None) -> str:
    if user is None:
        return "No user"
    return user.name
```

### Dict.get() with Type Safety

✅ **CORRECT** - Handle None case:

```python
def get_port(config: dict[str, int]) -> int:
    port = config.get("port")
    if port is None:
        return 8080
    return port
```

### List Operations

✅ **CORRECT** - Check before accessing:

```python
def first_or_default[T](items: list[T], default: T) -> T:
    if not items:
        return default
    return items[0]
```

## Critical Guidelines for Python 3.13

### DO NOT use from **future** import annotations

🔴 **FORBIDDEN** in Python 3.13:

```python
from __future__ import annotations  # DON'T DO THIS
```

**Why:**

- PEP 649 provides superior deferred evaluation by default
- Forward references work naturally without it
- Circular imports work naturally without it
- Using it masks the improved 3.13 behavior
- It's unnecessary and can cause confusion

### DO use natural forward references

✅ **CORRECT** - Just write the type naturally:

```python
class Node:
    def __init__(self, parent: Node | None = None):  # Works!
        self.parent = parent
```

❌ **WRONG** - Don't use quoted strings:

```python
class Node:
    def __init__(self, parent: "Node | None" = None):  # Unnecessary
        self.parent = parent
```

## When to Use PEP 695 vs TypeVar

**Use PEP 695 for**:

- Simple generic functions (no constraints/bounds)
- Simple generic classes
- Most common generic use cases
- New code

**Still use TypeVar for**:

- Constrained type variables: `TypeVar("T", str, bytes)`
- Bound type variables with complex bounds
- Covariant/contravariant type variables
- Reusing same TypeVar across multiple functions

## Migration from Python 3.12

If upgrading from Python 3.12:

1. **Remove `from __future__ import annotations`**:
   - It's no longer needed
   - PEP 649 provides better behavior

2. **Remove quoted forward references**:
   - `parent: "Node"` → `parent: Node`
   - Just works naturally now

3. **Simplify circular imports**:
   - Remove `TYPE_CHECKING` guards if only used for annotations
   - Direct imports now work fine

4. **All existing 3.12 syntax continues to work**:
   - PEP 695 syntax still preferred
   - `Self` type still preferred
   - `type` statement still preferred
   - Union with `|` still preferred

## References

- [PEP 649: Deferred Evaluation of Annotations](https://peps.python.org/pep-0649/)
- [Python 3.13 What's New](https://docs.python.org/3.13/whatsnew/3.13.html)
