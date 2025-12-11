---
name: dignified-python-313
description: This skill should be used when editing Python code in the erk codebase. Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception handling patterns, Python 3.13+ type syntax (list[str], str | None), pathlib operations, ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level. Also provides production-tested code smell patterns from Dagster Labs for API design, parameter complexity, and code organization. Essential for maintaining erk's dignified Python standards.
---

# Dignified Python - Python 3.13+ Coding Standards

Write explicit, predictable code that fails fast at proper boundaries.

---

## Quick Reference - Check Before Coding

| If you're about to write...                   | Check this rule                                                                                          |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `try:` or `except:`                           | → [Exception Handling](#1-exception-handling---never-for-control-flow-) - Default: let exceptions bubble |
| `from __future__ import annotations`          | → **FORBIDDEN** - Python 3.13+ doesn't need it                                                           |
| `List[...]`, `Dict[...]`, `Union[...]`        | → Use `list[...]`, `dict[...]`, `X \| Y`                                                                 |
| `dict[key]` without checking                  | → Use `if key in dict:` or `.get()`                                                                      |
| `path.resolve()` or `path.is_relative_to()`   | → Check `path.exists()` first                                                                            |
| `typing.Protocol`                             | → Use `abc.ABC` instead                                                                                  |
| `from .module import`                         | → Use absolute imports only                                                                              |
| `__all__ = ["..."]` in `__init__.py`          | → See references/core-standards.md#code-in-**init**py-and-**all**-exports                                |
| `print(...)` in CLI code                      | → Use `click.echo()`                                                                                     |
| `subprocess.run(...)`                         | → Add `check=True`                                                                                       |
| `@property` with I/O or expensive computation | → See references/core-standards.md#performance-expectations                                              |
| Function with many optional parameters        | → See references/code-smells-dagster.md                                                                  |
| `repr()` for sorting or hashing               | → See references/code-smells-dagster.md                                                                  |
| Context object passed everywhere              | → See references/code-smells-dagster.md                                                                  |
| Function with 10+ local variables             | → See references/code-smells-dagster.md                                                                  |
| Class with 50+ methods                        | → See references/code-smells-dagster.md                                                                  |

---

## CRITICAL RULES (Top 6)

### 1. Exception Handling - NEVER for Control Flow 🔴

**ALWAYS use LBYL (Look Before You Leap), NEVER EAFP**

```python
# ✅ CORRECT: Check before acting
if key in mapping:
    value = mapping[key]
else:
    handle_missing_key()

# ❌ WRONG: Using exceptions for control flow
try:
    value = mapping[key]
except KeyError:
    handle_missing_key()
```

**Details**: See `references/core-standards.md#exception-handling` for complete patterns

### 2. Type Annotations - Python 3.13+ Syntax Only 🔴

**FORBIDDEN**: `from __future__ import annotations`

```python
# ✅ CORRECT: Modern Python 3.13+ syntax
def process(items: list[str]) -> dict[str, int]: ...
def find_user(id: int) -> User | None: ...

# ❌ WRONG: Legacy syntax
from typing import List, Dict, Optional
def process(items: List[str]) -> Dict[str, int]: ...
```

**Details**: See `references/core-standards.md#type-annotations` for all patterns

### 3. Path Operations - Check Exists First 🔴

```python
# ✅ CORRECT: Check exists first
if path.exists():
    resolved = path.resolve()

# ❌ WRONG: Using exceptions
try:
    resolved = path.resolve()
except OSError:
    pass
```

**Details**: See `references/core-standards.md#path-operations`

### 4. Dependency Injection - ABC Not Protocol 🔴

```python
# ✅ CORRECT: Use ABC
from abc import ABC, abstractmethod

class MyOps(ABC):
    @abstractmethod
    def operation(self) -> None: ...

# ❌ WRONG: Using Protocol
from typing import Protocol
```

**Details**: See `references/core-standards.md#dependency-injection`

### 5. Imports - Module-Level and Absolute 🔴

**ALL imports must be at module level unless preventing circular imports**

```python
# ✅ CORRECT: Module-level, absolute imports
from erk.config import load_config
from pathlib import Path
import click

# ❌ WRONG: Inline imports (unless for circular import prevention)
def my_function():
    from erk.config import load_config  # WRONG unless circular import
    return load_config()

# ❌ WRONG: Relative imports
from .config import load_config
```

**Exception**: Inline imports are ONLY acceptable when preventing circular imports. Always document why:

```python
def create_context():
    # Inline import to avoid circular dependency with tests
    from tests.fakes.gitops import FakeGitOps
    return FakeGitOps()
```

**Details**: See `references/core-standards.md#imports`

### 6. No Silent Fallback Behavior 🔴

```python
# ❌ WRONG: Silent fallback
try:
    result = primary_method()
except:
    result = fallback_method()  # Untested, brittle

# ✅ CORRECT: Let error bubble up
result = primary_method()
```

**Details**: See `references/core-standards.md#anti-patterns`

---

## When to Load References

### Load `references/core-standards.md` when:

- Writing exception handling code (LBYL patterns)
- Working with type annotations (Python 3.13+ syntax)
- Implementing path operations (exists() checks)
- Creating ABC interfaces (dependency injection)
- Organizing imports (absolute imports, module-level)
- Working with CLI code (Click patterns)
- Using dataclasses and immutability
- Avoiding anti-patterns (silent fallback, exception swallowing)
- Implementing `@property` or `__len__` (performance expectations)

### Load `references/code-smells-dagster.md` when:

- Designing function APIs (default parameters, keyword arguments)
- Managing parameter complexity (parameter anxiety, invalid combinations)
- Refactoring large functions/classes (god classes, local variables)
- Working with context managers (assignment patterns)
- Using `repr()` programmatically (string representation abuse)
- Passing context objects (context coupling)
- Dealing with error boundaries (early validation)

### Load `references/patterns-reference.md` when:

- Developing CLI commands with Click
- Working with file I/O and pathlib
- Implementing dataclasses and frozen structures
- Managing subprocess operations
- Reducing code nesting (early returns, helper functions)

---

## Progressive Disclosure Guide

This skill uses a three-level loading system:

1. **This file (SKILL.md)**: Core rules and navigation (~350 lines)
2. **Reference files**: Detailed patterns and examples (loaded as needed)
3. **Quick lookup**: Use the tables above to find what you need

Claude loads reference files only when needed based on the current task. The reference files contain:

- **`core-standards.md`**: Foundational Python patterns from this skill
- **`code-smells-dagster.md`**: Production-tested anti-patterns from Dagster Labs
- **`patterns-reference.md`**: Common implementation patterns and examples

---

## Philosophy

**Write dignified Python code that:**

- Fails fast at proper boundaries (not deep in the stack)
- Makes invalid states unrepresentable (use the type system)
- Expresses intent clearly (LBYL over EAFP)
- Minimizes cognitive load (explicit over implicit)
- Enables confident refactoring (test what you build)

**Default stances:**

- Let exceptions bubble up (handle at boundaries only)
- Break APIs and migrate immediately (no unnecessary backwards compatibility)
- Check conditions proactively (LBYL)
- Use modern Python 3.13+ syntax

---

## Quick Decision Tree

**About to write Python code?**

1. **Using `try/except`?**
   - Can you use LBYL instead? → Do that
   - Is this an error boundary? → OK to handle
   - Otherwise → Let it bubble

2. **Using type hints?**
   - Use `list[str]`, `str | None`, not `List`, `Optional`
   - NO `from __future__ import annotations`

3. **Working with paths?**
   - Check `.exists()` before `.resolve()`
   - Use `pathlib.Path`, not `os.path`

4. **Writing CLI code?**
   - Use `click.echo()`, not `print()`
   - Exit with `raise SystemExit(1)`

5. **Too many parameters?**
   - See `references/code-smells-dagster.md#parameter-anxiety`

6. **Class getting large?**
   - See `references/code-smells-dagster.md#god-classes`

---

## Checklist Before Writing Code

Before writing `try/except`:

- [ ] Can I check the condition proactively? (LBYL)
- [ ] Is this at an error boundary? (CLI/API level)
- [ ] Am I adding meaningful context or just hiding the error?

Before using type hints:

- [ ] Am I using Python 3.13+ syntax? (`list`, `dict`, `|`)
- [ ] Have I removed all `typing` imports except essentials?

Before path operations:

- [ ] Did I check `.exists()` before `.resolve()`?
- [ ] Am I using `pathlib.Path`?
- [ ] Did I specify `encoding="utf-8"`?

Before adding backwards compatibility:

- [ ] Did the user explicitly request it?
- [ ] Is this a public API?
- [ ] Default: Break and migrate immediately

---

## Common Patterns Summary

| Scenario              | Preferred Approach                        | Avoid                                       |
| --------------------- | ----------------------------------------- | ------------------------------------------- |
| **Dictionary access** | `if key in dict:` or `.get(key, default)` | `try: dict[key] except KeyError:`           |
| **File existence**    | `if path.exists():`                       | `try: open(path) except FileNotFoundError:` |
| **Type checking**     | `if isinstance(obj, Type):`               | `try: obj.method() except AttributeError:`  |
| **Value validation**  | `if is_valid(value):`                     | `try: process(value) except ValueError:`    |
| **Path resolution**   | `if path.exists(): path.resolve()`        | `try: path.resolve() except OSError:`       |

---

## References

- **Core Standards**: `references/core-standards.md` - Detailed LBYL patterns, type annotations, imports
- **Code Smells**: `references/code-smells-dagster.md` - Production-tested anti-patterns
- **Pattern Reference**: `references/patterns-reference.md` - CLI, file I/O, dataclasses
- Python 3.13 docs: https://docs.python.org/3.13/
