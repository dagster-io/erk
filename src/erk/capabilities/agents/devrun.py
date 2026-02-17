"""DevrunAgentCapability - safe execution agent for dev tools."""

import shutil
from pathlib import Path

from erk.artifacts.paths import get_bundled_claude_dir, get_bundled_codex_dir
from erk.artifacts.state import add_installed_capability, remove_installed_capability
from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
    backend_agent_dir,
)
from erk_shared.context.types import AgentBackend


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

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare devrun agent as managed artifact."""
        return [ManagedArtifact(name="devrun", artifact_type="agent")]

    def is_installed(self, repo_root: Path | None, *, backend: AgentBackend) -> bool:
        """Check if the agent file exists."""
        assert repo_root is not None, "DevrunAgentCapability requires repo_root"
        agent_dir = backend_agent_dir(backend)
        return (repo_root / agent_dir / "agents" / "devrun.md").exists()

    def install(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        """Install the devrun agent definition."""
        assert repo_root is not None, "DevrunAgentCapability requires repo_root"

        if backend == "codex":
            bundled_dir = get_bundled_codex_dir()
        else:
            bundled_dir = get_bundled_claude_dir()

        agent_dir = backend_agent_dir(backend)

        # Check for single-file agent first, then directory
        agent_file_src = bundled_dir / "agents" / "devrun.md"
        agent_dir_src = bundled_dir / "agents" / "devrun"

        if agent_file_src.exists():
            agent_dst = repo_root / agent_dir / "agents" / "devrun.md"
            agent_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agent_file_src, agent_dst)
            # Record capability installation
            add_installed_capability(repo_root, self.name)
            return CapabilityResult(
                success=True,
                message=f"Installed {agent_dir}/agents/devrun.md",
            )
        elif agent_dir_src.exists():
            agent_dst = repo_root / agent_dir / "agents" / "devrun"
            agent_dst.mkdir(parents=True, exist_ok=True)
            self._copy_directory(agent_dir_src, agent_dst)
            # Record capability installation
            add_installed_capability(repo_root, self.name)
            return CapabilityResult(
                success=True,
                message=f"Installed {agent_dir}/agents/devrun/",
            )

        return CapabilityResult(
            success=False,
            message="Agent 'devrun' not found in erk package",
        )

    def uninstall(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        """Remove the devrun agent."""
        assert repo_root is not None, "DevrunAgentCapability requires repo_root"

        agent_dir = backend_agent_dir(backend)
        agent_file = repo_root / agent_dir / "agents" / "devrun.md"
        agent_dir_path = repo_root / agent_dir / "agents" / "devrun"

        # Remove from installed capabilities
        remove_installed_capability(repo_root, self.name)

        if agent_file.exists():
            agent_file.unlink()
            return CapabilityResult(
                success=True,
                message=f"Removed {agent_dir}/agents/devrun.md",
            )
        elif agent_dir_path.exists():
            shutil.rmtree(agent_dir_path)
            return CapabilityResult(
                success=True,
                message=f"Removed {agent_dir}/agents/devrun/",
            )

        return CapabilityResult(
            success=True,
            message="devrun-agent not installed",
        )

    def _copy_directory(self, source: Path, target: Path) -> None:
        """Copy directory contents recursively."""
        for source_path in source.rglob("*"):
            if source_path.is_file():
                relative = source_path.relative_to(source)
                target_path = target / relative
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
