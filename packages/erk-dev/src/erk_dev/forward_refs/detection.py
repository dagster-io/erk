"""AST-based detection of forward reference violations.

This module provides utilities to detect Python files that are at risk of
forward reference errors due to TYPE_CHECKING imports without the required
`from __future__ import annotations` import.

## Why This Exists (Due Diligence)

We investigated whether existing tools (ruff, ty, pyright) could detect this
pattern before building our own solution. They cannot:

### ruff

- **FA102 (future-required-type-annotation)**: Only checks for PEP 585/604
  syntax (`list[int]`, `int | str`) without future annotations. Does NOT
  detect TYPE_CHECKING imports used in annotations.
  https://docs.astral.sh/ruff/rules/future-required-type-annotation/

- **TCH rules (flake8-type-checking)**: Help move imports INTO TYPE_CHECKING
  blocks, but assume you already have future annotations. No rule enforces
  that future annotations are present when TYPE_CHECKING imports exist.
  https://github.com/charliermarsh/ruff/issues/2214

### ty / pyright

Type checkers treat `TYPE_CHECKING` as `True` during static analysis, so
they "see" all the conditional imports. The error only manifests at runtime
when `TYPE_CHECKING` is `False` and Python tries to evaluate the annotation.
This is why type checkers cannot catch this class of bug.

### The Gap

There is no existing linter rule that enforces:
"If you have TYPE_CHECKING imports, you must have future annotations."

This module fills that gap with static AST analysis.

## The Pattern We Detect

This pattern causes NameError at runtime:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType  # Only imported at type-check time

def process(x: MyType) -> MyType:  # NameError: 'MyType' not defined
    return x
```

The fix is simple - add future annotations:

```python
from __future__ import annotations  # Makes annotations strings, not evaluated
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mymodule import MyType

def process(x: MyType) -> MyType:  # Works! Annotation is now a string
    return x
```
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ForwardRefViolation:
    """A detected forward reference violation.

    Represents a file that has TYPE_CHECKING imports but lacks the required
    `from __future__ import annotations` import.
    """

    filepath: Path
    message: str


def has_type_checking_imports(tree: ast.AST) -> bool:
    """Check if AST has an `if TYPE_CHECKING:` block containing imports.

    Detects both patterns:
    - `if TYPE_CHECKING:`
    - `if typing.TYPE_CHECKING:`

    Args:
        tree: Parsed AST of a Python module

    Returns:
        True if the module has TYPE_CHECKING imports, False otherwise
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        test = node.test

        # Pattern 1: `if TYPE_CHECKING:`
        is_bare_type_checking = isinstance(test, ast.Name) and test.id == "TYPE_CHECKING"

        # Pattern 2: `if typing.TYPE_CHECKING:`
        is_qualified_type_checking = (
            isinstance(test, ast.Attribute)
            and test.attr == "TYPE_CHECKING"
            and isinstance(test.value, ast.Name)
            and test.value.id == "typing"
        )

        if is_bare_type_checking or is_qualified_type_checking:
            # Check if the block contains any import statements
            for stmt in node.body:
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    return True

    return False


def has_future_annotations(tree: ast.AST) -> bool:
    """Check if AST has `from __future__ import annotations`.

    Args:
        tree: Parsed AST of a Python module

    Returns:
        True if the module has the future annotations import, False otherwise
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.module != "__future__":
            continue

        for alias in node.names:
            if alias.name == "annotations":
                return True

    return False


def check_source(source: str) -> ForwardRefViolation | None:
    """Check Python source code for forward reference violations.

    A violation occurs when:
    1. The source has TYPE_CHECKING imports
    2. The source lacks `from __future__ import annotations`

    Args:
        source: Python source code to check

    Returns:
        A ForwardRefViolation if a violation is detected, None otherwise.
        Returns None if the source cannot be parsed (syntax error).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # Cannot parse, cannot check
        return None

    if has_type_checking_imports(tree) and not has_future_annotations(tree):
        return ForwardRefViolation(
            filepath=Path("<string>"),
            message="TYPE_CHECKING imports without 'from __future__ import annotations'",
        )

    return None


def check_file(filepath: Path) -> ForwardRefViolation | None:
    """Check a Python file for forward reference violations.

    Args:
        filepath: Path to the Python file to check

    Returns:
        A ForwardRefViolation if a violation is detected, None otherwise.

    Raises:
        FileNotFoundError: If the file does not exist
        OSError: If the file cannot be read
        UnicodeDecodeError: If the file is not valid UTF-8
        SyntaxError: If the file contains invalid Python syntax
    """
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))

    if has_type_checking_imports(tree) and not has_future_annotations(tree):
        return ForwardRefViolation(
            filepath=filepath,
            message="TYPE_CHECKING imports without 'from __future__ import annotations'",
        )

    return None
