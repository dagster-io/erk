"""Installation context models."""

from pathlib import Path


class InstallationContext:
    """Context for installation operations."""

    def __init__(self, base_path: Path):
        """Initialize installation context.

        Args:
            base_path: Base path for the installation (project directory)
        """
        self.base_path = base_path

    def get_claude_dir(self) -> Path:
        """Get the .claude directory path for this installation."""
        return self.base_path / ".claude"

    def get_config_path(self) -> Path:
        """Get the dot-agent.toml path for this installation."""
        return self.base_path / "dot-agent.toml"
