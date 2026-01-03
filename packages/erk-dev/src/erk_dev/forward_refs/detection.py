"""AST-based detection of forward reference violations.

This module provides utilities to detect Python files that are at risk of
forward reference errors. See `erk_dev.forward_refs` module docstring for
the full rationale and due diligence on why existing tools don't cover this.
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
        Returns None if the file cannot be read or parsed.
    """
    if not filepath.exists():
        return None

    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Cannot read file
        return None

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        # Cannot parse, cannot check
        return None

    if has_type_checking_imports(tree) and not has_future_annotations(tree):
        return ForwardRefViolation(
            filepath=filepath,
            message="TYPE_CHECKING imports without 'from __future__ import annotations'",
        )

    return None
