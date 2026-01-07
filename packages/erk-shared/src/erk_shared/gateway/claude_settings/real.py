"""Real implementation of UserLevelClaudeSettingsStore - reads/writes real filesystem."""

import json
from pathlib import Path

from erk_shared.gateway.claude_settings.abc import UserLevelClaudeSettingsStore


class RealUserLevelClaudeSettingsStore(UserLevelClaudeSettingsStore):
    """Production implementation - reads/writes real filesystem.

    This is the only implementation that should access Path.home() or the
    real ~/.claude/ directory. All other code accesses settings through
    ErkContext.claude_settings_store.
    """

    def get_global_settings_path(self) -> Path:
        """Get path to global Claude settings (~/.claude/settings.json).

        Returns:
            Path to ~/.claude/settings.json
        """
        return Path.home() / ".claude" / "settings.json"

    def read(self, path: Path) -> dict | None:
        """Read and parse Claude settings from disk.

        Args:
            path: Path to settings.json file

        Returns:
            Parsed settings dict, or None if file doesn't exist

        Raises:
            json.JSONDecodeError: If file contains invalid JSON
            OSError: If file cannot be read
        """
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")
        return json.loads(content)

    def write(self, path: Path, settings: dict) -> Path | None:
        """Write Claude settings to disk.

        Creates a backup of the existing file before writing (if it exists).

        Args:
            path: Path to settings.json file
            settings: Settings dict to write

        Returns:
            Path to backup file if created, None if no backup was needed

        Raises:
            PermissionError: If unable to write to file
            OSError: If unable to write to file
        """
        # Create backup of existing file (if it exists)
        backup_path: Path | None = None
        if path.exists():
            backup_path = path.with_suffix(".json.bak")
            backup_path.write_bytes(path.read_bytes())

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write with pretty formatting to match Claude's style
        content = json.dumps(settings, indent=2)
        path.write_text(content, encoding="utf-8")

        return backup_path
