"""Fake ErkInstallation implementation for testing.

FakeErkInstallation is a test double with constructor-injected values,
enabling tests to control bundled paths and version without mocking.
"""

from pathlib import Path

from erk_shared.gateway.installation.abc import ErkInstallation


class FakeErkInstallation(ErkInstallation):
    """Test double with constructor-injected values.

    This class has NO public setup methods. All state is provided via constructor.
    """

    def __init__(
        self,
        *,
        bundled_claude_dir: Path,
        bundled_github_dir: Path,
        current_version: str,
    ) -> None:
        """Create FakeErkInstallation with specified paths and version.

        Args:
            bundled_claude_dir: Path to return from get_bundled_claude_dir()
            bundled_github_dir: Path to return from get_bundled_github_dir()
            current_version: Version string to return from get_current_version()
        """
        self._bundled_claude_dir = bundled_claude_dir
        self._bundled_github_dir = bundled_github_dir
        self._current_version = current_version

    def get_bundled_claude_dir(self) -> Path:
        """Get the configured bundled .claude/ directory path."""
        return self._bundled_claude_dir

    def get_bundled_github_dir(self) -> Path:
        """Get the configured bundled .github/ directory path."""
        return self._bundled_github_dir

    def get_current_version(self) -> str:
        """Get the configured version string."""
        return self._current_version
