"""Agent-based capabilities for erk init.

Agent capabilities install Claude agent definitions.
"""

import shutil
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)


class DevrunAgentCapability(Capability):
    """Safe execution agent for pytest/ty/ruff/make/gt.

    Installs:
    - .claude/agents/devrun.md
    """

    @property
    def name(self) -> str:
        return "devrun-agent"

    @property
    def description(self) -> str:
        return "Safe execution agent for pytest/ty/ruff/make/gt"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".claude/agents/devrun.md exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".claude/agents/devrun.md",
                artifact_type="file",
            ),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if the agent file exists."""
        assert repo_root is not None, "DevrunAgentCapability requires repo_root"
        return (repo_root / ".claude" / "agents" / "devrun.md").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Install the devrun agent definition."""
        assert repo_root is not None, "DevrunAgentCapability requires repo_root"
        # Inline import: avoids circular dependency with artifacts module
        from erk.artifacts.sync import get_bundled_claude_dir

        bundled_claude_dir = get_bundled_claude_dir()

        # Check for single-file agent first, then directory
        agent_file_src = bundled_claude_dir / "agents" / "devrun.md"
        agent_dir_src = bundled_claude_dir / "agents" / "devrun"

        if agent_file_src.exists():
            agent_dst = repo_root / ".claude" / "agents" / "devrun.md"
            agent_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agent_file_src, agent_dst)
            return CapabilityResult(
                success=True,
                message="Installed .claude/agents/devrun.md",
            )
        elif agent_dir_src.exists():
            agent_dst = repo_root / ".claude" / "agents" / "devrun"
            agent_dst.mkdir(parents=True, exist_ok=True)
            self._copy_directory(agent_dir_src, agent_dst)
            return CapabilityResult(
                success=True,
                message="Installed .claude/agents/devrun/",
            )

        return CapabilityResult(
            success=False,
            message="Agent 'devrun' not found in erk package",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
