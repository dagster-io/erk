---
title: Protocol vs ABC Interface Design Guide
read_when:
  - "choosing between Protocol and ABC for interface design"
  - "designing interfaces with structural vs nominal typing"
  - "working with frozen dataclasses and Protocol @property patterns"
tripwires:
  - action: "creating Protocol with bare attributes for frozen dataclasses"
    warning: "Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors."
---

# Protocol vs ABC: Interface Design Guide

A detailed guide for choosing between `typing.Protocol` and `abc.ABC` when designing interfaces in the erk codebase.

## Table of Contents

- [Quick Decision Tree](#quick-decision-tree)
- [Core Concepts](#core-concepts)
- [When to Use Protocol](#when-to-use-protocol)
- [When to Use ABC](#when-to-use-abc)
- [Protocol with @property for Frozen Dataclasses](#protocol-with-property-for-frozen-dataclasses)
- [Real-World Example: GtKit Refactoring](#real-world-example-gtkit-refactoring)
- [Common Pitfalls](#common-pitfalls)
- [Code Examples](#code-examples)

## Quick Decision Tree

```
Need an interface?
    │
    ├─► Does an existing type already satisfy the interface?
    │   │
    │   ├─► YES → Use Protocol (structural typing)
    │   │         Example: ErkContext already has git, gh, graphite attributes
    │   │
    │   └─► NO → Use ABC (nominal typing)
    │            Example: New Git implementation must explicitly inherit
    │
    └─► Should implementers explicitly declare they implement it?
        │
        ├─► YES → Use ABC
        │         Forces explicit inheritance, catches errors at definition time
        │
        └─► NO → Use Protocol
                 Duck typing, any matching shape works
```

## Core Concepts

### Structural vs Nominal Typing

**Protocol = Structural Typing (Duck Typing)**

- "If it walks like a duck and quacks like a duck, it's a duck"
- Any object with matching attributes/methods satisfies the Protocol
- No inheritance required
- Checked at type-check time, not runtime

**ABC = Nominal Typing**

- Explicit inheritance required
- Classes must declare they implement the interface
- Missing methods caught at class definition time
- Creates an inheritance hierarchy

### When Each Matters

| Scenario                               | Use                       | Reason                                       |
| -------------------------------------- | ------------------------- | -------------------------------------------- |
| Composite interface for existing types | Protocol                  | Existing types already satisfy it            |
| Implementation contract for new code   | ABC                       | Forces explicit implementation               |
| Consumer needs read-only view          | Protocol with `@property` | Accepts both mutable and immutable providers |
| Testing with fakes                     | ABC                       | Ensures fakes implement full interface       |

## When to Use Protocol

Use Protocol when:

1. **Existing types already satisfy the interface** - You're creating a "view" over existing types
2. **You want duck typing** - Any matching shape should work
3. **The interface is consumed, not implemented** - You're defining what you need, not what others must build

### Example: Composite Interface

```python
from typing import Protocol

from erk.integration.git import Git
from erk.integration.gh import GitHub
from erk.integration.graphite import Graphite


class GtKit(Protocol):
    """Interface for gt kit operations.

    This Protocol allows ErkContext to be used directly without
    creating wrapper classes or explicit inheritance.
    """

    @property
    def git(self) -> Git: ...

    @property
    def gh(self) -> GitHub: ...

    @property
    def graphite(self) -> Graphite: ...
```

**Why Protocol here?**

- `ErkContext` already has `git`, `gh`, and `graphite` attributes
- No code changes needed to `ErkContext`
- Any object with these attributes works

## When to Use ABC

Use ABC when:

1. **Defining implementation contracts** - Classes must explicitly implement
2. **Creating gateway interfaces** - `Git`, `GitHub`, `Graphite`, etc.
3. **You want fakes to inherit** - Ensures test fakes implement full interface
4. **You need runtime checks** - `isinstance()` checks work with ABC

### Example: Gateway Interface

```python
from abc import ABC, abstractmethod
from pathlib import Path


class Git(ABC):
    """Abstract interface for git operations."""

    @abstractmethod
    def current_branch(self) -> str:
        """Get the current branch name."""
        ...

    @abstractmethod
    def is_clean(self) -> bool:
        """Check if working tree is clean."""
        ...

    @abstractmethod
    def commit(self, message: str) -> None:
        """Create a commit with the given message."""
        ...
```

**Why ABC here?**

- `RealGit`, `FakeGit`, `DryRunGit` must all implement the same methods
- Missing methods are caught at class definition time
- `isinstance(git, Git)` works for runtime checks

## Protocol with @property for Frozen Dataclasses

### The Problem

When a Protocol needs to accept frozen dataclasses (which have read-only attributes), bare attribute declarations don't work:

```python
from dataclasses import dataclass
from typing import Protocol


# WRONG - won't work with frozen dataclasses
class BadProtocol(Protocol):
    name: str  # Bare attribute expects read-write


@dataclass(frozen=True)
class FrozenThing:
    name: str  # Read-only attribute


def use_it(thing: BadProtocol) -> None:
    print(thing.name)


# Type error! FrozenThing.name is read-only but BadProtocol.name is read-write
use_it(FrozenThing(name="test"))
```

### The Solution

Use `@property` decorators in the Protocol:

```python
from dataclasses import dataclass
from typing import Protocol


# CORRECT - works with frozen dataclasses
class GoodProtocol(Protocol):
    @property
    def name(self) -> str: ...  # Read-only property


@dataclass(frozen=True)
class FrozenThing:
    name: str


def use_it(thing: GoodProtocol) -> None:
    print(thing.name)


# Works! Read-only consumer accepts both read-only and read-write providers
use_it(FrozenThing(name="test"))
```

### Why This Works

- A read-only consumer (Protocol with `@property`) accepts:
  - Read-only providers (frozen dataclass attributes)
  - Read-write providers (regular class attributes)
- A read-write consumer (Protocol with bare attribute) only accepts:
  - Read-write providers

**Rule:** When defining a Protocol that will be consumed (not written to), always use `@property`.

## Real-World Example: GtKit Refactoring

### Background

The gt kit needed access to `git`, `gh`, and `graphite` gateways. Initially, we considered making `ErkContext` inherit from a base class, but that would require changes throughout the codebase.

### First Attempt: ABC (Failed)

```python
from abc import ABC, abstractmethod


class GtKit(ABC):
    @property
    @abstractmethod
    def git(self) -> Git: ...

    # ErkContext would need to explicitly inherit from GtKit
    # This requires changes to ErkContext and its tests
```

**Problem:** Required modifying `ErkContext` to inherit from `GtKit`.

### Second Attempt: Protocol with Bare Attributes (Failed)

```python
from typing import Protocol


class GtKit(Protocol):
    git: Git
    gh: GitHub
    graphite: Graphite
```

**Problem:** `ErkContext` is a frozen dataclass with read-only attributes. Bare attribute declarations in Protocol expect read-write access.

### Final Solution: Protocol with @property (Success)

```python
from typing import Protocol


class GtKit(Protocol):
    """Interface for gt kit operations.

    Uses @property to accept frozen dataclasses with read-only attributes.
    """

    @property
    def git(self) -> Git: ...

    @property
    def gh(self) -> GitHub: ...

    @property
    def graphite(self) -> Graphite: ...
```

**Result:**

- `ErkContext` works without modification
- Frozen dataclass compatibility preserved
- Type checker validates structural compatibility

## Common Pitfalls

### Pitfall 1: Using Protocol When You Need Fake Testing

```python
# WRONG - Fakes won't be forced to implement all methods
class Git(Protocol):
    def commit(self, message: str) -> None: ...
    def push(self) -> None: ...


class FakeGit:
    def commit(self, message: str) -> None:
        pass
    # Forgot to implement push() - no error!
```

**Fix:** Use ABC for interfaces that will have fakes.

### Pitfall 2: Using ABC When Type Already Satisfies Interface

```python
# WRONG - Requires ErkContext to inherit from GtKit
class GtKit(ABC):
    @property
    @abstractmethod
    def git(self) -> Git: ...


# ErkContext already has a git property, but doesn't inherit from GtKit
# Type error when passing ErkContext where GtKit is expected
```

**Fix:** Use Protocol for composite interfaces over existing types.

### Pitfall 3: Forgetting @property in Protocol for Frozen Dataclasses

```python
# WRONG - bare attribute expects read-write
class MyProtocol(Protocol):
    value: int


@dataclass(frozen=True)
class MyData:
    value: int


def process(data: MyProtocol) -> None:
    pass


process(MyData(value=42))  # Type error!
```

**Fix:** Use `@property` when the Protocol will accept frozen dataclasses.

### Pitfall 4: Mixing Up Consumer vs Provider Perspective

```python
# The Protocol defines what the CONSUMER needs
# Not what the PROVIDER must exactly match

class Consumer(Protocol):
    @property
    def name(self) -> str: ...  # Consumer only reads


class Provider:
    name: str  # Provider can be read-write (more permissive)


def consume(thing: Consumer) -> None:
    print(thing.name)  # Consumer only reads


p = Provider()
p.name = "test"
consume(p)  # Works! Read-write satisfies read-only
```

## Code Examples

### Complete ABC Pattern (Gateway Layer)

```python
from abc import ABC, abstractmethod
from pathlib import Path


class Git(ABC):
    """Git operations interface."""

    @abstractmethod
    def current_branch(self) -> str:
        """Get current branch name."""
        ...

    @abstractmethod
    def is_clean(self) -> bool:
        """Check if working tree has no uncommitted changes."""
        ...


class RealGit(Git):
    """Real git implementation using subprocess."""

    def __init__(self, repo_path: Path) -> None:
        self._repo_path = repo_path

    def current_branch(self) -> str:
        # Real implementation
        ...

    def is_clean(self) -> bool:
        # Real implementation
        ...


class FakeGit(Git):
    """In-memory fake for testing."""

    def __init__(self) -> None:
        self._branch = "main"
        self._clean = True

    def current_branch(self) -> str:
        return self._branch

    def is_clean(self) -> bool:
        return self._clean
```

### Complete Protocol Pattern (Composite Interface)

```python
from dataclasses import dataclass
from typing import Protocol


class HasGit(Protocol):
    @property
    def git(self) -> Git: ...


class HasGitHub(Protocol):
    @property
    def gh(self) -> GitHub: ...


class FullContext(Protocol):
    """Composite interface for operations needing multiple gateways."""

    @property
    def git(self) -> Git: ...

    @property
    def gh(self) -> GitHub: ...

    @property
    def graphite(self) -> Graphite: ...


@dataclass(frozen=True)
class ErkContext:
    """Main context object - satisfies FullContext without inheritance."""

    git: Git
    gh: GitHub
    graphite: Graphite


def do_something(ctx: FullContext) -> None:
    """Accepts ErkContext or any other matching type."""
    branch = ctx.git.current_branch()
    ctx.gh.create_pr(branch)
```

## Summary

| Aspect           | Protocol             | ABC                      |
| ---------------- | -------------------- | ------------------------ |
| Typing           | Structural (duck)    | Nominal (explicit)       |
| Inheritance      | Not required         | Required                 |
| Error detection  | Type-check time      | Definition time          |
| Frozen dataclass | Use `@property`      | N/A                      |
| Best for         | Composite interfaces | Implementation contracts |
| Testing fakes    | Avoid                | Recommended              |

## Related Documentation

- [Erk Architecture](./erk-architecture.md) - Core architectural patterns
- [Fake-Driven Testing](./fake-driven-testing.md) - Testing with fakes
