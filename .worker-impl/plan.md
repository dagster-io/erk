# Documentation Plan: Lightweight __init__ Pattern

## Context

During implementation of the Codespace Registry (#5348, PR #5350), a PR review comment identified an architectural pattern that should be documented as a tripwire. The pattern was initially about registries but generalizes to all classes:

**Principle**: Class `__init__` methods should be lightweight and cheap - just data assignment. Heavy I/O operations (file reads, network calls, subprocess invocations) belong in static factory methods.

**Why this matters**:
- **Testability**: Tests can construct objects directly without I/O setup
- **Predictability**: Instantiation has no side effects
- **Explicit dependencies**: Heavy operations are visible at call sites
- **Flexibility**: Multiple construction paths (from file, from dict, for testing)

**Example pattern**:
```python
# CORRECT: __init__ is just data assignment
class ConfigRegistry:
    def __init__(self, items: list[Item], default: str | None) -> None:
        self._items = {item.name: item for item in items}
        self._default = default

    @classmethod
    def from_config_path(cls, path: Path) -> "ConfigRegistry":
        """Static factory that does the heavy I/O."""
        data = tomllib.loads(path.read_text())
        items = [Item.from_dict(d) for d in data.get("items", [])]
        return cls(items=items, default=data.get("default"))

# WRONG: __init__ does heavy I/O
class ConfigRegistry:
    def __init__(self, config_path: Path) -> None:
        data = tomllib.loads(config_path.read_text())  # Heavy I/O in __init__
        self._items = ...
```

**Existing code that follows this pattern**:
- `ErkContext` dataclass - pure data, factories do the work
- Gateway ABCs - implementations are lightweight, subprocess calls are in methods not init

**Existing code that violates this pattern** (to be addressed separately):
- `RealCodespaceRegistry` - loads from file in constructor
- `RealPlannerRegistry` - similar pattern

## Raw Materials

https://gist.github.com/schrockn/80223c509b2de9190f3c323354a79bba

## PR Review Insights

PR #5350 review comment from schrockn:
> This __init__ should receive the fully loaded data. There should be a static factory which translates from a config path. Mutation (save data) should be a in different codepath and we should reload a RealCodespaceRegistry, which should be an immutable object

Generalized to: Heavy I/O belongs in static factory methods, not `__init__`.

## Documentation Items

### 1. Add Tripwire: Lightweight __init__ Pattern

**Location**: `docs/learned/architecture/erk-architecture.md` (add new section) + tripwire

**Action**: Create

**Source**: [PR Review] PR #5350 comment

**Draft tripwire**:
```
**CRITICAL: Before adding file I/O, network calls, or subprocess invocations to a class __init__** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Class __init__ should be lightweight (just data assignment). Heavy operations belong in static factory methods like `from_config_path()` or `load()`. This enables direct instantiation in tests without I/O setup.
```

**Draft section for erk-architecture.md**:

```markdown
## Lightweight __init__ Pattern

Class `__init__` methods should be lightweight and cheap - just data assignment. Heavy I/O operations belong in static factory methods.

### Why

- **Testability**: Tests can construct objects directly without I/O setup
- **Predictability**: Instantiation has no side effects
- **Explicit dependencies**: Heavy operations are visible at call sites
- **Flexibility**: Multiple construction paths (from file, from dict, for testing)

### Pattern

```python
class Registry:
    def __init__(self, items: list[Item], default: str | None) -> None:
        """Lightweight - just assigns data."""
        self._items = {item.name: item for item in items}
        self._default = default

    @classmethod
    def from_config_path(cls, path: Path) -> "Registry":
        """Heavy I/O happens here, not in __init__."""
        data = tomllib.loads(path.read_text())
        items = [Item.from_dict(d) for d in data.get("items", [])]
        return cls(items=items, default=data.get("default"))
```

### Anti-pattern

```python
# WRONG: __init__ does heavy I/O
class Registry:
    def __init__(self, config_path: Path) -> None:
        data = tomllib.loads(config_path.read_text())  # Heavy I/O
        self._items = ...
```

### When This Applies

- Any class backed by file storage (TOML, JSON, etc.)
- Any class that calls subprocess on construction
- Any class that makes network requests on construction
- Any class where tests need to verify behavior without I/O

### Exceptions

- Gateway `real.py` implementations may do I/O in methods (that's their purpose)
- CLI commands that are thin wrappers around operations
```