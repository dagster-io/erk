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


def write_required_version(repo_root: Path, version: str) -> None:
    """Write required version to .erk/required-erk-uv-tool-version.

    Args:
        repo_root: Path to the git repository root
        version: Version string to write
    """
    version_file = repo_root / ".erk" / "required-erk-uv-tool-version"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text(version + "\n", encoding="utf-8")


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
    """Format warning message for version mismatch with direction-specific advice.

    When installed < required: suggests upgrading erk
    When installed > required: suggests running `erk project upgrade`

    Args:
        installed: Currently installed version
        required: Required version from repo

    Returns:
        Formatted warning message with appropriate action
    """
    installed_v = Version(installed)
    required_v = Version(required)

    if installed_v < required_v:
        # User needs to upgrade their local erk
        action = "   Run: uv tool upgrade erk"
    else:
        # User has newer erk - project needs upgrading
        action = "   Run: erk project upgrade"

    return (
        f"⚠️  Globally installed erk ({installed}) does not match the version "
        f"this repository is pinned to ({required}).\n"
        f"{action}"
    )
