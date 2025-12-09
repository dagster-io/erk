"""Tests for erk version check module.

These are Layer 4 tests (business logic) that verify version tracking
and kit synchronization behavior.
"""

from pathlib import Path

from erk.core.kit_installer import install_erk_kits
from erk.core.version_check import check_and_sync_kits
from erk.version import __version__ as ERK_VERSION


def test_check_and_sync_kits_creates_version_file(tmp_path: Path) -> None:
    """Test that check_and_sync_kits creates version file on first run."""
    # Create .erks directory
    erks_dir = tmp_path / ".erks"
    erks_dir.mkdir()

    # Run check (no kits installed yet, should just create version file)
    check_and_sync_kits(tmp_path)

    # Verify version file was created
    version_file = erks_dir / "last-erk-version"
    assert version_file.exists()
    assert version_file.read_text().strip() == ERK_VERSION


def test_check_and_sync_kits_skips_when_version_matches(tmp_path: Path) -> None:
    """Test that check_and_sync_kits skips sync when version matches."""
    # Create .erks directory and version file with current version
    erks_dir = tmp_path / ".erks"
    erks_dir.mkdir()
    version_file = erks_dir / "last-erk-version"
    version_file.write_text(ERK_VERSION)

    # Install kits so there's something to sync
    install_erk_kits(tmp_path, use_graphite=False)

    # Get initial timestamp
    initial_mtime = version_file.stat().st_mtime

    # Run check - should skip sync since version matches
    check_and_sync_kits(tmp_path)

    # Version file should be unchanged
    assert version_file.read_text().strip() == ERK_VERSION
    # File modification time should be very close (allowing small drift)
    assert abs(version_file.stat().st_mtime - initial_mtime) < 1.0


def test_check_and_sync_kits_syncs_on_version_change(tmp_path: Path) -> None:
    """Test that check_and_sync_kits syncs kits when version changes."""
    # Create .erks directory and version file with old version
    erks_dir = tmp_path / ".erks"
    erks_dir.mkdir()
    version_file = erks_dir / "last-erk-version"
    old_version = "0.0.1"
    version_file.write_text(old_version)

    # Install kits
    install_erk_kits(tmp_path, use_graphite=False)

    # Run check - should detect version change and sync
    check_and_sync_kits(tmp_path)

    # Version file should be updated to current version
    assert version_file.read_text().strip() == ERK_VERSION
    assert version_file.read_text().strip() != old_version


def test_check_and_sync_kits_no_erks_dir_returns_early(tmp_path: Path) -> None:
    """Test that check_and_sync_kits returns early if .erks doesn't exist."""
    # No .erks directory, should return without error
    check_and_sync_kits(tmp_path)

    # Should not create .erks or version file
    erks_dir = tmp_path / ".erks"
    assert not erks_dir.exists()


def test_check_and_sync_kits_first_time_no_sync(tmp_path: Path) -> None:
    """Test that check_and_sync_kits doesn't sync on first run (no previous version)."""
    # Create .erks directory but no version file
    erks_dir = tmp_path / ".erks"
    erks_dir.mkdir()

    # Run check - should create version file but not sync
    check_and_sync_kits(tmp_path)

    # Version file should be created
    version_file = erks_dir / "last-erk-version"
    assert version_file.exists()
    assert version_file.read_text().strip() == ERK_VERSION
