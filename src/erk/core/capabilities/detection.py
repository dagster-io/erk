"""Fast detection helpers for capabilities.

These functions provide fast checks for use in performance-critical paths like hooks.
"""

from pathlib import Path

import tomli


def is_reminder_installed(repo_root: Path, reminder_name: str) -> bool:
    """Check if a reminder capability is installed via state.toml.

    This is a fast check designed for use in hooks where performance matters.

    Args:
        repo_root: Path to the repository root.
        reminder_name: Name of the reminder (e.g., 'devrun', 'dignified-python').

    Returns:
        True if the reminder is in the installed list, False otherwise.
    """
    state_path = repo_root / ".erk" / "state.toml"
    if not state_path.exists():
        return False

    with state_path.open("rb") as f:
        data = tomli.load(f)

    reminders = data.get("reminders", {})
    installed = reminders.get("installed", [])
    return reminder_name in installed
