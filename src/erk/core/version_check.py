"""Version tracking and kit synchronization for erk upgrades.

This module tracks the erk version and automatically syncs Claude Code
kits when the version changes. This ensures artifacts stay in sync with
the erk installation.
"""

from pathlib import Path

from erk.core.kit_installer import sync_erk_kits
from erk.version import __version__ as ERK_VERSION


def check_and_sync_kits(repo_root: Path) -> None:
    """Check if erk version changed and sync kits if needed.

    This function:
    1. Reads the last erk version from .erks/last-erk-version
    2. Compares with current erk version
    3. If different, syncs all installed kits to latest versions
    4. Updates the version file

    This ensures that when users upgrade erk, their Claude Code artifacts
    automatically update to match the new bundled kit versions.

    Args:
        repo_root: Root directory of the repository

    Note:
        This function is safe to call on every init. It only performs
        expensive operations (kit sync) when the version has changed.
    """
    # Check if .erks directory exists
    erks_dir = repo_root / ".erks"
    if not erks_dir.exists():
        # Repository not yet initialized with erk
        return

    version_file = erks_dir / "last-erk-version"

    # Read last version if file exists
    last_version = None
    if version_file.exists():
        last_version = version_file.read_text().strip()

    # Version matches, no sync needed
    if last_version == ERK_VERSION:
        return

    # Version changed or first time - sync kits
    if last_version is not None:
        # This is an upgrade, sync kits
        sync_erk_kits(repo_root)

    # Write current version
    version_file.write_text(ERK_VERSION)
