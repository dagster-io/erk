"""Tests for artifact staleness checking."""

from pathlib import Path
from unittest.mock import patch

from erk.artifacts.staleness import check_staleness


def test_check_staleness_not_initialized(tmp_path: Path) -> None:
    """Returns not-initialized when no state file exists."""
    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_path)

    assert result.is_stale is True
    assert result.reason == "not-initialized"
    assert result.current_version == "1.0.0"
    assert result.installed_version is None


def test_check_staleness_version_mismatch(tmp_path: Path) -> None:
    """Returns version-mismatch when versions differ."""
    # Create state file with old version (requires files section)
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[artifacts]\nversion = "0.9.0"\n\n[artifacts.files]\n', encoding="utf-8")

    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_path)

    assert result.is_stale is True
    assert result.reason == "version-mismatch"
    assert result.current_version == "1.0.0"
    assert result.installed_version == "0.9.0"


def test_check_staleness_up_to_date(tmp_path: Path) -> None:
    """Returns up-to-date when versions match."""
    # Create state file with matching version (requires files section)
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[artifacts]\nversion = "1.0.0"\n\n[artifacts.files]\n', encoding="utf-8")

    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_path)

    assert result.is_stale is False
    assert result.reason == "up-to-date"
    assert result.current_version == "1.0.0"
    assert result.installed_version == "1.0.0"


def test_check_staleness_erk_repo(tmp_path: Path) -> None:
    """Returns erk-repo reason when in erk repository without state.toml."""
    # Create pyproject.toml with erk name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_path)

    assert result.is_stale is False
    assert result.reason == "erk-repo"
    assert result.current_version == "1.0.0"
    assert result.installed_version is None


def test_check_staleness_erk_repo_with_state(tmp_path: Path) -> None:
    """Loads state.toml in erk repo for dogfooding."""
    # Create pyproject.toml with erk name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    # Create state.toml (as would be created by erk artifact sync)
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[artifacts]\nversion = "0.5.0"\n\n[artifacts.files]\n', encoding="utf-8")

    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_path)

    assert result.is_stale is False
    assert result.reason == "erk-repo"
    assert result.current_version == "1.0.0"
    # Verifies state.toml was loaded - installed_version reflects saved state
    assert result.installed_version == "0.5.0"
