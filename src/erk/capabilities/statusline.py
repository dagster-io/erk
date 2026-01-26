"""StatuslineCapability - user-level capability for Claude Code statusline configuration."""

from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.claude_settings import (
    add_erk_statusline,
    has_erk_statusline,
    remove_erk_statusline,
)
from erk_shared.learn.extraction.claude_installation.abc import ClaudeInstallation
from erk_shared.learn.extraction.claude_installation.real import RealClaudeInstallation


class StatuslineCapability(Capability):
    """Capability for configuring the Claude Code status line.

    This is a user-level capability that modifies ~/.claude/settings.json.
    Unlike project-level capabilities, it does not require being in a git repository.
    """

    def __init__(
        self,
        *,
        claude_installation: ClaudeInstallation | None,
    ) -> None:
        """Initialize StatuslineCapability.

        Args:
            claude_installation: ClaudeInstallation for testability.
                                 If None, uses RealClaudeInstallation.
        """
        self._claude_installation = claude_installation or RealClaudeInstallation()

    @property
    def name(self) -> str:
        return "statusline"

    @property
    def description(self) -> str:
        return "Claude Code status line configuration"

    @property
    def scope(self) -> CapabilityScope:
        return "user"

    @property
    def installation_check_description(self) -> str:
        return "statusLine configured in ~/.claude/settings.json"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # settings.json is shared by multiple capabilities, so not listed here
        return []

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if erk-statusline is configured in Claude settings."""
        # User-level capability ignores repo_root
        _ = repo_root
        settings = self._claude_installation.read_settings()
        return has_erk_statusline(settings)

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Configure erk-statusline in ~/.claude/settings.json."""
        # User-level capability ignores repo_root
        _ = repo_root

        # Read current settings
        settings = self._claude_installation.read_settings()

        # Check if already configured
        if has_erk_statusline(settings):
            return CapabilityResult(
                success=True,
                message="erk-statusline already configured",
            )

        # Add statusline configuration
        new_settings = add_erk_statusline(settings)

        # Write updated settings
        self._claude_installation.write_settings(new_settings)

        return CapabilityResult(
            success=True,
            message="Configured erk-statusline in ~/.claude/settings.json",
            created_files=("~/.claude/settings.json",),
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove erk-statusline from ~/.claude/settings.json."""
        # User-level capability ignores repo_root
        _ = repo_root

        # Read current settings
        settings = self._claude_installation.read_settings()

        # Check if installed
        if not has_erk_statusline(settings):
            return CapabilityResult(
                success=True,
                message="statusline not installed",
            )

        # Remove statusline configuration
        new_settings = remove_erk_statusline(settings)

        # Write updated settings
        self._claude_installation.write_settings(new_settings)

        return CapabilityResult(
            success=True,
            message="Removed erk-statusline from ~/.claude/settings.json",
        )
