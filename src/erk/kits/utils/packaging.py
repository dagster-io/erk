"""Package utilities for detection and resolution."""

from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from pathlib import Path


def is_package_installed(package_name: str) -> bool:
    """Check if a Python package is installed."""
    spec = find_spec(package_name.replace("-", "_"))
    return spec is not None


def get_package_version(package_name: str) -> str | None:
    """Get the version of an installed package."""
    try:
        return version(package_name)
    except PackageNotFoundError:
        return None


def get_package_path(package_name: str) -> Path | None:
    """Get the filesystem path to an installed package."""
    spec = find_spec(package_name.replace("-", "_"))
    if spec is None or spec.origin is None:
        return None

    origin_path = Path(spec.origin)

    # Return the package directory (parent of __init__.py)
    if origin_path.name == "__init__.py":
        return origin_path.parent

    return origin_path


def find_kit_manifest(package_path: Path) -> Path | None:
    """Find kit.yaml in package directory."""
    # Check in package root
    manifest = package_path / "kit.yaml"
    if manifest.exists():
        return manifest

    # Check in parent (for packages/foo-kit/kit.yaml)
    parent_manifest = package_path.parent / "kit.yaml"
    if parent_manifest.exists():
        return parent_manifest

    return None
