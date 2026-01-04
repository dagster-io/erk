"""Tests for legacy config detection (early dogfooder migration support).

These tests cover functionality that exists ONLY for early dogfooders who may
have config files at legacy locations. Once all early dogfooders have migrated,
this entire folder can be deleted along with the associated code.

The legacy detection is used by 'erk doctor' to warn users about config files
that should be moved to .erk/config.toml.
"""

from pathlib import Path

from erk.core.health_checks_dogfooder.legacy_config_locations import (
    LegacyConfigLocation,
    detect_legacy_config_locations,
)


class TestDetectLegacyConfigLocations:
    """Tests for detect_legacy_config_locations function."""

    def test_no_legacy_configs(self, tmp_path: Path) -> None:
        """Returns empty list when no legacy configs exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()

        result = detect_legacy_config_locations(repo_root, metadata_dir)

        assert result == []

    def test_detects_repo_root_config(self, tmp_path: Path) -> None:
        """Detects config.toml at repo root."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text("[env]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, None)

        assert len(result) == 1
        assert result[0].path == repo_root / "config.toml"
        assert "repo root" in result[0].description

    def test_detects_dot_agent_toml(self, tmp_path: Path) -> None:
        """Detects dot-agent.toml at repo root as legacy config."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "dot-agent.toml").write_text("[kits]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, None)

        assert len(result) == 1
        assert result[0].path == repo_root / "dot-agent.toml"
        assert "legacy config" in result[0].description

    def test_detects_metadata_dir_config(self, tmp_path: Path) -> None:
        """Detects config.toml in metadata directory."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text("[env]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, metadata_dir)

        assert len(result) == 1
        assert result[0].path == metadata_dir / "config.toml"
        assert "metadata dir" in result[0].description

    def test_detects_all_legacy_locations(self, tmp_path: Path) -> None:
        """Detects all legacy locations: config.toml, dot-agent.toml, and metadata dir."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text("[env]", encoding="utf-8")
        (repo_root / "dot-agent.toml").write_text("[kits]", encoding="utf-8")
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text("[env]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, metadata_dir)

        assert len(result) == 3
        # Repo root config.toml is first, then dot-agent.toml, then metadata dir
        assert result[0].path == repo_root / "config.toml"
        assert result[1].path == repo_root / "dot-agent.toml"
        assert result[2].path == metadata_dir / "config.toml"

    def test_handles_none_metadata_dir(self, tmp_path: Path) -> None:
        """Handles None metadata_dir gracefully."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        result = detect_legacy_config_locations(repo_root, None)

        assert result == []


class TestLegacyConfigLocation:
    """Tests for LegacyConfigLocation dataclass."""

    def test_frozen(self) -> None:
        """LegacyConfigLocation is immutable."""
        import pytest

        loc = LegacyConfigLocation(
            path=Path("/some/path"),
            description="test",
        )

        with pytest.raises(AttributeError):
            loc.path = Path("/other")  # type: ignore[misc] -- intentionally mutating frozen dataclass to test immutability
