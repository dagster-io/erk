"""LearnWorkflowCapability - GitHub Action for learn workflow."""

import shutil
from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
)


class LearnWorkflowCapability(Capability):
    """GitHub Action for learn documentation workflow.

    Installs:
    - .github/workflows/learn.yml
    """

    @property
    def name(self) -> str:
        return "learn-workflow"

    @property
    def description(self) -> str:
        return "GitHub Action for automated documentation learning"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".github/workflows/learn.yml exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/learn.yml",
                artifact_type="file",
            ),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare learn workflow as managed artifact."""
        return [ManagedArtifact(name="learn", artifact_type="workflow")]

    def is_installed(self, repo_root: Path | None) -> bool:
        assert repo_root is not None, "LearnWorkflowCapability requires repo_root"
        return (repo_root / ".github" / "workflows" / "learn.yml").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        assert repo_root is not None, "LearnWorkflowCapability requires repo_root"
        from erk.artifacts.state import add_installed_capability
        from erk.artifacts.sync import get_bundled_github_dir

        bundled_github_dir = get_bundled_github_dir()
        if not bundled_github_dir.exists():
            return CapabilityResult(
                success=False,
                message="Bundled .github/ not found in erk package",
            )

        workflow_src = bundled_github_dir / "workflows" / "learn.yml"
        if not workflow_src.exists():
            return CapabilityResult(
                success=False,
                message="learn.yml not found in erk package",
            )

        workflow_dst = repo_root / ".github" / "workflows" / "learn.yml"
        workflow_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workflow_src, workflow_dst)

        # Record capability installation
        add_installed_capability(repo_root, self.name)

        return CapabilityResult(
            success=True,
            message="Installed learn workflow",
        )

    def uninstall(self, repo_root: Path | None) -> CapabilityResult:
        """Remove the learn workflow."""
        assert repo_root is not None, "LearnWorkflowCapability requires repo_root"
        from erk.artifacts.state import remove_installed_capability

        workflow_file = repo_root / ".github" / "workflows" / "learn.yml"

        # Remove from installed capabilities
        remove_installed_capability(repo_root, self.name)

        if not workflow_file.exists():
            return CapabilityResult(
                success=True,
                message="learn-workflow not installed",
            )

        workflow_file.unlink()
        return CapabilityResult(
            success=True,
            message="Removed .github/workflows/learn.yml",
        )
