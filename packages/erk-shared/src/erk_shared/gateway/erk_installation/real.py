"""Real ErkInstallation implementation.

RealErkInstallation provides production filesystem access to ~/.erk/ directory
for config, command history, and version tracking.
"""

import os
import tomllib
from pathlib import Path

from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.abc import ErkInstallation


def _installation_path() -> Path:
    """Return path to erk installation directory.

    Note: Not cached to allow tests to monkeypatch Path.home().
    The performance impact is negligible since Path.home() is fast.
    """
    return Path.home() / ".erk"


class RealErkInstallation(ErkInstallation):
    """Production implementation that reads/writes ~/.erk/ directory."""

    # --- Config operations ---

    def config_exists(self) -> bool:
        """Check if global config file exists."""
        return self.config_path().exists()

    def load_config(self) -> GlobalConfig:
        """Load global config from ~/.erk/config.toml.

        Returns:
            GlobalConfig instance with loaded values

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is missing required fields or malformed
        """
        config_path = self.config_path()

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

    def save_config(self, config: GlobalConfig) -> None:
        """Save global config to ~/.erk/config.toml.

        Args:
            config: GlobalConfig instance to save

        Raises:
            PermissionError: If directory or file cannot be written
        """
        config_path = self.config_path()
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

    def config_path(self) -> Path:
        """Get path to config file.

        Returns:
            Path to ~/.erk/config.toml
        """
        return _installation_path() / "config.toml"

    # --- Command history operations ---

    def get_command_log_path(self) -> Path:
        """Get path to command history log file.

        Returns:
            Path to ~/.erk/command_history.jsonl
        """
        return _installation_path() / "command_history.jsonl"

    # --- Version tracking operations ---

    def get_last_seen_version(self) -> str | None:
        """Get the last version user was notified about.

        Returns:
            Version string if tracking file exists, None otherwise
        """
        path = _installation_path() / "last_seen_version"
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8").strip()

    def update_last_seen_version(self, version: str) -> None:
        """Update the last seen version tracking file.

        Args:
            version: Version string to record
        """
        path = _installation_path() / "last_seen_version"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(version, encoding="utf-8")
