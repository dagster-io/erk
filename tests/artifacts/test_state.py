"""Tests for artifact state management."""

from pathlib import Path

from erk.artifacts.models import ArtifactFileState, ArtifactState
from erk.artifacts.state import (
    add_installed_capability,
    load_artifact_state,
    load_installed_capabilities,
    remove_installed_capability,
    save_artifact_state,
)


def test_load_artifact_state_returns_none_when_file_missing(tmp_path: Path) -> None:
    """Returns None when state file doesn't exist."""
    result = load_artifact_state(tmp_path)
    assert result is None


def test_load_artifact_state_returns_none_when_no_artifacts_section(tmp_path: Path) -> None:
    """Returns None when state file has no artifacts section."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[other]\nkey = "value"\n', encoding="utf-8")

    result = load_artifact_state(tmp_path)
    assert result is None


def test_load_artifact_state_returns_none_when_no_files_section(tmp_path: Path) -> None:
    """Returns None when state file has artifacts but no files section."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[artifacts]\nversion = "1.2.3"\n', encoding="utf-8")

    result = load_artifact_state(tmp_path)
    assert result is None


def test_load_artifact_state_reads_version_and_files(tmp_path: Path) -> None:
    """Reads version and files from state file."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        """[artifacts]
version = "1.2.3"

[artifacts.files."skills/dignified-python"]
version = "1.2.0"
hash = "abc123def456"
""",
        encoding="utf-8",
    )

    result = load_artifact_state(tmp_path)

    assert result is not None
    assert result.version == "1.2.3"
    assert "skills/dignified-python" in result.files
    assert result.files["skills/dignified-python"].version == "1.2.0"
    assert result.files["skills/dignified-python"].hash == "abc123def456"


def test_load_artifact_state_handles_empty_files_section(tmp_path: Path) -> None:
    """Handles state file with empty files section."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        """[artifacts]
version = "1.0.0"

[artifacts.files]
""",
        encoding="utf-8",
    )

    result = load_artifact_state(tmp_path)

    assert result is not None
    assert result.version == "1.0.0"
    assert len(result.files) == 0


def test_save_artifact_state_creates_file(tmp_path: Path) -> None:
    """Creates state file with version and files."""
    state = ArtifactState(
        version="1.0.0",
        files={
            "skills/test-skill": ArtifactFileState(version="1.0.0", hash="abc123"),
        },
    )

    save_artifact_state(tmp_path, state)

    state_file = tmp_path / ".erk" / "state.toml"
    assert state_file.exists()
    content = state_file.read_text(encoding="utf-8")
    assert 'version = "1.0.0"' in content
    assert "[artifacts.files" in content


def test_save_artifact_state_preserves_other_sections(tmp_path: Path) -> None:
    """Preserves other sections when updating artifacts."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[other]\nkey = "value"\n', encoding="utf-8")

    state = ArtifactState(version="2.0.0", files={})
    save_artifact_state(tmp_path, state)

    content = state_file.read_text(encoding="utf-8")
    assert 'key = "value"' in content
    assert 'version = "2.0.0"' in content


def test_roundtrip_state(tmp_path: Path) -> None:
    """State can be saved and loaded."""
    original = ArtifactState(
        version="3.5.7",
        files={
            "skills/dignified-python": ArtifactFileState(version="3.5.0", hash="abc123"),
            "agents/devrun": ArtifactFileState(version="3.5.7", hash="def456"),
        },
    )

    save_artifact_state(tmp_path, original)
    loaded = load_artifact_state(tmp_path)

    assert loaded is not None
    assert loaded.version == original.version
    assert len(loaded.files) == 2
    assert loaded.files["skills/dignified-python"].version == "3.5.0"
    assert loaded.files["skills/dignified-python"].hash == "abc123"
    assert loaded.files["agents/devrun"].version == "3.5.7"
    assert loaded.files["agents/devrun"].hash == "def456"


# Tests for installed capabilities tracking


def test_load_installed_capabilities_returns_empty_when_file_missing(tmp_path: Path) -> None:
    """Returns empty frozenset when state file doesn't exist."""
    result = load_installed_capabilities(tmp_path)
    assert result == frozenset()


def test_load_installed_capabilities_returns_empty_when_no_capabilities_section(
    tmp_path: Path,
) -> None:
    """Returns empty frozenset when state file has no capabilities section."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[other]\nkey = "value"\n', encoding="utf-8")

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset()


def test_load_installed_capabilities_reads_installed_list(tmp_path: Path) -> None:
    """Reads installed capabilities from state file."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        """[capabilities]
installed = ["dignified-python", "fake-driven-testing"]
""",
        encoding="utf-8",
    )

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset({"dignified-python", "fake-driven-testing"})


def test_add_installed_capability_creates_file(tmp_path: Path) -> None:
    """Creates state file with capability."""
    add_installed_capability(tmp_path, "dignified-python")

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset({"dignified-python"})


def test_add_installed_capability_appends_to_existing(tmp_path: Path) -> None:
    """Appends capability to existing list."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        """[capabilities]
installed = ["fake-driven-testing"]
""",
        encoding="utf-8",
    )

    add_installed_capability(tmp_path, "dignified-python")

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset({"dignified-python", "fake-driven-testing"})


def test_add_installed_capability_is_idempotent(tmp_path: Path) -> None:
    """Adding same capability twice doesn't duplicate."""
    add_installed_capability(tmp_path, "dignified-python")
    add_installed_capability(tmp_path, "dignified-python")

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset({"dignified-python"})


def test_add_installed_capability_preserves_other_sections(tmp_path: Path) -> None:
    """Preserves other sections when updating capabilities."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text('[other]\nkey = "value"\n', encoding="utf-8")

    add_installed_capability(tmp_path, "dignified-python")

    content = state_file.read_text(encoding="utf-8")
    assert 'key = "value"' in content
    assert "dignified-python" in content


def test_remove_installed_capability_removes_from_list(tmp_path: Path) -> None:
    """Removes capability from installed list."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        """[capabilities]
installed = ["dignified-python", "fake-driven-testing"]
""",
        encoding="utf-8",
    )

    remove_installed_capability(tmp_path, "dignified-python")

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset({"fake-driven-testing"})


def test_remove_installed_capability_noop_when_not_installed(tmp_path: Path) -> None:
    """No-op when capability isn't installed."""
    state_file = tmp_path / ".erk" / "state.toml"
    state_file.parent.mkdir(parents=True)
    state_file.write_text(
        """[capabilities]
installed = ["dignified-python"]
""",
        encoding="utf-8",
    )

    remove_installed_capability(tmp_path, "nonexistent")

    result = load_installed_capabilities(tmp_path)
    assert result == frozenset({"dignified-python"})


def test_remove_installed_capability_noop_when_file_missing(tmp_path: Path) -> None:
    """No-op when state file doesn't exist."""
    remove_installed_capability(tmp_path, "dignified-python")
    # No error, no file created
    assert not (tmp_path / ".erk" / "state.toml").exists()
