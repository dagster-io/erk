"""Ruff format capability for auto-formatting Python files after Write/Edit.

Capability for configuring a PostToolUse hook that runs ruff format on Python files.
"""

import json
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.claude_settings import (
    add_ruff_format_hook,
    get_repo_claude_settings_path,
    has_ruff_format_hook,
    write_claude_settings,
)


class RuffFormatCapability(Capability):
    """Capability to configure ruff format hook in Claude Code settings.

    This capability installs a PostToolUse hook that automatically runs
    `uv run ruff format` on Python files after Write or Edit operations.

    This capability is optional (required=False), meaning users must
    explicitly install it via `erk init capability add ruff-format`.
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

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if ruff format hook is configured in settings.json."""
        if repo_root is None:
            return False

        settings_path = get_repo_claude_settings_path(repo_root)
        if not settings_path.exists():
            return False

        content = settings_path.read_text(encoding="utf-8")
        if not content.strip():
            return False

        settings = json.loads(content)
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
            content = settings_path.read_text(encoding="utf-8")
            if content.strip():
                settings = json.loads(content)
            else:
                settings = {}
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
