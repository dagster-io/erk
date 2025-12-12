"""Tests for legacy config locations health check (dogfooder feature)."""

from pathlib import Path

from erk.core.health_checks_dogfooder import check_legacy_config_locations


def test_check_legacy_config_passes_when_primary_location_exists(
    tmp_path: Path,
) -> None:
    """Test check passes when .erk/config.toml exists (primary location)."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text("[config]\n", encoding="utf-8")

    result = check_legacy_config_locations(tmp_path, metadata_dir=None)

    assert result.passed is True
    assert result.name == "legacy config"
    assert "primary location" in result.message


def test_check_legacy_config_passes_when_no_legacy_configs(
    tmp_path: Path,
) -> None:
    """Test check passes when no config files exist anywhere."""
    result = check_legacy_config_locations(tmp_path, metadata_dir=None)

    assert result.passed is True
    assert result.name == "legacy config"
    assert "No legacy" in result.message


def test_check_legacy_config_warns_on_repo_root_config(
    tmp_path: Path,
) -> None:
    """Test check warns when config.toml exists at repo root (legacy location)."""
    config_path = tmp_path / "config.toml"
    config_path.write_text("[config]\n", encoding="utf-8")

    result = check_legacy_config_locations(tmp_path, metadata_dir=None)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy config"
    assert "1 legacy config" in result.message
    assert result.details is not None
    assert "repo root" in result.details
    assert ".erk/config.toml" in result.details


def test_check_legacy_config_warns_on_metadata_dir_config(
    tmp_path: Path,
) -> None:
    """Test check warns when config.toml exists in metadata dir (legacy location)."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    config_path = metadata_dir / "config.toml"
    config_path.write_text("[config]\n", encoding="utf-8")

    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    result = check_legacy_config_locations(repo_root, metadata_dir=metadata_dir)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy config"
    assert "1 legacy config" in result.message
    assert result.details is not None
    assert "metadata dir" in result.details


def test_check_legacy_config_warns_on_multiple_legacy_locations(
    tmp_path: Path,
) -> None:
    """Test check warns when config.toml exists at multiple legacy locations."""
    # Create repo root config
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "config.toml").write_text("[config]\n", encoding="utf-8")

    # Create metadata dir config
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    (metadata_dir / "config.toml").write_text("[config]\n", encoding="utf-8")

    result = check_legacy_config_locations(repo_root, metadata_dir=metadata_dir)

    assert result.passed is True  # Warning only, doesn't fail
    assert result.warning is True
    assert result.name == "legacy config"
    assert "2 legacy config" in result.message
    assert result.details is not None
    assert "repo root" in result.details
    assert "metadata dir" in result.details


def test_check_legacy_config_skips_legacy_when_primary_exists(
    tmp_path: Path,
) -> None:
    """Test check skips legacy detection when primary location exists."""
    # Create primary location
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("[config]\n", encoding="utf-8")

    # Also create legacy location (should be ignored)
    (tmp_path / "config.toml").write_text("[config]\n", encoding="utf-8")

    result = check_legacy_config_locations(tmp_path, metadata_dir=None)

    # Should pass without warning because primary exists
    assert result.passed is True
    assert result.warning is not True
    assert "primary location" in result.message
