"""OneShotWorkflowCapability - GitHub Action for one-shot workflow."""

import shutil
from pathlib import Path

from erk.artifacts.paths import get_bundled_github_dir
from erk.artifacts.state import add_installed_capability, remove_installed_capability
from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)
from erk_shared.context.types import AgentBackend


class OneShotWorkflowCapability(Capability):
    """GitHub Action for one-shot workflow.

    Installs:
    - .github/workflows/one-shot.yml
    """

    @property
    def name(self) -> str:
        return "one-shot-workflow"

    @property
    def description(self) -> str:
        return "GitHub Action for autonomous one-shot planning and implementation"

    @property
    def required(self) -> bool:
        return True

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/one-shot.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/one-shot.yml",
                artifact_type="file",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare one-shot workflow as managed artifact."""
        return [ManagedArtifact(name="one-shot", artifact_type="workflow")]

    def is_installed(self, repo_root: Path | None, *, backend: AgentBackend) -> bool:
        if repo_root is None:
            raise ValueError("OneShotWorkflowCapability requires repo_root")
        return (repo_root / ".github" / "workflows" / "one-shot.yml").exists()

    def install(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        if repo_root is None:
            raise ValueError("OneShotWorkflowCapability requires repo_root")

        bundled_github_dir = get_bundled_github_dir()
        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        workflow_src = bundled_github_dir / "workflows" / "one-shot.yml"
        if not workflow_src.exists():
            return CapabilityResult(
                success=False,
                message="one-shot.yml not found in erk package",
            )

        workflow_dst = repo_root / ".github" / "workflows" / "one-shot.yml"
        workflow_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workflow_src, workflow_dst)

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        return CapabilityResult(
            success=True,
            message="Installed one-shot workflow",
        )

    def uninstall(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        """Remove the one-shot workflow."""
        if repo_root is None:
            raise ValueError("OneShotWorkflowCapability requires repo_root")

        workflow_file = repo_root / ".github" / "workflows" / "one-shot.yml"

        # Remove from installed capabilities
        remove_installed_capability(repo_root, self.name)

        if not workflow_file.exists():
            return CapabilityResult(
                success=True,
                message="one-shot-workflow not installed",
            )

        workflow_file.unlink()
        return CapabilityResult(
            success=True,
            message="Removed .github/workflows/one-shot.yml",
        )
