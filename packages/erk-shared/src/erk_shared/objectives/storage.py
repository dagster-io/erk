"""Objective storage abstraction.

Provides file-based storage for objectives in the repository's .erk/objectives/ directory.

Import from this module:
- ObjectiveStore (ABC)
- FileObjectiveStore (production)
- FakeObjectiveStore (testing)
"""

from abc import ABC, abstractmethod
from pathlib import Path

from erk_shared.objectives.types import (
    ObjectiveDefinition,
    ObjectiveNotes,
    WorkLogEntry,
)


class ObjectiveStore(ABC):
    """Abstract interface for objective persistence operations.

    Objectives are stored in the repository under .erk/objectives/<name>/:
    - README.md: Objective definition (stable)
    - notes.md: Accumulated knowledge from turns
    - work-log.md: Chronological record (observability)
    """

    @abstractmethod
    def list_objectives(self, repo_root: Path) -> list[str]:
        """List all objective names in the repository.

        Returns:
            List of objective names (directory names under .erk/objectives/)
        """
        ...

    @abstractmethod
    def objective_exists(self, repo_root: Path, name: str) -> bool:
        """Check if an objective exists.

        Args:
            repo_root: Repository root path
            name: Objective name

        Returns:
            True if objective directory exists with README.md
        """
        ...

    @abstractmethod
    def get_objective_definition(self, repo_root: Path, name: str) -> ObjectiveDefinition:
        """Get objective definition by name.

        Args:
            repo_root: Repository root path
            name: Objective name

        Returns:
            Parsed ObjectiveDefinition

        Raises:
            ValueError: If objective not found or README.md is invalid
        """
        ...

    @abstractmethod
    def get_notes(self, repo_root: Path, name: str) -> ObjectiveNotes:
        """Get accumulated knowledge for an objective.

        Args:
            repo_root: Repository root path
            name: Objective name

        Returns:
            ObjectiveNotes (empty entries if notes.md doesn't exist)
        """
        ...

    @abstractmethod
    def append_work_log(self, repo_root: Path, name: str, entry: WorkLogEntry) -> None:
        """Append entry to work log.

        Args:
            repo_root: Repository root path
            name: Objective name
            entry: Work log entry to append

        Raises:
            ValueError: If objective not found
        """
        ...

    @abstractmethod
    def get_readme_content(self, repo_root: Path, name: str) -> str:
        """Get raw README.md content for an objective.

        Args:
            repo_root: Repository root path
            name: Objective name

        Returns:
            Raw markdown content

        Raises:
            ValueError: If objective not found
        """
        ...

    @abstractmethod
    def get_notes_content(self, repo_root: Path, name: str) -> str | None:
        """Get raw notes.md content for an objective.

        Args:
            repo_root: Repository root path
            name: Objective name

        Returns:
            Raw markdown content, or None if notes.md doesn't exist
        """
        ...


class FileObjectiveStore(ObjectiveStore):
    """Production implementation using filesystem storage.

    Reads/writes objectives from .erk/objectives/ directory in the repository.
    """

    def _objectives_dir(self, repo_root: Path) -> Path:
        """Return path to objectives directory."""
        return repo_root / ".erk" / "objectives"

    def _objective_dir(self, repo_root: Path, name: str) -> Path:
        """Return path to specific objective directory."""
        return self._objectives_dir(repo_root) / name

    def list_objectives(self, repo_root: Path) -> list[str]:
        """List all objective names in the repository."""
        objectives_dir = self._objectives_dir(repo_root)
        if not objectives_dir.exists():
            return []

        objectives: list[str] = []
        for item in objectives_dir.iterdir():
            if item.is_dir():
                readme = item / "README.md"
                if readme.exists():
                    objectives.append(item.name)

        return sorted(objectives)

    def objective_exists(self, repo_root: Path, name: str) -> bool:
        """Check if an objective exists."""
        objective_dir = self._objective_dir(repo_root, name)
        readme = objective_dir / "README.md"
        return readme.exists()

    def get_objective_definition(self, repo_root: Path, name: str) -> ObjectiveDefinition:
        """Get objective definition by name."""
        from erk_shared.objectives.parser import parse_objective_definition

        content = self.get_readme_content(repo_root, name)
        return parse_objective_definition(name, content)

    def get_notes(self, repo_root: Path, name: str) -> ObjectiveNotes:
        """Get accumulated knowledge for an objective."""
        from erk_shared.objectives.parser import parse_objective_notes

        content = self.get_notes_content(repo_root, name)
        if content is None:
            return ObjectiveNotes(entries=[])
        return parse_objective_notes(content)

    def append_work_log(self, repo_root: Path, name: str, entry: WorkLogEntry) -> None:
        """Append entry to work log."""
        if not self.objective_exists(repo_root, name):
            raise ValueError(f"Objective not found: {name}")

        objective_dir = self._objective_dir(repo_root, name)
        work_log_path = objective_dir / "work-log.md"

        # Format entry
        entry_lines = [
            f"## {entry.timestamp}",
            "",
            f"**Event:** {entry.event_type}",
            "",
            entry.summary,
        ]

        if entry.details:
            entry_lines.append("")
            entry_lines.append("**Details:**")
            for key, value in entry.details.items():
                entry_lines.append(f"- {key}: {value}")

        entry_lines.append("")
        entry_lines.append("---")
        entry_lines.append("")

        entry_text = "\n".join(entry_lines)

        # Append to file (create if needed)
        if work_log_path.exists():
            existing = work_log_path.read_text(encoding="utf-8")
            work_log_path.write_text(existing + entry_text, encoding="utf-8")
        else:
            header = f"# Work Log: {name}\n\n"
            work_log_path.write_text(header + entry_text, encoding="utf-8")

    def get_readme_content(self, repo_root: Path, name: str) -> str:
        """Get raw README.md content for an objective."""
        objective_dir = self._objective_dir(repo_root, name)
        readme = objective_dir / "README.md"

        if not readme.exists():
            raise ValueError(f"Objective not found: {name}")

        return readme.read_text(encoding="utf-8")

    def get_notes_content(self, repo_root: Path, name: str) -> str | None:
        """Get raw notes.md content for an objective."""
        objective_dir = self._objective_dir(repo_root, name)
        notes_path = objective_dir / "notes.md"

        if not notes_path.exists():
            return None

        return notes_path.read_text(encoding="utf-8")


class FakeObjectiveStore(ObjectiveStore):
    """In-memory implementation for testing.

    All state is provided via constructor parameters. Tracks mutations
    for test assertions.
    """

    def __init__(
        self,
        *,
        objectives: dict[str, ObjectiveDefinition] | None = None,
        notes: dict[str, ObjectiveNotes] | None = None,
        readme_contents: dict[str, str] | None = None,
        notes_contents: dict[str, str] | None = None,
    ) -> None:
        """Initialize fake with test state.

        Args:
            objectives: Map of objective name to definition
            notes: Map of objective name to notes
            readme_contents: Map of objective name to raw README content
            notes_contents: Map of objective name to raw notes content
        """
        self._objectives = objectives or {}
        self._notes = notes or {}
        self._readme_contents = readme_contents or {}
        self._notes_contents = notes_contents or {}

        # Track mutations
        self._work_log_entries: list[tuple[str, WorkLogEntry]] = []

    def list_objectives(self, repo_root: Path) -> list[str]:
        """List all objective names."""
        return sorted(self._objectives.keys())

    def objective_exists(self, repo_root: Path, name: str) -> bool:
        """Check if an objective exists."""
        return name in self._objectives

    def get_objective_definition(self, repo_root: Path, name: str) -> ObjectiveDefinition:
        """Get objective definition by name."""
        if name not in self._objectives:
            raise ValueError(f"Objective not found: {name}")
        return self._objectives[name]

    def get_notes(self, repo_root: Path, name: str) -> ObjectiveNotes:
        """Get accumulated knowledge for an objective."""
        return self._notes.get(name, ObjectiveNotes(entries=[]))

    def append_work_log(self, repo_root: Path, name: str, entry: WorkLogEntry) -> None:
        """Append entry to work log."""
        if name not in self._objectives:
            raise ValueError(f"Objective not found: {name}")
        self._work_log_entries.append((name, entry))

    def get_readme_content(self, repo_root: Path, name: str) -> str:
        """Get raw README.md content for an objective."""
        if name not in self._readme_contents:
            raise ValueError(f"Objective not found: {name}")
        return self._readme_contents[name]

    def get_notes_content(self, repo_root: Path, name: str) -> str | None:
        """Get raw notes.md content for an objective."""
        return self._notes_contents.get(name)

    # Properties to expose tracked mutations for test assertions

    @property
    def work_log_entries(self) -> list[tuple[str, WorkLogEntry]]:
        """Get all work log entries that were appended."""
        return list(self._work_log_entries)
