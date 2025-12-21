"""Global configuration data structures and loading.

Provides the RealConfigStore implementation and re-exports ABC and types
from erk_shared.core for backward compatibility.
"""

import os
import tomllib
from pathlib import Path

# Re-export ABC and types from erk_shared.core for backward compatibility
from erk_shared.context.types import GlobalConfig as GlobalConfig
from erk_shared.core.config_store import ConfigStore as ConfigStore


class RealConfigStore(ConfigStore):
    """Production implementation that reads/writes ~/.erk/config.toml."""

    def exists(self) -> bool:
        """Check if global config file exists."""
        return self.path().exists()

    def load(self) -> GlobalConfig:
        """Load global config from ~/.erk/config.toml.

        Returns:
            GlobalConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is missing required fields or malformed
        """
        config_path = self.path()

        if not config_path.exists():
            raise FileNotFoundError(f"Global config not found at {config_path}")

        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        root = data.get("erk_root")
        if not root:
            raise ValueError(f"Missing 'erk_root' in {config_path}")

        return GlobalConfig(
            erk_root=Path(root).expanduser().resolve(),
            use_graphite=bool(data.get("use_graphite", False)),
            shell_setup_complete=bool(data.get("shell_setup_complete", False)),
            show_pr_info=bool(data.get("show_pr_info", True)),
            github_planning=bool(data.get("github_planning", True)),
            auto_restack_require_dangerous_flag=bool(
                data.get("auto_restack_require_dangerous_flag", True)
            ),
            show_hidden_commands=bool(data.get("show_hidden_commands", False)),
        )

    def save(self, config: GlobalConfig) -> None:
        """Save global config to ~/.erk/config.toml.

        Args:
            config: GlobalConfig instance to save

        Raises:
            PermissionError: If directory or file cannot be written
        """
        config_path = self.path()
        parent = config_path.parent

        # Check parent directory permissions BEFORE attempting mkdir
        if parent.exists() and not os.access(parent, os.W_OK):
            raise PermissionError(
                f"Cannot write to directory: {parent}\n"
                f"The directory exists but is not writable.\n\n"
                f"To fix this manually:\n"
                f"  1. Create the config file: touch {config_path}\n"
                f"  2. Edit it with your preferred editor\n"
                f"  3. Add: shell_setup_complete = true"
            )

        # Try to create directory structure
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError(
                f"Cannot create directory: {parent}\n"
                f"Check permissions on your home directory.\n\n"
                f"To fix this manually:\n"
                f"  1. Create the directory: mkdir -p {parent}\n"
                f"  2. Ensure it's writable: chmod 755 {parent}\n"
                f"  3. Run erk init --shell again"
            ) from None

        # Check file writability BEFORE attempting write
        if config_path.exists() and not os.access(config_path, os.W_OK):
            raise PermissionError(
                f"Cannot write to file: {config_path}\n"
                f"The file exists but is not writable.\n\n"
                f"To fix this manually:\n"
                f"  1. Make it writable: chmod 644 {config_path}\n"
                f"  2. Run erk init --shell again\n"
                f"  Or edit the file directly to add: shell_setup_complete = true"
            )

        content = f"""# Global erk configuration
erk_root = "{config.erk_root}"
use_graphite = {str(config.use_graphite).lower()}
shell_setup_complete = {str(config.shell_setup_complete).lower()}
show_pr_info = {str(config.show_pr_info).lower()}
github_planning = {str(config.github_planning).lower()}
auto_restack_require_dangerous_flag = {str(config.auto_restack_require_dangerous_flag).lower()}
show_hidden_commands = {str(config.show_hidden_commands).lower()}
"""

        try:
            config_path.write_text(content, encoding="utf-8")
        except PermissionError:
            raise PermissionError(
                f"Cannot write to file: {config_path}\n"
                f"Permission denied during write operation.\n\n"
                f"To fix this manually:\n"
                f"  1. Check parent directory permissions: ls -ld {parent}\n"
                f"  2. Ensure directory is writable: chmod 755 {parent}\n"
                f"  3. Create the file manually with the config content above"
            ) from None

    def path(self) -> Path:
        """Get the path to the global config file.

        Returns:
            Path to ~/.erk/config.toml
        """
        return Path.home() / ".erk" / "config.toml"


class FakeConfigStore(ConfigStore):
    """Test implementation that stores config in memory without touching filesystem."""

    def __init__(self, config: GlobalConfig | None = None) -> None:
        """Initialize in-memory config ops.

        Args:
            config: Initial config state (None = config doesn't exist)
        """
        self._config = config

    def exists(self) -> bool:
        """Check if global config exists in memory."""
        return self._config is not None

    def load(self) -> GlobalConfig:
        """Load global config from memory.

        Returns:
            GlobalConfig instance stored in memory

        Raises:
            FileNotFoundError: If config doesn't exist in memory
        """
        if self._config is None:
            raise FileNotFoundError(f"Global config not found at {self.path()}")
        return self._config

    def save(self, config: GlobalConfig) -> None:
        """Save global config to memory.

        Args:
            config: GlobalConfig instance to store
        """
        self._config = config

    def path(self) -> Path:
        """Get fake path for error messages.

        Returns:
            Path to fake config location (for error messages)
        """
        return Path("/fake/erk/config.toml")
