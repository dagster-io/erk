"""File and module discovery utilities for forward reference checking."""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiscoveryResult:
    """Result of file or module discovery.

    Includes both the discovered items and metadata for verification.
    """

    items: tuple[str, ...]
    source_paths: tuple[Path, ...]


def discover_python_files(paths: list[Path]) -> DiscoveryResult:
    """Discover all Python files in the given paths.

    Args:
        paths: List of directory paths to search

    Returns:
        DiscoveryResult with discovered file paths as strings and the
        source paths that were searched.
    """
    files: list[str] = []
    valid_paths: list[Path] = []

    for path in paths:
        if not path.exists():
            continue
        if not path.is_dir():
            continue

        valid_paths.append(path)
        for py_file in path.rglob("*.py"):
            files.append(str(py_file))

    return DiscoveryResult(
        items=tuple(sorted(files)),
        source_paths=tuple(valid_paths),
    )


def discover_package_modules(package_name: str) -> DiscoveryResult:
    """Discover all modules in a package recursively.

    Args:
        package_name: Name of the package to discover (e.g., "erk", "erk_shared")

    Returns:
        DiscoveryResult with discovered module names and the package path.
    """
    modules: list[str] = []
    source_paths: list[Path] = []

    try:
        package = importlib.import_module(package_name)
    except ImportError:
        return DiscoveryResult(items=(), source_paths=())

    if not hasattr(package, "__path__"):
        # Not a package, just a module
        return DiscoveryResult(
            items=(package_name,),
            source_paths=(),
        )

    # Get the package path
    package_path = getattr(package, "__path__", None)
    if package_path:
        for p in package_path:
            path = Path(p)
            if path.exists():
                source_paths.append(path)

    for _importer, modname, _ispkg in pkgutil.walk_packages(
        package.__path__, prefix=f"{package_name}."
    ):
        modules.append(modname)

    return DiscoveryResult(
        items=tuple(sorted(modules)),
        source_paths=tuple(source_paths),
    )


def import_module_safely(module_name: str) -> tuple[bool, str | None]:
    """Attempt to import a module and report any NameError.

    This is used to detect forward reference errors that manifest at import time.

    Args:
        module_name: Fully qualified module name to import

    Returns:
        Tuple of (success, error_message). If success is True, error_message
        is None. If success is False, error_message contains the NameError
        message.
    """
    try:
        importlib.import_module(module_name)
        return (True, None)
    except NameError as e:
        return (False, f"{module_name}: NameError - {e}")
    except ImportError:
        # ImportError is expected for optional dependencies
        # We only care about NameError (forward reference issues)
        return (True, None)
    except Exception:
        # Other errors (circular imports, missing native deps, etc.) are not
        # forward reference issues. They'll surface elsewhere in the test suite
        # or when the module is actually used. We only care about NameError here.
        return (True, None)
