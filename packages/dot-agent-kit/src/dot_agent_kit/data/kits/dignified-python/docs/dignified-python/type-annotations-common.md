# Type Annotations - Common

This document contains type annotation guidance shared across all supported Python versions.

For version-specific features (PEP 695, type statement, deferred evaluation), see the version-specific delta files.

## Universal Philosophy

**Code Clarity:**

- Types serve as inline documentation
- Make function contracts explicit
- Reduce cognitive load when reading code
- Help understand data flow without tracing through implementation

**IDE Support:**

- Enable autocomplete and intelligent suggestions
- Catch typos and attribute errors before runtime
- Support refactoring tools (rename, move, extract)
- Provide jump-to-definition for typed objects

**Bug Prevention:**

- Catch type mismatches during static analysis
- Prevent None-related errors with explicit optional types
- Document expected input/output without running code
- Enable early detection of API contract violations

## Consistency Rules

**All public APIs:**

- 🔴 MUST: Type all function parameters (except `self` and `cls`)
- 🔴 MUST: Type all function return values
- 🔴 MUST: Type all class attributes
- 🟡 SHOULD: Type module-level constants

**Internal code:**

- 🟡 SHOULD: Type function signatures where helpful for clarity
- 🟢 MAY: Type complex local variables where type isn't obvious
- 🟢 MAY: Omit types for obvious cases (e.g., `count = 0`)

## Basic Collection Types

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

**Why**: Built-in types are more concise, don't require imports, and are the modern Python standard (available since 3.10).

## Union Types

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

## Optional Types

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

## Callable Types

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

## Interfaces: ABC vs Protocol

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

## General Best Practices

**Prefer specificity:**

```python
# ✅ GOOD - Specific
def get_config() -> dict[str, str | int]:
    ...

# ❌ WRONG - Too vague
def get_config() -> dict:
    ...
```

**Use Union sparingly:**

```python
# ✅ GOOD - Union only when necessary
def process(value: str | int) -> str:
    ...

# ❌ WRONG - Too permissive
def process(value: str | int | list | dict) -> str | None | list:
    ...
```

**Be explicit with None:**

```python
# ✅ GOOD - Explicit optional
def find_user(id: str) -> User | None:
    ...

# ❌ WRONG - Implicit None return
def find_user(id: str) -> User:
    return None  # Type checker error!
```

**Avoid Any when possible:**

```python
# ✅ GOOD - Specific type
def serialize(obj: User | Config) -> str:
    ...

# ❌ WRONG - Defeats purpose of types
from typing import Any
def serialize(obj: Any) -> str:
    ...
```

## When to Use Types

**Always type:**

- Public function signatures (parameters + return)
- Class attributes (including private ones)
- Function parameters that cross module boundaries
- Return values that aren't immediately obvious

**Type when helpful:**

- Complex local variables
- Closures and nested functions
- Lambda expressions used as callbacks

**Can skip:**

- Obvious cases: `count = 0`, `name = "example"`
- Trivial private helpers
- Test fixture setup code (if types add no clarity)

## Type Checking with Pyright

Dignified Python uses Pyright for static type checking:

```bash
# Check all files
pyright

# Check specific file
pyright src/mymodule.py

# Check with specific Python version
pyright --pythonversion 3.13
```

**Configuration** (in `pyproject.toml`):

```toml
[tool.pyright]
pythonVersion = "3.13"
strict = ["src/**/*.py"]
```

## Common Patterns

### Builder pattern with method chaining

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

### Container with get/set

```python
class Config:
    def __init__(self) -> None:
        self._data: dict[str, str | int] = {}

    def get(self, key: str) -> str | int | None:
        if key not in self._data:
            return None
        return self._data[key]

    def set(self, key: str, value: str | int) -> None:
        self._data[key] = value
```

### Factory function

```python
def create_user(data: dict[str, Any]) -> User | None:
    if "id" not in data or "name" not in data:
        return None
    return User(id=data["id"], name=data["name"])
```

## Anti-Patterns

**❌ Don't ignore type errors with `# type: ignore`**

```python
# ❌ WRONG - Hiding type error
result = unsafe_function()  # type: ignore

# ✅ CORRECT - Fix the type error
result: Expected = cast(Expected, unsafe_function())
```

**❌ Don't use bare Exception in type hints**

```python
# ❌ WRONG - No value from typing exception
def risky() -> str | Exception:
    ...

# ✅ CORRECT - Let exceptions bubble
def risky() -> str:
    ...  # Raises ValueError on error
```

**❌ Don't over-type simple cases**

```python
# ❌ WRONG - Obvious from context
def add_numbers(a: int, b: int) -> int:
    result: int = a + b  # Unnecessary type annotation
    return result

# ✅ CORRECT - Type only signature
def add_numbers(a: int, b: int) -> int:
    result = a + b  # Type is obvious
    return result
```
