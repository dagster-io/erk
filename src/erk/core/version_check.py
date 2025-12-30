"""Version checking for erk tool installation.

Compares the installed version against a repository-specified required version.
Used to warn users when their installed erk is outdated compared to what the
repository requires.
"""

from pathlib import Path

from packaging.version import Version


def get_required_version(repo_root: Path) -> str | None:
    """Read required version from .erk/required-erk-uv-tool-version.

    Args:
        repo_root: Path to the git repository root

    Returns:
        Version string if file exists, None otherwise
    """
    version_file = repo_root / ".erk" / "required-erk-uv-tool-version"
    if not version_file.exists():
        return None
    return version_file.read_text(encoding="utf-8").strip()


def is_version_mismatch(installed: str, required: str) -> bool:
    """Check if installed version doesn't match required version exactly.

    Args:
        installed: Currently installed version (e.g., "0.2.7")
        required: Required version from repo (e.g., "0.2.8")

    Returns:
        True if versions don't match exactly, False if they match
    """
    return Version(installed) != Version(required)


def format_version_warning(installed: str, required: str) -> str:
    """Format warning message for version mismatch.

    Args:
        installed: Currently installed version
        required: Required version from repo

    Returns:
        Formatted warning message
    """
    return (
        f"⚠️  Your erk ({installed}) doesn't match required ({required})\n"
        f"   You must update or erk may not work properly.\n"
        f"   Update: uv tool upgrade erk"
    )
