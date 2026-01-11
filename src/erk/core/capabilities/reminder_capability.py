"""Base class for reminder capabilities.

ReminderCapability provides a common pattern for capabilities that control
whether specific reminders are injected by the user prompt hook.

Each reminder capability:
- Stores state in `.erk/state.toml` under [reminders] section
- Is marked as required=False (opt-in, not auto-installed)
- Follows the naming convention `{reminder_name}-reminder`
"""

from abc import abstractmethod
from pathlib import Path
from typing import Any

import tomli
import tomli_w

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)


def _state_file_path(repo_root: Path) -> Path:
    """Return path to state file."""
    return repo_root / ".erk" / "state.toml"


def _load_installed_reminders(repo_root: Path) -> list[str]:
    """Load list of installed reminders from state.toml."""
    state_path = _state_file_path(repo_root)
    if not state_path.exists():
        return []

    with state_path.open("rb") as f:
        data = tomli.load(f)

    reminders = data.get("reminders", {})
    return reminders.get("installed", [])


def _save_installed_reminders(repo_root: Path, installed: list[str]) -> None:
    """Save list of installed reminders to state.toml."""
    state_path = _state_file_path(repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing data to preserve other sections
    existing_data: dict[str, Any] = {}
    if state_path.exists():
        with state_path.open("rb") as f:
            existing_data = tomli.load(f)

    # Update reminders section
    existing_data["reminders"] = {"installed": sorted(installed)}

    with state_path.open("wb") as f:
        tomli_w.dump(existing_data, f)


class ReminderCapability(Capability):
    """Base class for capabilities that control reminder injection.

    Subclasses only need to implement reminder_name and description.
    The base class handles state management in state.toml.
    """

    @property
    @abstractmethod
    def reminder_name(self) -> str:
        """Name of the reminder (e.g., 'devrun', 'dignified-python')."""
        ...

    @property
    def name(self) -> str:
        """CLI-facing identifier - follows pattern '{reminder_name}-reminder'."""
        return f"{self.reminder_name}-reminder"

    @property
    def scope(self) -> CapabilityScope:
        """Reminder capabilities are project-level."""
        return "project"

    @property
    def required(self) -> bool:
        """Reminders are opt-in, not auto-installed during erk init."""
        return False

    @property
    def installation_check_description(self) -> str:
        """Human-readable description of what is_installed() checks."""
        return f"'{self.reminder_name}' in .erk/state.toml [reminders] section"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        """List of artifacts this capability installs.

        Reminders don't create separate files - they store state in state.toml.
        """
        return []

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if this reminder is in the installed list in state.toml."""
        if repo_root is None:
            return False
        installed = _load_installed_reminders(repo_root)
        return self.reminder_name in installed

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Add this reminder to the installed list in state.toml."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="ReminderCapability requires repo_root",
            )

        installed = _load_installed_reminders(repo_root)

        if self.reminder_name in installed:
            return CapabilityResult(
                success=True,
                message=f"{self.name} already installed",
            )

        # Add to installed list and save
        installed.append(self.reminder_name)
        _save_installed_reminders(repo_root, installed)

        return CapabilityResult(
            success=True,
            message=f"Installed {self.name} capability",
        )
