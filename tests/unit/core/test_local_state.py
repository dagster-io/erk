"""Tests for local_state.py local init state management.

Uses tmp_path fixture for real filesystem I/O since the functions
read and write actual files.
"""

from pathlib import Path

from erk.core.local_state import (
    LOCAL_STATE_FILENAME,
    LocalInitState,
    create_local_init_state,
    get_local_state_path,
    load_local_state,
    save_local_state,
)


def test_get_local_state_path_returns_correct_path(tmp_path: Path) -> None:
    """Test that get_local_state_path returns the correct path."""
    result = get_local_state_path(tmp_path)

    assert result == tmp_path / ".erk" / LOCAL_STATE_FILENAME


def test_load_local_state_returns_none_when_file_missing(tmp_path: Path) -> None:
    """Test that load_local_state returns None when file doesn't exist."""
    result = load_local_state(tmp_path)

    assert result is None


def test_load_local_state_returns_none_when_erk_dir_missing(tmp_path: Path) -> None:
    """Test that load_local_state returns None when .erk directory doesn't exist."""
    # Don't create .erk directory
    result = load_local_state(tmp_path)

    assert result is None


def test_save_and_load_local_state_roundtrip(tmp_path: Path) -> None:
    """Test that save_local_state and load_local_state work together."""
    state = LocalInitState(
        initialized_version="0.3.0",
        timestamp="2025-12-31T16:00:00",
    )

    save_local_state(tmp_path, state)
    loaded = load_local_state(tmp_path)

    assert loaded is not None
    assert loaded.initialized_version == "0.3.0"
    assert loaded.timestamp == "2025-12-31T16:00:00"


def test_save_local_state_creates_erk_directory(tmp_path: Path) -> None:
    """Test that save_local_state creates .erk directory if needed."""
    state = LocalInitState(
        initialized_version="0.3.0",
        timestamp="2025-12-31T16:00:00",
    )

    # .erk directory doesn't exist yet
    assert not (tmp_path / ".erk").exists()

    save_local_state(tmp_path, state)

    # .erk directory should now exist
    assert (tmp_path / ".erk").is_dir()
    assert (tmp_path / ".erk" / LOCAL_STATE_FILENAME).is_file()


def test_load_local_state_returns_none_for_empty_file(tmp_path: Path) -> None:
    """Test that load_local_state returns None for empty file."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    state_file = erk_dir / LOCAL_STATE_FILENAME
    state_file.write_text("", encoding="utf-8")

    result = load_local_state(tmp_path)

    assert result is None


def test_load_local_state_returns_none_for_missing_local_init_section(
    tmp_path: Path,
) -> None:
    """Test that load_local_state returns None when local_init section missing."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    state_file = erk_dir / LOCAL_STATE_FILENAME
    state_file.write_text("[other_section]\nkey = 'value'\n", encoding="utf-8")

    result = load_local_state(tmp_path)

    assert result is None


def test_load_local_state_returns_none_for_missing_version(tmp_path: Path) -> None:
    """Test that load_local_state returns None when version field missing."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    state_file = erk_dir / LOCAL_STATE_FILENAME
    state_file.write_text(
        "[local_init]\ntimestamp = '2025-12-31T16:00:00'\n",
        encoding="utf-8",
    )

    result = load_local_state(tmp_path)

    assert result is None


def test_load_local_state_returns_none_for_missing_timestamp(tmp_path: Path) -> None:
    """Test that load_local_state returns None when timestamp field missing."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    state_file = erk_dir / LOCAL_STATE_FILENAME
    state_file.write_text(
        "[local_init]\ninitialized_version = '0.3.0'\n",
        encoding="utf-8",
    )

    result = load_local_state(tmp_path)

    assert result is None


def test_create_local_init_state_creates_state_with_version() -> None:
    """Test that create_local_init_state creates state with given version."""
    state = create_local_init_state("0.3.0")

    assert state.initialized_version == "0.3.0"
    # Timestamp should be a valid ISO format string
    assert "T" in state.timestamp


def test_create_local_init_state_uses_current_timestamp() -> None:
    """Test that create_local_init_state uses a recent timestamp."""
    from datetime import datetime

    before = datetime.now()
    state = create_local_init_state("0.3.0")
    after = datetime.now()

    # Parse the timestamp and verify it's between before and after
    timestamp = datetime.fromisoformat(state.timestamp)
    assert before <= timestamp <= after


def test_local_init_state_is_frozen() -> None:
    """Test that LocalInitState is immutable."""
    state = LocalInitState(
        initialized_version="0.3.0",
        timestamp="2025-12-31T16:00:00",
    )

    # Attempting to modify should raise
    try:
        state.initialized_version = "0.4.0"  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except AttributeError:
        pass  # Expected for frozen dataclass
