"""Fake implementation of UserLevelClaudeSettingsStore for testing."""

from pathlib import Path

from erk_shared.gateway.claude_settings.abc import UserLevelClaudeSettingsStore


class FakeUserLevelClaudeSettingsStore(UserLevelClaudeSettingsStore):
    """Test implementation - in-memory storage, no filesystem access.

    This fake provides:
    - In-memory storage that never touches the real filesystem
    - Constructor injection for initial state
    - Mutation tracking via read-only properties

    The global_settings_path is configurable and defaults to a fake path,
    never returning the real Path.home(). This ensures tests cannot
    accidentally read or write to ~/.claude/settings.json.

    Usage:
        # Basic usage - empty store with fake path
        store = FakeUserLevelClaudeSettingsStore()

        # Pre-populated with initial settings
        store = FakeUserLevelClaudeSettingsStore(
            initial_settings={
                Path("/fake/.claude/settings.json"): {"permissions": {"allow": []}}
            }
        )

        # Verify writes in tests
        store.write(path, new_settings)
        assert path in store.writes
        assert store.writes[path] == new_settings
    """

    def __init__(
        self,
        global_settings_path: Path | None = None,
        initial_settings: dict[Path, dict] | None = None,
    ) -> None:
        """Initialize fake store with optional pre-populated state.

        Args:
            global_settings_path: Path to return from get_global_settings_path().
                Defaults to Path("/fake/.claude/settings.json") to ensure
                it's never confused with the real path.
            initial_settings: Optional mapping of path -> settings dict to
                pre-populate the store for testing scenarios.
        """
        self._global_path = global_settings_path or Path("/fake/.claude/settings.json")
        self._storage: dict[Path, dict] = dict(initial_settings or {})
        self._writes: dict[Path, dict] = {}

    def get_global_settings_path(self) -> Path:
        """Get path to global Claude settings.

        Returns:
            The configured fake path (never Path.home())
        """
        return self._global_path

    def read(self, path: Path) -> dict | None:
        """Read settings from in-memory storage.

        Args:
            path: Path to settings file

        Returns:
            Stored settings dict, or None if not in storage
        """
        if path not in self._storage:
            return None
        return self._storage[path]

    def write(self, path: Path, settings: dict) -> Path | None:
        """Write settings to in-memory storage.

        Does not create actual backups - just stores the new settings.

        Args:
            path: Path to settings file
            settings: Settings dict to store

        Returns:
            None (fake never creates real backups)
        """
        self._storage[path] = settings
        self._writes[path] = settings
        return None

    @property
    def writes(self) -> dict[Path, dict]:
        """Read-only access to all writes for test assertions.

        Returns:
            Mapping of path -> settings for each write that occurred
        """
        return dict(self._writes)

    @property
    def storage(self) -> dict[Path, dict]:
        """Read-only access to current storage state for test assertions.

        Returns:
            Mapping of path -> settings for current state
        """
        return dict(self._storage)
