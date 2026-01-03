"""Tests to prevent forward reference errors from TYPE_CHECKING imports.

This module provides two layers of protection:

1. Runtime import test: Catches actual NameError failures when modules are imported
2. Static analysis test: Detects the risky pattern proactively before it causes errors

The pattern we're preventing:
- Types imported under `if TYPE_CHECKING:` (only available at type-check time)
- Those types used in annotations with `|` union syntax
- File lacks `from __future__ import annotations`

Without the future import, Python evaluates annotations at runtime, causing
NameError for TYPE_CHECKING-only imports.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest


def _discover_package_modules(package_name: str) -> list[str]:
    """Discover all modules in a package recursively.

    Args:
        package_name: Name of the package to discover (e.g., "erk", "erk_shared")

    Returns:
        List of fully qualified module names
    """
    modules: list[str] = []

    try:
        package = importlib.import_module(package_name)
    except ImportError:
        return modules

    if not hasattr(package, "__path__"):
        # Not a package, just a module
        return [package_name]

    for _importer, modname, _ispkg in pkgutil.walk_packages(
        package.__path__, prefix=f"{package_name}."
    ):
        modules.append(modname)

    return modules


def _get_package_source_paths() -> list[Path]:
    """Get the source paths for erk and erk_shared packages."""
    # Find the project root by looking for pyproject.toml
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "pyproject.toml").exists():
            project_root = current
            break
        current = current.parent
    else:
        pytest.fail("Could not find project root (pyproject.toml)")

    paths = [
        project_root / "src" / "erk",
        project_root / "packages" / "erk-shared" / "src" / "erk_shared",
    ]

    return [p for p in paths if p.exists()]


def _discover_python_files() -> list[Path]:
    """Discover all Python files in erk and erk_shared packages."""
    files: list[Path] = []

    for package_path in _get_package_source_paths():
        for py_file in package_path.rglob("*.py"):
            files.append(py_file)

    return files


def _has_type_checking_block(tree: ast.AST) -> bool:
    """Check if AST has an `if TYPE_CHECKING:` block with imports."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue

        # Check for `if TYPE_CHECKING:` pattern
        test = node.test

        # Direct name: `if TYPE_CHECKING:`
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            # Check if body has any import statements
            for stmt in node.body:
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    return True

        # Attribute access: `if typing.TYPE_CHECKING:`
        if (
            isinstance(test, ast.Attribute)
            and test.attr == "TYPE_CHECKING"
            and isinstance(test.value, ast.Name)
            and test.value.id == "typing"
        ):
            for stmt in node.body:
                if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                    return True

    return False


def _has_future_annotations(tree: ast.AST) -> bool:
    """Check if AST has `from __future__ import annotations`."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.module == "__future__":
            for alias in node.names:
                if alias.name == "annotations":
                    return True

    return False


def test_all_modules_import_successfully() -> None:
    """Runtime test: Verify all modules can be imported without NameError.

    This catches forward reference errors that manifest at import time,
    which includes all class/function definition annotations.
    """
    packages = ["erk", "erk_shared"]
    import_errors: list[str] = []

    for package_name in packages:
        for module_name in _discover_package_modules(package_name):
            try:
                importlib.import_module(module_name)
            except NameError as e:
                import_errors.append(f"{module_name}: NameError - {e}")
            except ImportError:
                # ImportError is expected for some optional dependencies
                # We only care about NameError (forward reference issues)
                pass

    if import_errors:
        pytest.fail(
            "Forward reference errors detected during import:\n"
            + "\n".join(f"  - {err}" for err in import_errors)
        )


def test_files_with_type_checking_have_future_annotations() -> None:
    """Static analysis: Detect risky pattern before it causes runtime errors.

    Files with TYPE_CHECKING imports SHOULD have `from __future__ import annotations`
    to prevent forward reference errors. This test catches the pattern proactively.
    """
    violations: list[str] = []

    for filepath in _discover_python_files():
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(filepath))
        except SyntaxError:
            # Skip files with syntax errors (they'll fail elsewhere)
            continue

        if _has_type_checking_block(tree) and not _has_future_annotations(tree):
            # Make path relative for cleaner output
            try:
                relative = filepath.relative_to(Path.cwd())
            except ValueError:
                relative = filepath
            violations.append(str(relative))

    if violations:
        pytest.fail(
            "Files with TYPE_CHECKING imports missing 'from __future__ import annotations':\n"
            + "\n".join(f"  - {f}" for f in sorted(violations))
            + "\n\nAdd 'from __future__ import annotations' after the module docstring."
        )
