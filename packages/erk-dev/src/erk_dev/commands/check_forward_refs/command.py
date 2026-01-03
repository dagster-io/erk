"""Check for forward reference violations in Python files."""

from __future__ import annotations

from pathlib import Path

import click

from erk_dev.cli.output import user_output
from erk_dev.forward_refs.detection import check_file
from erk_dev.forward_refs.discovery import discover_python_files


def find_project_root() -> Path | None:
    """Find project root by looking for pyproject.toml."""
    current = Path.cwd().resolve()
    while current.parent != current:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    return None


def get_default_source_paths(project_root: Path) -> list[Path]:
    """Get default source paths for erk project."""
    paths = [
        project_root / "src" / "erk",
        project_root / "packages" / "erk-shared" / "src" / "erk_shared",
        project_root / "packages" / "erk-dev" / "src" / "erk_dev",
    ]
    return [p for p in paths if p.exists()]


@click.command(name="check-forward-refs")
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option("--verbose", "-v", is_flag=True, help="Show all files checked")
def check_forward_refs_command(paths: tuple[Path, ...], verbose: bool) -> None:
    """Check Python files for forward reference violations.

    Detects files that have TYPE_CHECKING imports but lack the required
    `from __future__ import annotations` import.

    If no PATHS are provided, checks the erk and erk_shared packages.
    """
    # Determine paths to check
    if paths:
        path_list = list(paths)
    else:
        project_root = find_project_root()
        if project_root is None:
            user_output("Error: Could not find project root (pyproject.toml)")
            raise SystemExit(1)
        path_list = get_default_source_paths(project_root)

    if not path_list:
        user_output("No paths to check")
        raise SystemExit(0)

    # Discover files
    result = discover_python_files(path_list)

    if not result.items:
        user_output("No Python files found")
        raise SystemExit(0)

    user_output(f"Checking {len(result.items)} Python files...")

    # Check each file
    violations: list[str] = []
    for filepath_str in result.items:
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
        elif verbose:
            user_output(f"  OK: {filepath}")

    # Report results
    if violations:
        user_output("")
        user_output(
            "Files with TYPE_CHECKING imports missing 'from __future__ import annotations':"
        )
        for v in sorted(violations):
            user_output(f"  - {v}")
        user_output("")
        user_output("Fix: Add 'from __future__ import annotations' after the module docstring.")
        raise SystemExit(1)
    else:
        user_output(f"All {len(result.items)} files OK")
