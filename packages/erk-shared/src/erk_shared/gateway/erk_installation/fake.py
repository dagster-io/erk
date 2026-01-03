"""Fake ErkInstallation implementation for testing.

FakeErkInstallation is an in-memory implementation that enables fast and
deterministic tests without touching the filesystem.
"""

from pathlib import Path

from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.abc import ErkInstallation


class FakeErkInstallation(ErkInstallation):
    """In-memory fake implementation that tracks mutations.

    This class has NO public setup methods beyond constructor.
    All state is provided via constructor or captured during execution.
    """

    def __init__(
        self,
        *,
        config: GlobalConfig | None = None,
        command_log_path: Path | None = None,
        last_seen_version: str | None = None,
    ) -> None:
        """Create FakeErkInstallation with optional initial state.

        Args:
            config: Initial config state (None = config doesn't exist)
            command_log_path: Custom command log path (defaults to /fake/erk/command_history.jsonl)
            last_seen_version: Pre-configured last seen version (None means no file exists)
        """
        self._config = config
        self._command_log_path = (
            command_log_path
            if command_log_path is not None
            else Path("/fake/erk/command_history.jsonl")
        )
        self._saved_configs: list[GlobalConfig] = []
        self._last_seen_version = last_seen_version
        self._version_updates: list[str] = []

    # --- Test assertions ---

    @property
    def saved_configs(self) -> list[GlobalConfig]:
        """Get list of configs that were saved.

        Returns a copy to prevent external mutation.
        This property is for test assertions only.
        """
        return list(self._saved_configs)

    @property
    def current_config(self) -> GlobalConfig | None:
        """Get current config state.

        This property is for test assertions only.
        """
        return self._config

    @property
    def version_updates(self) -> list[str]:
        """Get the list of version updates that were made.

        Returns a copy to prevent accidental mutation by tests.

        This property is for test assertions only.
        """
        return self._version_updates.copy()

    # --- Config operations ---

    def config_exists(self) -> bool:
        """Check if global config exists in memory."""
        return self._config is not None

    def load_config(self) -> GlobalConfig:
        """Load global config from memory.

        Returns:
            GlobalConfig instance stored in memory

        Raises:
            FileNotFoundError: If config doesn't exist in memory
        """
        if self._config is None:
            raise FileNotFoundError(f"Global config not found at {self.config_path()}")
        return self._config

    def save_config(self, config: GlobalConfig) -> None:
        """Save global config to memory.

        Args:
            config: GlobalConfig instance to store
        """
        self._config = config
        self._saved_configs.append(config)

    def config_path(self) -> Path:
        """Get fake path for error messages.

        Returns:
            Path to fake config location
        """
        return Path("/fake/erk/config.toml")

    # --- Command history operations ---

    def get_command_log_path(self) -> Path:
        """Get path to command history log file.

        Returns:
            The configured command log path
        """
        return self._command_log_path

    # --- Version tracking operations ---

    def get_last_seen_version(self) -> str | None:
        """Get the last version user was notified about.

        Returns:
            Version string if set, None otherwise
        """
        return self._last_seen_version

    def update_last_seen_version(self, version: str) -> None:
        """Update the last seen version.

        Tracks updates for test assertions.

        Args:
            version: Version string to record
        """
        self._last_seen_version = version
        self._version_updates.append(version)
