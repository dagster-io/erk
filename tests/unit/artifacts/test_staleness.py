"""Tests for artifacts staleness detection."""

from pathlib import Path
from unittest.mock import patch

from erk.artifacts.models import ArtifactState
from erk.artifacts.staleness import check_staleness, is_dev_mode
from erk.artifacts.state import save_artifact_state


def test_is_dev_mode_returns_true_for_erk_repo(tmp_project: Path) -> None:
    """Test that is_dev_mode returns True when packages/erk-kits exists."""
    # Create the dev mode indicator directory
    dev_indicator = tmp_project / "packages" / "erk-kits"
    dev_indicator.mkdir(parents=True)

    assert is_dev_mode(tmp_project) is True


def test_is_dev_mode_returns_false_for_regular_project(tmp_project: Path) -> None:
    """Test that is_dev_mode returns False for a regular project."""
    assert is_dev_mode(tmp_project) is False


def test_check_staleness_not_initialized(tmp_project: Path) -> None:
    """Test staleness check when project is not initialized."""
    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_project)

    assert result.is_stale is True
    assert result.reason == "not initialized"
    assert result.current_version == "1.0.0"
    assert result.installed_version is None


def test_check_staleness_version_mismatch(tmp_project: Path) -> None:
    """Test staleness check when installed version differs from current."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    with patch("erk.artifacts.staleness.get_current_version", return_value="2.0.0"):
        result = check_staleness(tmp_project)

    assert result.is_stale is True
    assert result.reason == "version mismatch"
    assert result.current_version == "2.0.0"
    assert result.installed_version == "1.0.0"


def test_check_staleness_up_to_date(tmp_project: Path) -> None:
    """Test staleness check when versions match."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        result = check_staleness(tmp_project)

    assert result.is_stale is False
    assert result.reason == "up to date"
    assert result.current_version == "1.0.0"
    assert result.installed_version == "1.0.0"


def test_staleness_result_is_frozen() -> None:
    """Test that StalenessResult is immutable."""
    from erk.artifacts.models import StalenessResult

    result = StalenessResult(
        is_stale=True,
        reason="test",
        current_version="1.0.0",
        installed_version=None,
    )

    # Frozen dataclass should raise FrozenInstanceError on attribute assignment
    import pytest

    with pytest.raises(AttributeError):
        result.is_stale = False  # type: ignore[misc]
