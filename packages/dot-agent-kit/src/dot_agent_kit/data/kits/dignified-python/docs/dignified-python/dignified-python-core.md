# Dignified Python - Core Standards

This document contains the core Python coding standards that apply to 80%+ of Python code. These principles are loaded with every skill invocation.

For conditional loading of specialized patterns:

- CLI development → Load `cli-patterns.md`
- Subprocess operations → Load `subprocess.md`

---

## The Cornerstone: LBYL Over EAFP

**Look Before You Leap: Check conditions proactively, NEVER use exceptions for control flow.**

This is the single most important rule in dignified Python. Every pattern below flows from this principle.

```python
# ✅ CORRECT: Check first
if key in mapping:
    value = mapping[key]
    process(value)

# ❌ WRONG: Exception as control flow
try:
    value = mapping[key]
    process(value)
except KeyError:
    pass
```

---

## Exception Handling

### Core Principle

**ALWAYS use LBYL, NEVER EAFP for control flow**

LBYL means checking conditions before acting. EAFP (Easier to Ask for Forgiveness than Permission) means trying operations and catching exceptions. In dignified Python, we strongly prefer LBYL.

### Dictionary Access Patterns

```python
# ✅ CORRECT: Membership testing
if key in mapping:
    value = mapping[key]
    process(value)
else:
    handle_missing()

# ✅ ALSO CORRECT: .get() with default
value = mapping.get(key, default_value)
process(value)

# ✅ CORRECT: Check before nested access
if "config" in data and "timeout" in data["config"]:
    timeout = data["config"]["timeout"]

# ❌ WRONG: KeyError as control flow
try:
    value = mapping[key]
except KeyError:
    handle_missing()
```

### When Exceptions ARE Acceptable

Exceptions are ONLY acceptable at:

1. **Error boundaries** (CLI/API level)
2. **Third-party API compatibility** (when no alternative exists)
3. **Adding context before re-raising**

#### 1. Error Boundaries

```python
# ✅ ACCEPTABLE: CLI command error boundary
@click.command("create")
@click.pass_obj
def create(ctx: ErkContext, name: str) -> None:
    """Create a worktree."""
    try:
        create_worktree(ctx, name)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Git command failed: {e.stderr}", err=True)
        raise SystemExit(1)
```

#### 2. Third-Party API Compatibility

```python
# ✅ ACCEPTABLE: Third-party API forces exception handling
def _get_bigquery_sample(sql_client, table_name):
    """
    BigQuery's TABLESAMPLE doesn't work on views.
    There's no reliable way to determine a priori whether
    a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        return sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")
```

#### 3. Adding Context Before Re-raising

```python
# ✅ ACCEPTABLE: Adding context before re-raising
try:
    process_file(config_file)
except yaml.YAMLError as e:
    raise ValueError(f"Failed to parse config file {config_file}: {e}") from e
```

### Exception Chaining (B904 Lint Compliance)

**Ruff rule B904** requires explicit exception chaining when raising inside an `except` block. This prevents losing the original traceback.

```python
# ✅ CORRECT: Chain to preserve context
try:
    parse_config(path)
except ValueError as e:
    click.echo(json.dumps({"success": False, "error": str(e)}))
    raise SystemExit(1) from e  # Preserves traceback

# ✅ CORRECT: Explicitly break chain when intentional
try:
    fetch_from_cache(key)
except KeyError:
    # Original exception is not relevant to caller
    raise ValueError(f"Unknown key: {key}") from None

# ❌ WRONG: Missing exception chain (B904 violation)
try:
    parse_config(path)
except ValueError:
    raise SystemExit(1)  # Lint error: missing 'from e' or 'from None'
```

**When to use each:**

- `from e` - Preserve original exception for debugging
- `from None` - Intentionally suppress original (e.g., transforming exception type)

### Exception Anti-Patterns

**❌ Never swallow exceptions silently**

```python
# ❌ WRONG: Silent exception swallowing
try:
    risky_operation()
except:
    pass

# ✅ CORRECT: Let exceptions bubble up
risky_operation()
```

**❌ Never use silent fallback behavior**

```python
# ❌ WRONG: Silent fallback masks failure
def process_text(text: str) -> dict:
    try:
        return llm_client.process(text)
    except Exception:
        return regex_parse_fallback(text)

# ✅ CORRECT: Let error bubble to boundary
def process_text(text: str) -> dict:
    return llm_client.process(text)
```

---

## Path Operations

### The Golden Rule

**ALWAYS check `.exists()` BEFORE `.resolve()` or `.is_relative_to()`**

### Why This Matters

- `.resolve()` raises `OSError` for non-existent paths
- `.is_relative_to()` raises `ValueError` for invalid comparisons
- Checking `.exists()` first avoids exceptions entirely (LBYL!)

### Correct Patterns

```python
from pathlib import Path

# ✅ CORRECT: Check exists first
for wt_path in worktree_paths:
    if wt_path.exists():
        wt_path_resolved = wt_path.resolve()
        if current_dir.is_relative_to(wt_path_resolved):
            current_worktree = wt_path_resolved
            break

# ❌ WRONG: Using exceptions for path validation
try:
    wt_path_resolved = wt_path.resolve()
    if current_dir.is_relative_to(wt_path_resolved):
        current_worktree = wt_path_resolved
except (OSError, ValueError):
    continue
```

### Pathlib Best Practices

**Always Use Pathlib (Never os.path)**

```python
# ✅ CORRECT: Use pathlib.Path
from pathlib import Path

config_file = Path.home() / ".config" / "app.yml"
if config_file.exists():
    content = config_file.read_text(encoding="utf-8")

# ❌ WRONG: Use os.path
import os.path
config_file = os.path.join(os.path.expanduser("~"), ".config", "app.yml")
```

**Always Specify Encoding**

```python
# ✅ CORRECT: Always specify encoding
content = path.read_text(encoding="utf-8")
path.write_text(data, encoding="utf-8")

# ❌ WRONG: Default encoding
content = path.read_text()  # Platform-dependent!
```

---

## Import Organization

### Core Rules

1. **Default: ALWAYS place imports at module level**
2. **Use absolute imports only** (no relative imports)
3. **Inline imports only for specific exceptions** (see below)

### Correct Import Patterns

```python
# ✅ CORRECT: Module-level imports
import json
import click
from pathlib import Path
from erk.config import load_config

def my_function() -> None:
    data = json.loads(content)
    click.echo("Processing")
    config = load_config()

# ❌ WRONG: Inline imports without justification
def my_function() -> None:
    import json  # NEVER do this
    import click  # NEVER do this
    data = json.loads(content)
```

### Legitimate Inline Import Patterns

#### 1. Circular Import Prevention

```python
# commands/sync.py
def register_commands(cli_group):
    """Register commands with CLI group (avoids circular import)."""
    from myapp.cli import sync_command  # Breaks circular dependency
    cli_group.add_command(sync_command)
```

**When to use:**

- CLI command registration
- Plugin systems with bidirectional dependencies
- Lazy loading to break import cycles

#### 2. Conditional Feature Imports

```python
def process_data(data: dict, dry_run: bool = False) -> None:
    if dry_run:
        # Inline import: Only needed for dry-run mode
        from myapp.dry_run import NoopProcessor
        processor = NoopProcessor()
    else:
        processor = RealProcessor()
    processor.execute(data)
```

**When to use:**

- Debug/verbose mode utilities
- Dry-run mode wrappers
- Optional feature modules
- Platform-specific implementations

#### 3. TYPE_CHECKING Imports

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from myapp.models import User  # Only for type hints

def process_user(user: "User") -> None:
    ...
```

**When to use:**

- Avoiding circular dependencies in type hints
- Forward declarations

### Absolute vs Relative Imports

```python
# ✅ CORRECT: Absolute import
from erk.config import load_config

# ❌ WRONG: Relative import
from .config import load_config
```

---

## Dependency Injection

### Core Rule

**Use ABC for interfaces, NEVER Protocol**

### ABC Interface Pattern

```python
# ✅ CORRECT: Use ABC for interfaces
from abc import ABC, abstractmethod

class Repository(ABC):
    @abstractmethod
    def save(self, entity: Entity) -> None:
        """Save entity to storage."""
        ...

    @abstractmethod
    def load(self, id: str) -> Entity:
        """Load entity by ID."""
        ...

class PostgresRepository(Repository):
    def save(self, entity: Entity) -> None:
        # Implementation
        pass

    def load(self, id: str) -> Entity:
        # Implementation
        pass

# ❌ WRONG: Using Protocol
from typing import Protocol

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...
    def load(self, id: str) -> Entity: ...
```

### Benefits of ABC

1. **Explicit inheritance** - Clear class hierarchy
2. **Runtime validation** - Errors if abstract methods not implemented
3. **Better IDE support** - Autocomplete and refactoring work better
4. **Documentation** - Clear contract definition

### Complete DI Example

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Define the interface
class DataStore(ABC):
    @abstractmethod
    def get(self, key: str) -> str | None:
        """Retrieve value by key."""
        ...

    @abstractmethod
    def set(self, key: str, value: str) -> None:
        """Store value with key."""
        ...

# Real implementation
class RedisStore(DataStore):
    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str) -> None:
        self.client.set(key, value)

# Fake for testing
class FakeStore(DataStore):
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        if key not in self._data:
            return None
        return self._data[key]

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

# Business logic accepts interface
@dataclass
class Service:
    store: DataStore  # Depends on abstraction

    def process(self, item: str) -> None:
        cached = self.store.get(item)
        if cached is None:
            result = expensive_computation(item)
            self.store.set(item, result)
        else:
            result = cached
        use_result(result)
```

---

## Performance Guidelines

### Properties Must Be O(1)

```python
# ❌ WRONG: Property doing I/O
@property
def size(self) -> int:
    return self._fetch_from_db()

# ✅ CORRECT: Explicit method name
def fetch_size_from_db(self) -> int:
    return self._fetch_from_db()

# ✅ CORRECT: O(1) property
@property
def size(self) -> int:
    return self._cached_size
```

### Magic Methods Must Be O(1)

```python
# ❌ WRONG: __len__ doing iteration
def __len__(self) -> int:
    return sum(1 for _ in self._items)

# ✅ CORRECT: O(1) __len__
def __len__(self) -> int:
    return self._count
```

---

## Anti-Patterns

### Preserving Unnecessary Backwards Compatibility

```python
# ❌ WRONG: Keeping old API unnecessarily
def process_data(data: dict, legacy_format: bool = False) -> Result:
    if legacy_format:
        return legacy_process(data)
    return new_process(data)

# ✅ CORRECT: Break and migrate immediately
def process_data(data: dict) -> Result:
    return new_process(data)
```

### No Re-Exports: One Canonical Import Path

**Core Principle:** Every symbol has exactly one import path. Never re-export.

This rule applies to:

- `__all__` exports in `__init__.py`
- Re-exporting symbols from other modules
- Shim modules that import and expose symbols from elsewhere

```python
# ❌ WRONG: __all__ exports create duplicate import paths
# myapp/__init__.py
from myapp.core import Process
__all__ = ["Process"]

# Now Process can be imported two ways - breaks grepability

# ❌ WRONG: Re-exporting symbols in a shim module
# myapp/compat.py
from myapp.core import Process, Config, execute
# These can now be imported from myapp.compat OR myapp.core

# ✅ CORRECT: Empty __init__.py, import from canonical location
# from myapp.core import Process

# ✅ CORRECT: Shim imports only what it needs for its own use
# myapp/cli_entry.py (needs the click command for CLI registration)
from myapp.core import main_command  # Only import what this module uses
# Other code imports Process, Config from myapp.core directly
```

**Why prohibited:**

1. Breaks grepability - hard to find all usages
2. Confuses static analysis tools
3. Impairs refactoring safety
4. Violates explicit > implicit
5. Creates confusion about canonical import location

**Shim modules:** When a module must exist as an entry point (e.g., for plugin systems or CLI registration), import only the minimum symbols needed for that purpose. Document that other symbols should be imported from the canonical location.

**When re-exports ARE required:** Some systems (like kit CLI entry points) require a module to exist at a specific path and expose a specific symbol. In these cases, use the explicit `import X as X` syntax to signal intentional re-export:

```python
# ✅ CORRECT: Explicit re-export syntax for required entry points
# This shim exists because the kit CLI system expects a module at this path
from myapp.core.feature import my_function as my_function

# ❌ WRONG: Plain import looks like unused import to linters
from myapp.core.feature import my_function  # ruff will flag as F401
```

The `as X` syntax is the PEP 484 standard for indicating intentional re-exports. It tells both linters and readers that this import is meant to be consumed from this module.

### Speculative Tests

```python
# ❌ FORBIDDEN: Tests for future features
# def test_feature_we_might_add():
#     pass

# ✅ CORRECT: TDD for current implementation
def test_feature_being_built_now():
    result = new_feature()
    assert result == expected
```

---

## Code Organization

### Indentation Depth Limit

**Maximum indentation: 4 levels**

```python
# ❌ WRONG: Too deeply nested
def process_items(items):
    for item in items:
        if item.valid:
            for child in item.children:
                if child.enabled:
                    for grandchild in child.descendants:
                        # 5 levels deep!
                        pass

# ✅ CORRECT: Extract helper functions
def process_items(items):
    for item in items:
        if item.valid:
            process_children(item.children)

def process_children(children):
    for child in children:
        if child.enabled:
            process_descendants(child.descendants)
```

---

## Backwards Compatibility Philosophy

**Default stance: NO backwards compatibility preservation**

Only preserve backwards compatibility when:

- Code is clearly part of public API
- User explicitly requests it
- Migration cost is prohibitively high (rare)

Benefits:

- Cleaner, maintainable codebase
- Faster iteration
- No legacy code accumulation
- Simpler mental models

---

## Decision Checklist

### Before writing `try/except`:

- [ ] Is this at an error boundary? (CLI/API level)
- [ ] Can I check the condition proactively? (LBYL)
- [ ] Am I adding meaningful context, or just hiding?
- [ ] Is third-party API forcing me to use exceptions?
- [ ] Have I encapsulated the violation?
- [ ] Am I catching specific exceptions, not broad?

**Default: Let exceptions bubble up**

### Before path operations:

- [ ] Did I check `.exists()` before `.resolve()`?
- [ ] Did I check `.exists()` before `.is_relative_to()`?
- [ ] Am I using `pathlib.Path`, not `os.path`?
- [ ] Did I specify `encoding="utf-8"`?

### Before preserving backwards compatibility:

- [ ] Did the user explicitly request it?
- [ ] Is this a public API with external consumers?
- [ ] Have I documented why it's needed?
- [ ] Is migration cost prohibitively high?

**Default: Break the API and migrate callsites immediately**

### Before inline imports:

- [ ] Is this to break a circular dependency?
- [ ] Is this for TYPE_CHECKING?
- [ ] Is this for conditional features?
- [ ] Have I documented why the inline import is needed?

**Default: Module-level imports**

### Before importing/re-exporting symbols:

- [ ] Is there already a canonical location for this symbol?
- [ ] Am I creating a second import path for the same symbol?
- [ ] If this is a shim module, am I importing only what's needed for this module's purpose?
- [ ] Have I avoided `__all__` exports?

**Default: Import from canonical location, never re-export**
