"""Tests for artifacts state management."""

from pathlib import Path

from erk.artifacts.models import ArtifactState
from erk.artifacts.state import get_state_path, load_artifact_state, save_artifact_state


def test_get_state_path(tmp_project: Path) -> None:
    """Test that state path is correctly computed."""
    expected = tmp_project / ".erk" / "state.toml"
    assert get_state_path(tmp_project) == expected


def test_load_artifact_state_returns_none_if_not_exists(tmp_project: Path) -> None:
    """Test loading returns None when file doesn't exist."""
    state = load_artifact_state(tmp_project)
    assert state is None


def test_save_and_load_artifact_state(tmp_project: Path) -> None:
    """Test round-trip save and load of artifact state."""
    state = ArtifactState(version="1.2.3")

    save_artifact_state(tmp_project, state)
    loaded_state = load_artifact_state(tmp_project)

    assert loaded_state is not None
    assert loaded_state.version == "1.2.3"


def test_save_creates_erk_directory(tmp_project: Path) -> None:
    """Test that save creates .erk/ directory if needed."""
    erk_dir = tmp_project / ".erk"
    assert not erk_dir.exists()

    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    assert erk_dir.exists()
    assert (erk_dir / "state.toml").exists()


def test_save_overwrites_existing_state(tmp_project: Path) -> None:
    """Test that save overwrites existing state file."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))
    save_artifact_state(tmp_project, ArtifactState(version="2.0.0"))

    loaded_state = load_artifact_state(tmp_project)
    assert loaded_state is not None
    assert loaded_state.version == "2.0.0"


def test_state_file_format(tmp_project: Path) -> None:
    """Test that state file is written in correct TOML format."""
    save_artifact_state(tmp_project, ArtifactState(version="1.2.3"))

    state_path = get_state_path(tmp_project)
    content = state_path.read_text(encoding="utf-8")

    # Should contain [artifacts] section with version key
    assert "[artifacts]" in content
    assert 'version = "1.2.3"' in content
