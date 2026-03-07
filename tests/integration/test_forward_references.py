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

## Due Diligence: Why Custom Tests?

We investigated ruff and ty for existing rules - they don't cover this case.
See `erk_dev.forward_refs` module docstring for full rationale.

## Testing the Tests

The detection logic is tested separately in `test_forward_reference_detection.py`
with known good/bad inputs. This file uses those utilities to scan the actual
erk codebase.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from erk_dev.forward_refs.detection import check_file
from erk_dev.forward_refs.discovery import (
    discover_package_modules,
    discover_python_files,
    import_module_safely,
)

# Minimum expected counts to guard against silent discovery failures
# These should be updated if the project structure changes significantly
MIN_EXPECTED_FILES = 50  # We have way more than 50 Python files
MIN_EXPECTED_MODULES = 20  # We have way more than 20 modules


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


def test_file_discovery_finds_expected_minimum() -> None:
    """Verify file discovery actually finds files (guards against silent failures)."""
    paths = _get_package_source_paths()
    result = discover_python_files(paths)

    assert len(result.items) >= MIN_EXPECTED_FILES, (
        f"Expected at least {MIN_EXPECTED_FILES} Python files, "
        f"found {len(result.items)}. "
        "This may indicate a discovery bug or project restructure."
    )


def test_module_discovery_finds_expected_minimum() -> None:
    """Verify module discovery actually finds modules (guards against silent failures)."""
    erk_result = discover_package_modules("erk")
    erk_shared_result = discover_package_modules("erk_shared")

    total_modules = len(erk_result.items) + len(erk_shared_result.items)

    assert total_modules >= MIN_EXPECTED_MODULES, (
        f"Expected at least {MIN_EXPECTED_MODULES} modules, "
        f"found {total_modules}. "
        "This may indicate a discovery bug or project restructure."
    )


def test_all_modules_import_successfully() -> None:
    """Runtime test: Verify all modules can be imported without NameError.

    This catches forward reference errors that manifest at import time,
    which includes all class/function definition annotations.
    """
    packages = ["erk", "erk_shared"]
    import_errors: list[str] = []
    modules_checked = 0

    for package_name in packages:
        result = discover_package_modules(package_name)
        for module_name in result.items:
            modules_checked += 1
            success, error_message = import_module_safely(module_name)
            if not success and error_message is not None:
                import_errors.append(error_message)

    # Guard: Ensure we actually checked some modules
    assert modules_checked >= MIN_EXPECTED_MODULES, (
        f"Expected to check at least {MIN_EXPECTED_MODULES} modules, "
        f"only checked {modules_checked}. Discovery may be broken."
    )

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
    files_checked = 0

    for filepath_str in discover_python_files(_get_package_source_paths()).items:
        files_checked += 1
        filepath = Path(filepath_str)
        violation = check_file(filepath)

        if violation is not None:
            # Make path relative for cleaner output (LBYL pattern)
            cwd = Path.cwd()
            if filepath.is_relative_to(cwd):
                relative = filepath.relative_to(cwd)
            else:
                relative = filepath
            violations.append(str(relative))

    # Guard: Ensure we actually checked some files
    assert files_checked >= MIN_EXPECTED_FILES, (
        f"Expected to check at least {MIN_EXPECTED_FILES} files, "
        f"only checked {files_checked}. Discovery may be broken."
    )

    if violations:
        pytest.fail(
            "Files with TYPE_CHECKING imports missing 'from __future__ import annotations':\n"
            + "\n".join(f"  - {f}" for f in sorted(violations))
            + "\n\nAdd 'from __future__ import annotations' after the module docstring."
        )
