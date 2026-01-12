"""Hooks capability for erk init.

Capability for configuring Claude Code hooks required by erk.
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
    add_erk_hooks,
    get_repo_claude_settings_path,
    has_erk_hook_by_marker,
    has_exit_plan_hook,
    has_user_prompt_hook,
    write_claude_settings,
)


class HooksCapability(Capability):
    """Capability to configure erk hooks in Claude Code settings.

    This capability installs the UserPromptSubmit and ExitPlanMode hooks
    required for erk's session management and plan tracking.

    This capability is marked as required=True, meaning it will be
    automatically installed during `erk init` without prompting.
    """

    @property
    def name(self) -> str:
        return "erk-hooks"

    @property
    def description(self) -> str:
        return "Configure Claude Code hooks for session management"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return "UserPromptSubmit and ExitPlanMode hooks in .claude/settings.json"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # settings.json is shared by multiple capabilities, so not listed here
        return []

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare erk hooks as managed artifacts."""
        return [
            ManagedArtifact(name="user-prompt-hook", artifact_type="hook"),
            ManagedArtifact(name="exit-plan-mode-hook", artifact_type="hook"),
        ]

    @property
    def required(self) -> bool:
        """Hooks are required for erk to function properly."""
        return True

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if both erk hooks are configured in settings.json with CURRENT commands.

        This checks for exact command match, not just marker presence.
        Old hooks with outdated commands will cause this to return False,
        triggering a re-install that updates to current commands.
        """
        if repo_root is None:
            return False

        settings_path = get_repo_claude_settings_path(repo_root)
        if not settings_path.exists():
            return False

        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        # Check for CURRENT command versions (exact match)
        return has_user_prompt_hook(settings) and has_exit_plan_hook(settings)

    def has_any_erk_hooks(self, repo_root: Path | None) -> bool:
        """Check if ANY erk hooks are present (current or old versions).

        Uses marker-based detection to find hooks regardless of command version.
        Useful for determining if hooks need updating vs fresh install.
        """
        if repo_root is None:
            return False

        settings_path = get_repo_claude_settings_path(repo_root)
        if not settings_path.exists():
            return False

        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return False

        has_user_prompt = has_erk_hook_by_marker(
            settings,
            hook_type="UserPromptSubmit",
            marker="ERK_HOOK_ID=user-prompt-hook",
            matcher=None,
        )
        has_exit_plan = has_erk_hook_by_marker(
            settings,
            hook_type="PreToolUse",
            marker="ERK_HOOK_ID=exit-plan-mode-hook",
            matcher="ExitPlanMode",
        )

        return has_user_prompt or has_exit_plan

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Add or update erk hooks in .claude/settings.json.

        This method is idempotent - it will replace any existing erk hooks
        (identified by ERK_HOOK_ID marker) with current versions, or add
        them if not present.
        """
        if repo_root is None:
            return CapabilityResult(
                success=False,
                message="HooksCapability requires repo_root",
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

        # Check if already installed with CURRENT commands
        if has_user_prompt_hook(settings) and has_exit_plan_hook(settings):
            return CapabilityResult(
                success=True,
                message="Hooks already configured",
            )

        # Determine if this is an update or fresh install
        has_any_hooks = self.has_any_erk_hooks(repo_root)

        # Add/replace hooks using the pure function
        new_settings = add_erk_hooks(settings)

        # Write back
        write_claude_settings(settings_path, new_settings)

        if has_any_hooks:
            message = "Updated erk hooks in .claude/settings.json"
        else:
            message = "Added erk hooks to .claude/settings.json"

        return CapabilityResult(
            success=True,
            message=message,
            created_files=tuple(created_files),
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Uninstall is blocked for required capabilities.

        Note: The CLI should block uninstall of required capabilities.
        This method exists to satisfy the ABC interface.
        """
        return CapabilityResult(
            success=False,
            message="Cannot uninstall required capability 'erk-hooks'",
        )
