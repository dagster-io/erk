"""Ruff format capability for auto-formatting Python files after Write/Edit.

This capability installs a PostToolUse hook that automatically runs
`uv run ruff format` on Python files whenever Claude uses Write or Edit tools.
"""

import json
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)
from erk.core.claude_settings import (
    add_ruff_format_hook,
    get_repo_claude_settings_path,
    has_ruff_format_hook,
    write_claude_settings,
)


class RuffFormatCapability(Capability):
    """Capability to auto-format Python files with ruff after Write/Edit.

    This capability installs a PostToolUse hook that runs `uv run ruff format`
    on any Python file that Claude writes or edits.
    """

    @property
    def name(self) -> str:
        return "ruff-format"

    @property
    def description(self) -> str:
        return "Auto-format Python files with ruff after Write/Edit"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return "PostToolUse ruff format hook in .claude/settings.json"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # settings.json is shared by multiple capabilities, so not listed here
        return []

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare ruff-format hook as managed artifact."""
        return [ManagedArtifact(name="ruff-format-hook", artifact_type="hook")]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the ruff format hook is configured in settings.json."""
        if repo_root is None:
            return False

        settings_path = get_repo_claude_settings_path(repo_root)
        if not settings_path.exists():
            return False

        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        return has_ruff_format_hook(settings)

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Add ruff format hook to .claude/settings.json."""
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="RuffFormatCapability requires repo_root",
            )

        settings_path = get_repo_claude_settings_path(repo_root)
        created_files: list[str] = []

        # Load existing settings or create new
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                return CapabilityResult(
                    success=False,
                    message=f"Invalid JSON in .claude/settings.json: {e}",
                )
        else:
            # Create directory if needed
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings = {}
            created_files.append(".claude/settings.json")

        # Check if already installed
        if has_ruff_format_hook(settings):
            return CapabilityResult(
                success=True,
                message="Ruff format hook already configured",
            )

        # Add hook using the pure function
        new_settings = add_ruff_format_hook(settings)

        # Write back
        write_claude_settings(settings_path, new_settings)

        return CapabilityResult(
            success=True,
            message="Added ruff format hook to .claude/settings.json",
            created_files=tuple(created_files),
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove ruff format hook from .claude/settings.json."""
        from erk.core.claude_settings import remove_ruff_format_hook

        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="RuffFormatCapability requires repo_root",
            )

        settings_path = get_repo_claude_settings_path(repo_root)

        if not settings_path.exists():
            return CapabilityResult(
                success=True,
                message="ruff-format not installed (no settings.json)",
            )

        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return CapabilityResult(
                success=False,
                message=f"Invalid JSON in .claude/settings.json: {e}",
            )

        if not has_ruff_format_hook(settings):
            return CapabilityResult(
                success=True,
                message="ruff-format not installed",
            )

        # Remove hook using the pure function
        new_settings = remove_ruff_format_hook(settings)

        # Write back
        write_claude_settings(settings_path, new_settings)

        return CapabilityResult(
            success=True,
            message="Removed ruff format hook from .claude/settings.json",
        )
