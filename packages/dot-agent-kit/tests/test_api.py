"""Tests for dot-agent-kit public API.

These are Layer 4 tests (business logic over fakes) that verify the
public API functionality using real filesystem operations but in isolated
temporary directories.
"""

from pathlib import Path

import pytest

from dot_agent_kit.api import (
    KitInstallResult,
    get_bundled_kit_version,
    install_bundled_kits,
    sync_installed_kits,
)
from dot_agent_kit.sources.exceptions import KitNotFoundError


def test_install_bundled_kits_creates_artifacts(tmp_path: Path) -> None:
    """Test that install_bundled_kits creates artifacts in .claude/ directory."""
    # Install a single bundled kit
    results = install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun"],
        overwrite=False,
    )

    # Verify results
    assert len(results) == 1
    result = results[0]
    assert result.kit_id == "devrun"
    assert result.was_updated is True
    assert result.artifacts_installed > 0

    # Verify artifacts were created
    claude_dir = tmp_path / ".claude"
    assert claude_dir.exists()

    # Verify dot-agent.toml was created
    config_path = tmp_path / "dot-agent.toml"
    assert config_path.exists()


def test_install_bundled_kits_multiple_kits(tmp_path: Path) -> None:
    """Test installing multiple kits at once."""
    results = install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun", "dignified-python"],
        overwrite=False,
    )

    assert len(results) == 2
    assert {r.kit_id for r in results} == {"devrun", "dignified-python"}
    assert all(r.was_updated for r in results)


def test_install_bundled_kits_skips_existing(tmp_path: Path) -> None:
    """Test that installing same kit twice skips second installation."""
    # First installation
    results1 = install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun"],
        overwrite=False,
    )
    assert results1[0].was_updated is True

    # Second installation should skip
    results2 = install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun"],
        overwrite=False,
    )
    assert results2[0].was_updated is False
    assert results2[0].kit_id == "devrun"


def test_install_bundled_kits_overwrites_with_flag(tmp_path: Path) -> None:
    """Test that overwrite=True reinstalls existing kits."""
    # First installation
    install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun"],
        overwrite=False,
    )

    # Second installation with overwrite
    results = install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun"],
        overwrite=True,
    )
    assert results[0].was_updated is True


def test_install_bundled_kits_nonexistent_directory(tmp_path: Path) -> None:
    """Test that installing to nonexistent directory raises FileNotFoundError."""
    nonexistent = tmp_path / "does-not-exist"

    with pytest.raises(FileNotFoundError):
        install_bundled_kits(
            project_dir=nonexistent,
            kit_ids=["devrun"],
            overwrite=False,
        )


def test_install_bundled_kits_invalid_kit_id(tmp_path: Path) -> None:
    """Test that invalid kit ID raises KitNotFoundError."""
    with pytest.raises(KitNotFoundError):
        install_bundled_kits(
            project_dir=tmp_path,
            kit_ids=["nonexistent-kit-12345"],
            overwrite=False,
        )


def test_sync_installed_kits_updates_versions(tmp_path: Path) -> None:
    """Test that sync_installed_kits updates kit versions."""
    # Install initial kit
    install_bundled_kits(
        project_dir=tmp_path,
        kit_ids=["devrun"],
        overwrite=False,
    )

    # Sync should check for updates (force=True always updates)
    results = sync_installed_kits(
        project_dir=tmp_path,
        force=True,
    )

    assert len(results) == 1
    assert results[0].kit_id == "devrun"
    assert results[0].was_updated is True


def test_sync_installed_kits_no_config(tmp_path: Path) -> None:
    """Test that sync without dot-agent.toml raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        sync_installed_kits(
            project_dir=tmp_path,
            force=False,
        )


def test_sync_installed_kits_nonexistent_directory(tmp_path: Path) -> None:
    """Test that syncing to nonexistent directory raises FileNotFoundError."""
    nonexistent = tmp_path / "does-not-exist"

    with pytest.raises(FileNotFoundError):
        sync_installed_kits(
            project_dir=nonexistent,
            force=False,
        )


def test_get_bundled_kit_version_returns_version() -> None:
    """Test that get_bundled_kit_version returns version string."""
    version = get_bundled_kit_version("devrun")

    assert isinstance(version, str)
    assert len(version) > 0
    # Version should be in semver-like format
    assert "." in version


def test_get_bundled_kit_version_invalid_kit() -> None:
    """Test that get_bundled_kit_version raises KitNotFoundError for invalid kit."""
    with pytest.raises(KitNotFoundError):
        get_bundled_kit_version("nonexistent-kit-12345")


def test_install_result_immutable() -> None:
    """Test that KitInstallResult is immutable (frozen dataclass)."""
    result = KitInstallResult(
        kit_id="test",
        version="1.0.0",
        artifacts_installed=5,
        was_updated=True,
    )

    # Attempting to modify should raise AttributeError
    with pytest.raises(AttributeError):
        result.kit_id = "modified"  # type: ignore[misc]
