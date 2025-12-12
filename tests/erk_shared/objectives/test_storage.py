"""Tests for objective storage implementations."""

from pathlib import Path

import pytest

from erk_shared.objectives.storage import (
    FakeObjectiveStore,
    FileObjectiveStore,
)
from erk_shared.objectives.types import (
    NoteEntry,
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
    WorkLogEntry,
)


class TestFileObjectiveStore:
    """Tests for FileObjectiveStore."""

    def test_list_objectives_empty_when_no_directory(self, tmp_path: Path) -> None:
        """Should return empty list when objectives directory doesn't exist."""
        store = FileObjectiveStore()

        result = store.list_objectives(tmp_path)

        assert result == []

    def test_list_objectives_returns_directories_with_readme(self, tmp_path: Path) -> None:
        """Should return objective names for directories containing README.md."""
        store = FileObjectiveStore()

        # Create objectives directory
        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)

        # Create valid objective
        obj1 = objectives_dir / "obj-one"
        obj1.mkdir()
        (obj1 / "README.md").write_text("# Objective", encoding="utf-8")

        # Create another valid objective
        obj2 = objectives_dir / "obj-two"
        obj2.mkdir()
        (obj2 / "README.md").write_text("# Objective", encoding="utf-8")

        # Create directory without README (should be ignored)
        obj3 = objectives_dir / "obj-invalid"
        obj3.mkdir()

        result = store.list_objectives(tmp_path)

        assert sorted(result) == ["obj-one", "obj-two"]

    def test_objective_exists_returns_true_for_valid_objective(self, tmp_path: Path) -> None:
        """Should return True when objective directory has README.md."""
        store = FileObjectiveStore()

        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)
        obj = objectives_dir / "my-obj"
        obj.mkdir()
        (obj / "README.md").write_text("# Objective", encoding="utf-8")

        assert store.objective_exists(tmp_path, "my-obj") is True

    def test_objective_exists_returns_false_for_missing_objective(self, tmp_path: Path) -> None:
        """Should return False when objective doesn't exist."""
        store = FileObjectiveStore()

        assert store.objective_exists(tmp_path, "nonexistent") is False

    def test_get_readme_content_returns_content(self, tmp_path: Path) -> None:
        """Should return README.md content."""
        store = FileObjectiveStore()

        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)
        obj = objectives_dir / "my-obj"
        obj.mkdir()
        (obj / "README.md").write_text("# My Objective\n\nContent here.", encoding="utf-8")

        result = store.get_readme_content(tmp_path, "my-obj")

        assert "My Objective" in result
        assert "Content here" in result

    def test_get_readme_content_raises_for_missing(self, tmp_path: Path) -> None:
        """Should raise ValueError when objective doesn't exist."""
        store = FileObjectiveStore()

        with pytest.raises(ValueError, match="Objective not found"):
            store.get_readme_content(tmp_path, "nonexistent")

    def test_get_notes_content_returns_content(self, tmp_path: Path) -> None:
        """Should return notes.md content."""
        store = FileObjectiveStore()

        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)
        obj = objectives_dir / "my-obj"
        obj.mkdir()
        (obj / "README.md").write_text("# Objective", encoding="utf-8")
        (obj / "notes.md").write_text("# Notes\n\nSome notes.", encoding="utf-8")

        result = store.get_notes_content(tmp_path, "my-obj")

        assert result is not None
        assert "Notes" in result

    def test_get_notes_content_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when notes.md doesn't exist."""
        store = FileObjectiveStore()

        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)
        obj = objectives_dir / "my-obj"
        obj.mkdir()
        (obj / "README.md").write_text("# Objective", encoding="utf-8")

        result = store.get_notes_content(tmp_path, "my-obj")

        assert result is None

    def test_append_work_log_creates_file(self, tmp_path: Path) -> None:
        """Should create work-log.md when appending to new objective."""
        store = FileObjectiveStore()

        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)
        obj = objectives_dir / "my-obj"
        obj.mkdir()
        (obj / "README.md").write_text("# Objective", encoding="utf-8")

        entry = WorkLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            event_type="turn_started",
            summary="Started evaluation turn.",
            details={"files_checked": 5},
        )

        store.append_work_log(tmp_path, "my-obj", entry)

        work_log_path = obj / "work-log.md"
        assert work_log_path.exists()
        content = work_log_path.read_text(encoding="utf-8")
        assert "2024-01-15T10:30:00Z" in content
        assert "turn_started" in content
        assert "Started evaluation turn" in content
        assert "files_checked: 5" in content

    def test_append_work_log_appends_to_existing(self, tmp_path: Path) -> None:
        """Should append to existing work-log.md."""
        store = FileObjectiveStore()

        objectives_dir = tmp_path / ".erk" / "objectives"
        objectives_dir.mkdir(parents=True)
        obj = objectives_dir / "my-obj"
        obj.mkdir()
        (obj / "README.md").write_text("# Objective", encoding="utf-8")
        (obj / "work-log.md").write_text("# Work Log: my-obj\n\n", encoding="utf-8")

        entry = WorkLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            event_type="turn_completed",
            summary="Completed turn.",
        )

        store.append_work_log(tmp_path, "my-obj", entry)

        work_log_path = obj / "work-log.md"
        content = work_log_path.read_text(encoding="utf-8")
        assert content.count("# Work Log") == 1  # Only one header
        assert "turn_completed" in content

    def test_append_work_log_raises_for_missing_objective(self, tmp_path: Path) -> None:
        """Should raise ValueError when objective doesn't exist."""
        store = FileObjectiveStore()

        entry = WorkLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            event_type="test",
            summary="Test.",
        )

        with pytest.raises(ValueError, match="Objective not found"):
            store.append_work_log(tmp_path, "nonexistent", entry)


class TestFakeObjectiveStore:
    """Tests for FakeObjectiveStore."""

    def test_list_objectives_returns_configured_names(self) -> None:
        """Should return names of configured objectives."""
        definition = ObjectiveDefinition(
            name="test-obj",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="test",
            rationale="test",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="test",
            plan_sizing_prompt="test",
        )
        store = FakeObjectiveStore(objectives={"test-obj": definition})

        result = store.list_objectives(Path("/repo"))

        assert result == ["test-obj"]

    def test_objective_exists_returns_true_for_configured(self) -> None:
        """Should return True for configured objectives."""
        definition = ObjectiveDefinition(
            name="test-obj",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="test",
            rationale="test",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="test",
            plan_sizing_prompt="test",
        )
        store = FakeObjectiveStore(objectives={"test-obj": definition})

        assert store.objective_exists(Path("/repo"), "test-obj") is True
        assert store.objective_exists(Path("/repo"), "other") is False

    def test_get_objective_definition_returns_configured(self) -> None:
        """Should return configured definition."""
        definition = ObjectiveDefinition(
            name="test-obj",
            objective_type=ObjectiveType.PERPETUAL,
            desired_state="no bugs",
            rationale="quality",
            examples=["example"],
            scope_includes=["src/"],
            scope_excludes=["tests/"],
            evaluation_prompt="check",
            plan_sizing_prompt="small",
        )
        store = FakeObjectiveStore(objectives={"test-obj": definition})

        result = store.get_objective_definition(Path("/repo"), "test-obj")

        assert result == definition

    def test_get_objective_definition_raises_for_missing(self) -> None:
        """Should raise ValueError for unconfigured objective."""
        store = FakeObjectiveStore()

        with pytest.raises(ValueError, match="Objective not found"):
            store.get_objective_definition(Path("/repo"), "nonexistent")

    def test_get_notes_returns_configured(self) -> None:
        """Should return configured notes."""
        notes = ObjectiveNotes(
            entries=[
                NoteEntry(timestamp="2024-01-15", content="note 1"),
                NoteEntry(timestamp="2024-01-16", content="note 2"),
            ]
        )
        store = FakeObjectiveStore(notes={"test-obj": notes})

        result = store.get_notes(Path("/repo"), "test-obj")

        assert len(result.entries) == 2

    def test_get_notes_returns_empty_for_unconfigured(self) -> None:
        """Should return empty notes for objective without notes."""
        definition = ObjectiveDefinition(
            name="test-obj",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="test",
            rationale="test",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="test",
            plan_sizing_prompt="test",
        )
        store = FakeObjectiveStore(objectives={"test-obj": definition})

        result = store.get_notes(Path("/repo"), "test-obj")

        assert len(result.entries) == 0

    def test_append_work_log_tracks_calls(self) -> None:
        """Should track work log append calls."""
        definition = ObjectiveDefinition(
            name="test-obj",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="test",
            rationale="test",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="test",
            plan_sizing_prompt="test",
        )
        store = FakeObjectiveStore(objectives={"test-obj": definition})

        entry = WorkLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            event_type="test",
            summary="Test entry.",
        )

        store.append_work_log(Path("/repo"), "test-obj", entry)

        assert len(store.work_log_entries) == 1
        assert store.work_log_entries[0][0] == "test-obj"
        assert store.work_log_entries[0][1] == entry

    def test_append_work_log_raises_for_missing_objective(self) -> None:
        """Should raise ValueError when objective not configured."""
        store = FakeObjectiveStore()

        entry = WorkLogEntry(
            timestamp="2024-01-15T10:30:00Z",
            event_type="test",
            summary="Test.",
        )

        with pytest.raises(ValueError, match="Objective not found"):
            store.append_work_log(Path("/repo"), "nonexistent", entry)
