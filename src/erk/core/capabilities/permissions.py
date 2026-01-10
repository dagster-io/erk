"""Permission-based capabilities for erk init.

Capabilities that modify .claude/settings.json permissions.
"""

import json
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)


class ErkBashPermissionsCapability(Capability):
    """Capability to add Bash(erk:*) permission to settings.json."""

    @property
    def name(self) -> str:
        return "erk-bash-permissions"

    @property
    def description(self) -> str:
        return "Allow Bash(erk:*) commands in Claude Code"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return "Bash(erk:*) in .claude/settings.json permissions.allow"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # settings.json is shared by multiple capabilities, so not listed here
        return []

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if Bash(erk:*) permission exists in settings.json."""
        assert repo_root is not None, "ErkBashPermissionsCapability requires repo_root"
        settings_path = repo_root / ".claude" / "settings.json"
        if not settings_path.exists():
            return False

        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        permissions = settings.get("permissions", {})
        allow_list = permissions.get("allow", [])
        return "Bash(erk:*)" in allow_list

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Add Bash(erk:*) to permissions.allow in settings.json."""
        assert repo_root is not None, "ErkBashPermissionsCapability requires repo_root"
        settings_path = repo_root / ".claude" / "settings.json"
        created_files: list[str] = []

        # Load existing settings or create new
        if settings_path.exists():
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        else:
            # Create directory if needed
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings = {}
            created_files.append(".claude/settings.json")

        # Ensure permissions structure exists
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "allow" not in settings["permissions"]:
            settings["permissions"]["allow"] = []

        # Check if already present
        if "Bash(erk:*)" in settings["permissions"]["allow"]:
            return CapabilityResult(
                success=True,
                message="Bash(erk:*) already in permissions.allow",
            )

        # Add the permission
        settings["permissions"]["allow"].append("Bash(erk:*)")

        # Write back with nice formatting
        settings_path.write_text(
            json.dumps(settings, indent=2) + "\n",
            encoding="utf-8",
        )

        return CapabilityResult(
            success=True,
            message="Added Bash(erk:*) to permissions.allow",
            created_files=tuple(created_files),
        )
