"""Hooks capability for erk init.

Required capability that installs Claude Code hooks for erk integration.
"""

from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.claude_settings import (
    add_erk_hooks,
    get_repo_claude_settings_path,
    has_exit_plan_hook,
    has_user_prompt_hook,
    read_claude_settings,
    write_claude_settings,
)


class HooksCapability(Capability):
    """Required capability that installs erk hooks in Claude Code settings.

    This capability adds the UserPromptSubmit and ExitPlanMode hooks that erk
    needs for session management and plan tracking.
    """

    @property
    def name(self) -> str:
        return "erk-hooks"

    @property
    def description(self) -> str:
        return "Claude Code hooks for session and plan management"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return "UserPromptSubmit and ExitPlanMode hooks in .claude/settings.json"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(path=".claude/settings.json", artifact_type="file"),
        ]

    @property
    def required(self) -> bool:
        """Hooks are required for erk to function properly."""
        return True

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if both erk hooks are configured in settings.json."""
        assert repo_root is not None, "HooksCapability requires repo_root"
        settings_path = get_repo_claude_settings_path(repo_root)

        settings = read_claude_settings(settings_path)
        if settings is None:
            return False

        return has_user_prompt_hook(settings) and has_exit_plan_hook(settings)

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Add erk hooks to .claude/settings.json."""
        assert repo_root is not None, "HooksCapability requires repo_root"
        settings_path = get_repo_claude_settings_path(repo_root)
        created_files: list[str] = []

        # Load existing settings or create new
        settings = read_claude_settings(settings_path)
        if settings is None:
            # Create directory if needed
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings = {}
            created_files.append(".claude/settings.json")

        # Check if already installed
        if has_user_prompt_hook(settings) and has_exit_plan_hook(settings):
            return CapabilityResult(
                success=True,
                message="Erk hooks already configured",
            )

        # Add hooks
        new_settings = add_erk_hooks(settings)
        write_claude_settings(settings_path, new_settings)

        return CapabilityResult(
            success=True,
            message="Added erk hooks to .claude/settings.json",
            created_files=tuple(created_files),
        )
