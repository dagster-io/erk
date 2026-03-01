"""PrRebaseWorkflowCapability - GitHub Action for PR rebase workflow."""

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


class PrRebaseWorkflowCapability(Capability):
    """GitHub Action for PR rebase workflow.

    Installs:
    - .github/workflows/pr-rebase.yml
    """

    @property
    def name(self) -> str:
        return "pr-rebase-workflow"

    @property
    def description(self) -> str:
        return "GitHub Action for rebasing PRs"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/pr-rebase.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/pr-rebase.yml",
                artifact_type="file",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare pr-rebase workflow as managed artifact."""
        return [ManagedArtifact(name="pr-rebase", artifact_type="workflow")]

    def is_installed(self, repo_root: Path | None, *, backend: AgentBackend) -> bool:
        if repo_root is None:
            raise ValueError("PrRebaseWorkflowCapability requires repo_root")
        return (repo_root / ".github" / "workflows" / "pr-rebase.yml").exists()

    def install(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        if repo_root is None:
            raise ValueError("PrRebaseWorkflowCapability requires repo_root")

        bundled_github_dir = get_bundled_github_dir()
        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        workflow_src = bundled_github_dir / "workflows" / "pr-rebase.yml"
        if not workflow_src.exists():
            return CapabilityResult(
                success=False,
                message="pr-rebase.yml not found in erk package",
            )

        workflow_dst = repo_root / ".github" / "workflows" / "pr-rebase.yml"
        workflow_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workflow_src, workflow_dst)

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        return CapabilityResult(
            success=True,
            message="Installed pr-rebase workflow",
        )

    def uninstall(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        """Remove the pr-rebase workflow."""
        if repo_root is None:
            raise ValueError("PrRebaseWorkflowCapability requires repo_root")

        workflow_file = repo_root / ".github" / "workflows" / "pr-rebase.yml"

        # Remove from installed capabilities
        remove_installed_capability(repo_root, self.name)

        if not workflow_file.exists():
            return CapabilityResult(
                success=True,
                message="pr-rebase-workflow not installed",
            )

        workflow_file.unlink()
        return CapabilityResult(
            success=True,
            message="Removed .github/workflows/pr-rebase.yml",
        )
